#!/usr/bin/env python3
"""
s16: Team Protocols — request-response protocol + request_id + dispatch + state machine.

Run:  python s16_team_protocols/code.py
Need: pip install anthropic python-dotenv + .env with ANTHROPIC_API_KEY

Changes from s15:
  - ProtocolState dataclass (request_id, type, sender, status, created_at)
  - pending_requests dict: tracks in-flight protocol requests
  - dispatch_message: routes incoming messages by type to handlers
  - request_shutdown: Lead sends shutdown protocol request
  - request_plan: Lead asks teammate to submit plan
  - handle_shutdown_request / handle_plan_response: teammate receives & responds
  - match_response: Lead correlates response to request via request_id (with type validation)
  - Teammate idle loop: waits for inbox messages instead of exiting after 10 rounds
  - Unified consume_lead_inbox: protocol routing + injection into history
  - 3 new Lead tools: request_shutdown, request_plan, review_plan
  - 1 new teammate tool: submit_plan

ASCII flow:
  Lead: BUS.send("shutdown_request", {request_id}) ──────→ teammate inbox
  Teammate: dispatch → handler → BUS.send("shutdown_response", {request_id}) ─→ Lead inbox
  Lead: consume_lead_inbox → match_response(request_id) → pending_requests[req_id].status = approved

Env/client setup and the base tools come from common.py. s16 inherits s13's
run_in_background bash signature (re-defined locally, delegating to the
base). The __main__ REPL stays inline because protocol inbox routing
(consume_lead_inbox) has to be interleaved with each agent turn.
"""

import json
import random
import sys
import threading
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field

# Bootstrap repo root onto sys.path so `from common import ...` works whether
# this file is run directly or loaded by tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import init_env, make_base_tools, select_tools

client, MODEL, WORKDIR = init_env()
safe_path, _base_run_bash, run_read, run_write, _, _ = make_base_tools(WORKDIR)
MEMORY_DIR = WORKDIR / ".memory"
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"


def run_bash(command: str, run_in_background: bool = False) -> str:
    # run_in_background is dispatched by agent_loop; the base run_bash does the
    # actual execution. Re-defined locally to keep the s16 tool signature.
    return _base_run_bash(command)

# ── Task System (imported from s12 via mechanisms/tasks.py; issue #349) ──
# s12 defines this inline (first-appearance rule); s13-s16 reuse it verbatim.
from mechanisms.tasks import (
    init_tasks, Task, create_task, save_task, load_task, list_tasks,
    get_task, can_start, claim_task, complete_task)
init_tasks(WORKDIR)


# ── Prompt Assembly (from s10, synced) ──

PROMPT_SECTIONS = {
    "identity": "You are a coding agent. Act, don't explain.",
    "tools": "Available tools: bash, read_file, write_file, "
             "get_task, create_task, list_tasks, claim_task, complete_task, "
             "spawn_teammate, send_message, check_inbox, "
             "request_shutdown, request_plan, review_plan.",
    "workspace": f"Working directory: {WORKDIR}",
    "memory": "Relevant memories are injected below when available.",
}


# Prompt Assembly: s10 defines inline (first-appearance rule); s11+ reuse
# via factory. PROMPT_SECTIONS stays local — the tools list is lesson-specific.
from mechanisms.prompt_assembly import make_prompt_assembly
assemble_system_prompt, get_system_prompt = make_prompt_assembly(PROMPT_SECTIONS, verbose=True)

def run_create_task(subject: str, description: str = "",
                    blockedBy: list[str] | None = None) -> str:
    task = create_task(subject, description, blockedBy)
    deps = f" (blockedBy: {', '.join(blockedBy)})" if blockedBy else ""
    print(f"  \033[34m[create] {task.subject}{deps}\033[0m")
    return f"Created {task.id}: {task.subject}{deps}"


def run_list_tasks() -> str:
    tasks = list_tasks()
    if not tasks:
        return "No tasks. Use create_task to add some."
    lines = []
    for t in tasks:
        icon = {"pending": "○", "in_progress": "●",
                "completed": "✓"}.get(t.status, "?")
        deps = f" (blockedBy: {', '.join(t.blockedBy)})" if t.blockedBy else ""
        owner = f" [{t.owner}]" if t.owner else ""
        lines.append(f"  {icon} {t.id}: {t.subject} "
                     f"[{t.status}]{owner}{deps}")
    return "\n".join(lines)


def run_get_task(task_id: str) -> str:
    try:
        return get_task(task_id)
    except FileNotFoundError:
        return f"Error: Task {task_id} not found"


def run_claim_task(task_id: str) -> str:
    return claim_task(task_id, owner="agent")


def run_complete_task(task_id: str) -> str:
    return complete_task(task_id)


# ── Background Tasks (from s13 via mechanisms/background.py; issue #349) ──
# s13 defines inline (first-appearance rule); s14+ reuse via factory.
# execute_tool is defined later (Tool Dispatch) — factory binds at call time.
from mechanisms.background import (
    is_slow_operation, should_run_background, make_background)


# ── MessageBus (from s15 via mechanisms/messagebus.py; issue #349) ──
# s15 defines this inline (first-appearance rule); s16+ reuse it.
# s16 added the `metadata` param to send (carried forward here).
from mechanisms.messagebus import MessageBus, init_messagebus
init_messagebus(WORKDIR)
BUS = MessageBus()
active_teammates: dict[str, bool] = {}


# ── Protocol State (s16 new) ──

@dataclass
class ProtocolState:
    request_id: str
    type: str       # "shutdown" | "plan_approval"
    sender: str
    target: str
    status: str     # pending | approved | rejected
    payload: str    # plan text or shutdown reason
    created_at: float = field(default_factory=time.time)


pending_requests: dict[str, ProtocolState] = {}


def new_request_id() -> str:
    return f"req_{random.randint(0, 999999):06d}"


def match_response(response_type: str, request_id: str, approve: bool):
    """Correlate a response to the original request via request_id.
    Validates that response_type matches the request type."""
    state = pending_requests.get(request_id)
    if not state:
        print(f"  \033[31m[protocol] unknown request_id: {request_id}\033[0m")
        return
    # Validate response type matches request type
    if state.type == "shutdown" and response_type != "shutdown_response":
        print(f"  \033[31m[protocol] type mismatch: expected shutdown_response, "
              f"got {response_type}\033[0m")
        return
    if state.type == "plan_approval" and response_type != "plan_approval_response":
        print(f"  \033[31m[protocol] type mismatch: expected plan_approval_response, "
              f"got {response_type}\033[0m")
        return
    if state.status != "pending":
        print(f"  \033[33m[protocol] {request_id} already {state.status}, "
              f"ignoring duplicate\033[0m")
        return
    state.status = "approved" if approve else "rejected"
    icon = "✓" if approve else "✗"
    color = "32" if approve else "31"
    print(f"  \033[{color}m[protocol] {state.type} {icon} "
          f"({request_id}: {state.status})\033[0m")


# ── Unified Lead Inbox Consumer (s16 fix) ──
# Both check_inbox tool and main loop call this function.
# Protocol responses are routed via match_response before returning.

def consume_lead_inbox(route_protocol: bool = True) -> list[dict]:
    """Read Lead's inbox. Route protocol responses, return all messages.
    Called by both run_check_inbox() and main loop to avoid
    messages being consumed without protocol routing."""
    msgs = BUS.read_inbox("lead")
    if not msgs:
        return []
    if route_protocol:
        for msg in msgs:
            meta = msg.get("metadata", {})
            req_id = meta.get("request_id", "")
            msg_type = msg.get("type", "")
            if req_id and msg_type.endswith("_response"):
                approve = meta.get("approve", False)
                match_response(msg_type, req_id, approve)
    return msgs


# ── Teammate Thread (s16: idle loop + dispatch) ──

def spawn_teammate_thread(name: str, role: str, prompt: str) -> str:
    """Spawn a teammate agent in a background thread.
    Uses idle loop: after each LLM turn, waits for inbox messages
    (shutdown_request, new task) instead of exiting."""
    if name in active_teammates:
        return f"Teammate '{name}' already exists"

    system = (f"You are '{name}', a {role}. "
              f"Use tools to complete tasks. "
              f"Check inbox for protocol messages (shutdown_request, etc).")

    def handle_inbox_message(name: str, msg: dict, messages: list) -> bool:
        """Dispatch incoming protocol messages by type.
        Returns True if teammate should stop."""
        msg_type = msg.get("type", "message")
        meta = msg.get("metadata", {})
        req_id = meta.get("request_id", "")

        if msg_type == "shutdown_request":
            BUS.send(name, "lead", "Shutting down gracefully.",
                     "shutdown_response",
                     {"request_id": req_id, "approve": True})
            print(f"  \033[35m[protocol] {name} approved shutdown "
                  f"({req_id})\033[0m")
            return True  # stop the loop

        if msg_type == "plan_approval_response":
            approve = meta.get("approve", False)
            if approve:
                messages.append({"role": "user",
                    "content": f"[Plan approved] Proceed with the task."})
            else:
                messages.append({"role": "user",
                    "content": f"[Plan rejected] Feedback: {msg['content']}"})

        return False  # continue

    def run():
        messages = [{"role": "user", "content": prompt}]
        sub_tools = [
            {"name": "bash", "description": "Run a shell command.",
             "input_schema": {"type": "object",
                              "properties": {"command": {"type": "string"}},
                              "required": ["command"]}},
            {"name": "read_file", "description": "Read file.",
             "input_schema": {"type": "object",
                              "properties": {"path": {"type": "string"}},
                              "required": ["path"]}},
            {"name": "write_file", "description": "Write file.",
             "input_schema": {"type": "object",
                              "properties": {"path": {"type": "string"},
                                             "content": {"type": "string"}},
                              "required": ["path", "content"]}},
            {"name": "send_message",
             "description": "Send message to another agent.",
             "input_schema": {"type": "object",
                              "properties": {"to": {"type": "string"},
                                             "content": {"type": "string"}},
                              "required": ["to", "content"]}},
            {"name": "submit_plan",
             "description": "Submit a plan for Lead approval.",
             "input_schema": {"type": "object",
                              "properties": {"plan": {"type": "string"}},
                              "required": ["plan"]}},
        ]
        sub_handlers = {
            "bash": run_bash, "read_file": run_read, "write_file": run_write,
            "send_message": lambda to, content: (BUS.send(name, to, content),
                                                  "Sent")[1],
            "submit_plan": lambda plan: _teammate_submit_plan(name, plan),
        }

        shutdown_requested = False
        while not shutdown_requested:
            # Check inbox for protocol messages
            inbox = BUS.read_inbox(name)
            should_stop = False
            non_protocol = []
            for msg in inbox:
                if msg.get("type") in ("shutdown_request", "plan_approval_response"):
                    should_stop = handle_inbox_message(name, msg, messages)
                    if should_stop:
                        break
                else:
                    non_protocol.append(msg)
            if should_stop:
                shutdown_requested = True
                break
            if non_protocol:
                inbox_json = json.dumps(non_protocol)
                messages.append({"role": "user",
                    "content": "<inbox>" + inbox_json + "</inbox>"})

            # LLM turn
            try:
                response = client.messages.create(
                    model=MODEL, system=system, messages=messages[-20:],
                    tools=sub_tools, max_tokens=8000)
            except Exception:
                break

            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                # Idle: wait for inbox messages instead of exiting
                # Real CC sends idle_notification to Lead here
                while not shutdown_requested:
                    time.sleep(1)
                    inbox = BUS.read_inbox(name)
                    if not inbox:
                        continue
                    for msg in inbox:
                        if msg.get("type") in ("shutdown_request", "plan_approval_response"):
                            should_stop = handle_inbox_message(name, msg, messages)
                            if should_stop:
                                shutdown_requested = True
                                break
                        else:
                            non_protocol.append(msg)
                    if shutdown_requested:
                        break
                    if non_protocol:
                        inbox_json = json.dumps(non_protocol)
                        messages.append({"role": "user",
                            "content": "<inbox>" + inbox_json + "</inbox>"})
                        break  # back to LLM turn with new messages

            # Execute tool calls
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    handler = sub_handlers.get(block.name)
                    output = handler(**block.input) if handler else "Unknown"
                    results.append({"type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": str(output)})
            messages.append({"role": "user", "content": results})

        # Send final summary to Lead
        summary = "Done."
        for msg in reversed(messages):
            if msg["role"] == "assistant" and isinstance(msg["content"], list):
                for b in msg["content"]:
                    if getattr(b, "type", None) == "text":
                        summary = b.text
                        break
                else:
                    continue
                break
        BUS.send(name, "lead", summary, "result")
        active_teammates.pop(name, None)
        print(f"  \033[32m[teammate] {name} finished\033[0m")

    active_teammates[name] = True
    threading.Thread(target=run, daemon=True).start()
    print(f"  \033[36m[teammate] {name} spawned as {role}\033[0m")
    return f"Teammate '{name}' spawned as {role}"


def _teammate_submit_plan(from_name: str, plan: str) -> str:
    """Teammate submits a plan to Lead for approval.

    Note: This is a protocol-level request, not a code-level gate.
    After submitting, the teammate's thread continues running — it can
    still call bash/write/etc. Real enforcement relies on the model
    waiting for the approval response before acting. Code-level tool
    gating would require blocking the teammate's tool dispatch until
    approval arrives.
    """
    req_id = new_request_id()
    pending_requests[req_id] = ProtocolState(
        request_id=req_id, type="plan_approval",
        sender=from_name, target="lead",
        status="pending", payload=plan)
    BUS.send(from_name, "lead", plan,
             "plan_approval_request",
             {"request_id": req_id})
    return f"Plan submitted ({req_id}). Waiting for approval..."


# ── Lead Protocol Tools (s16 new) ──

def run_request_shutdown(teammate: str) -> str:
    req_id = new_request_id()
    pending_requests[req_id] = ProtocolState(
        request_id=req_id, type="shutdown",
        sender="lead", target=teammate,
        status="pending", payload="")
    BUS.send("lead", teammate, "Please shut down gracefully.",
             "shutdown_request",
             {"request_id": req_id})
    print(f"  \033[35m[protocol] shutdown_request → {teammate} "
          f"({req_id})\033[0m")
    return f"Shutdown request sent to {teammate} (req: {req_id})"


def run_request_plan(teammate: str, task: str) -> str:
    """Lead asks a teammate to submit a plan for a task."""
    BUS.send("lead", teammate, f"Please submit a plan for: {task}",
             "message")
    return f"Asked {teammate} to submit a plan"


def run_review_plan(request_id: str, approve: bool, feedback: str = "") -> str:
    state = pending_requests.get(request_id)
    if not state:
        return f"Request {request_id} not found"
    if state.status != "pending":
        return f"Request {request_id} already {state.status}"
    state.status = "approved" if approve else "rejected"
    BUS.send("lead", state.sender, feedback or ("Approved" if approve else "Rejected"),
             "plan_approval_response",
             {"request_id": request_id, "approve": approve})
    icon = "✓" if approve else "✗"
    print(f"  \033[32m[protocol] plan {icon} ({request_id})\033[0m")
    return f"Plan {'approved' if approve else 'rejected'} ({request_id})"


# ── Other Lead Tool Handlers ──

def run_spawn_teammate(name: str, role: str, prompt: str) -> str:
    return spawn_teammate_thread(name, role, prompt)


def run_send_message(to: str, content: str) -> str:
    BUS.send("lead", to, content)
    return f"Sent to {to}"


def run_check_inbox() -> str:
    """Check Lead's inbox. Routes protocol responses via match_response."""
    msgs = consume_lead_inbox(route_protocol=True)
    if not msgs:
        return "(inbox empty)"
    lines = []
    for m in msgs:
        meta = m.get("metadata", {})
        req_id = meta.get("request_id", "")
        tag = f" [{m['type']} req:{req_id}]" if req_id else f" [{m['type']}]"
        lines.append(f"  [{m['from']}]{tag} {m['content'][:200]}")
    return "\n".join(lines)


# ── Tool Dispatch ──

def execute_tool(block) -> str:
    """Execute a tool call block, return output."""
    handler = {
        "bash": run_bash, "read_file": run_read, "write_file": run_write,
        "create_task": run_create_task, "list_tasks": run_list_tasks,
        "get_task": run_get_task, "claim_task": run_claim_task,
        "complete_task": run_complete_task,
        "spawn_teammate": run_spawn_teammate,
        "send_message": run_send_message, "check_inbox": run_check_inbox,
        "request_shutdown": run_request_shutdown,
        "request_plan": run_request_plan, "review_plan": run_review_plan,
    }.get(block.name)
    if handler:
        return handler(**block.input)
    return f"Unknown tool: {block.name}"


start_background_task, collect_background_results, has_pending_background = \
    make_background(execute_tool)


# ── Tool Definitions ──

TOOLS = [
    # bash carries the run_in_background flag (dispatched by agent_loop)
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object",
                      "properties": {
                          "command": {"type": "string"},
                          "run_in_background": {"type": "boolean"}},
                      "required": ["command"]}},
    *select_tools(("read_file", "write_file")),
    {"name": "create_task",
     "description": "Create a new task with optional blockedBy dependencies.",
     "input_schema": {"type": "object",
                      "properties": {
                          "subject": {"type": "string"},
                          "description": {"type": "string"},
                          "blockedBy": {"type": "array",
                                        "items": {"type": "string"}}},
                      "required": ["subject"]}},
    {"name": "list_tasks",
     "description": "List all tasks with status, owner, and dependencies.",
     "input_schema": {"type": "object", "properties": {},
                      "required": []}},
    {"name": "get_task",
     "description": "Get full details of a specific task by ID.",
     "input_schema": {"type": "object",
                      "properties": {"task_id": {"type": "string"}},
                      "required": ["task_id"]}},
    {"name": "claim_task",
     "description": "Claim a pending task. Sets owner, changes status to in_progress.",
     "input_schema": {"type": "object",
                      "properties": {"task_id": {"type": "string"}},
                      "required": ["task_id"]}},
    {"name": "complete_task",
     "description": "Complete an in-progress task. Reports unblocked downstream tasks.",
     "input_schema": {"type": "object",
                      "properties": {"task_id": {"type": "string"}},
                      "required": ["task_id"]}},
    {"name": "spawn_teammate",
     "description": "Spawn a teammate agent in a background thread.",
     "input_schema": {"type": "object",
                      "properties": {
                          "name": {"type": "string"},
                          "role": {"type": "string"},
                          "prompt": {"type": "string"}},
                      "required": ["name", "role", "prompt"]}},
    {"name": "send_message",
     "description": "Send message to a teammate via MessageBus.",
     "input_schema": {"type": "object",
                      "properties": {"to": {"type": "string"},
                                     "content": {"type": "string"}},
                      "required": ["to", "content"]}},
    {"name": "check_inbox",
     "description": "Check Lead's inbox. Routes protocol responses automatically.",
     "input_schema": {"type": "object", "properties": {},
                      "required": []}},
    {"name": "request_shutdown",
     "description": "Request a teammate to shut down gracefully.",
     "input_schema": {"type": "object",
                      "properties": {"teammate": {"type": "string"}},
                      "required": ["teammate"]}},
    {"name": "request_plan",
     "description": "Ask a teammate to submit a plan for review.",
     "input_schema": {"type": "object",
                      "properties": {"teammate": {"type": "string"},
                                     "task": {"type": "string"}},
                      "required": ["teammate", "task"]}},
    {"name": "review_plan",
     "description": "Approve or reject a submitted plan by request_id.",
     "input_schema": {"type": "object",
                      "properties": {
                          "request_id": {"type": "string"},
                          "approve": {"type": "boolean"},
                          "feedback": {"type": "string"}},
                      "required": ["request_id", "approve"]}},
]


# ── Context ──

def update_context(context: dict, messages: list) -> dict:
    """Derive context from real state."""
    memories = ""
    if MEMORY_INDEX.exists():
        content = MEMORY_INDEX.read_text().strip()
        if content:
            memories = content
    return {
        "enabled_tools": [t["name"] for t in TOOLS],
        "workspace": str(WORKDIR),
        "memories": memories,
    }


# ── Agent Loop ──

def agent_loop(messages: list, context: dict):
    system = get_system_prompt(context)
    while True:
        try:
            response = client.messages.create(
                model=MODEL, system=system, messages=messages,
                tools=TOOLS, max_tokens=8000)
        except Exception as e:
            messages.append({"role": "assistant", "content": [
                {"type": "text",
                 "text": f"[Error] {type(e).__name__}: {e}"}]})
            return

        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"\033[36m> {block.name}\033[0m")

            if should_run_background(block.name, block.input):
                bg_id = start_background_task(block)
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"[Background task {bg_id} started] "
                                           f"Result will be available when complete."})
            else:
                output = execute_tool(block)
                print(str(output)[:300])
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": output})

        # Merge background tool results + notifications into one user message
        user_content = list(results)
        bg_notifications = collect_background_results()
        if bg_notifications:
            for notif in bg_notifications:
                user_content.append({"type": "text", "text": notif})
        messages.append({"role": "user", "content": user_content})
        context = update_context(context, messages)
        system = get_system_prompt(context)


if __name__ == "__main__":
    print("s16: team protocols")
    print("Enter a question, press Enter to send. Type q to quit.\n")
    history = []
    context = update_context({}, [])
    while True:
        try:
            query = input("\033[36ms16 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history, context)
        context = update_context(context, history)
        for block in history[-1]["content"]:
            if getattr(block, "type", None) == "text":
                print(block.text)
            elif isinstance(block, dict) and block.get("type") == "text":
                print(block.get("text", ""))

        # Check inbox → route protocol + inject into history
        inbox_msgs = consume_lead_inbox(route_protocol=True)
        if inbox_msgs:
            inbox_text = "\n".join(
                f"From {m['from']}: {m['content'][:200]}" for m in inbox_msgs)
            history.append({"role": "user",
                            "content": f"[Inbox]\n{inbox_text}"})
            print(f"\n\033[33m[Inbox: {len(inbox_msgs)} messages injected]\033[0m")
        print()
