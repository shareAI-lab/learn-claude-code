#!/usr/bin/env python3
"""
s15: Agent Teams — MessageBus + spawn_teammate_thread + inbox injection.

Run:  python s15_agent_teams/code.py
Need: pip install anthropic python-dotenv + .env with ANTHROPIC_API_KEY

Changes from s14:
  - MessageBus class: file-based mailboxes (.mailboxes/*.jsonl)
  - spawn_teammate_thread: creates teammate in background thread
  - Teammate runs own simplified agent_loop (bash, read, write, send_message)
  - Lead tools: spawn_teammate, send_message, check_inbox (3 new)
  - Lead inbox: teammate messages injected into history (not just printed)
  - Teaching version: teammates limited to 10 rounds (real CC uses idle loop)

ASCII flow:
  Lead: cron_queue → messages → prompt → LLM → TOOLS ────→ loop
                ↑                     ↓                        |
                └── inbox ← MessageBus ← teammate.send_message ←┘
  Teammate: inbox → LLM → bash/read/write/send → loop (max 10 turns)

Env/client setup and the base tools come from common.py. s15 inherits s13's
run_in_background bash signature (re-defined locally, delegating to the
base). The __main__ REPL stays inline because the event-queue + input/inbox
poller threads need a custom main loop.
"""

import json
import random
import sys
import threading
import time
import queue
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

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
    # actual execution. Re-defined locally to keep the s15 tool signature.
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
             "schedule_cron, list_crons, cancel_cron, "
             "spawn_teammate, send_message, check_inbox.",
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


# ── Background Tasks (from s13, synced) ──


# Background Tasks: s13 defines inline (first-appearance rule); s14+ reuse
# via factory. execute_tool stays local — the handler dict is lesson-specific.
from mechanisms.background import (
    is_slow_operation, should_run_background, make_background)


def execute_tool(block) -> str:
    """Execute a tool call block, return output."""
    handler = {
        "bash": run_bash, "read_file": run_read, "write_file": run_write,
        "create_task": run_create_task, "list_tasks": run_list_tasks,
        "get_task": run_get_task, "claim_task": run_claim_task,
        "complete_task": run_complete_task,
        "schedule_cron": run_schedule_cron, "list_crons": run_list_crons,
        "cancel_cron": run_cancel_cron,
        "spawn_teammate": run_spawn_teammate,
        "send_message": run_send_message, "check_inbox": run_check_inbox,
    }.get(block.name)
    if handler:
        return handler(**block.input)
    return f"Unknown tool: {block.name}"


start_background_task, collect_background_results, has_pending_background = make_background(execute_tool)



# ── Cron Scheduler (from s14 via mechanisms/cron.py; issue #349) ──
# s14 defines this inline (first-appearance rule); s15 reuses it verbatim.
from mechanisms.cron import (
    init_cron, CronJob, schedule_job, cancel_job, list_scheduled_jobs,
    consume_cron_queue, has_cron_queue, save_durable_jobs,
    validate_cron, cron_matches)
init_cron(WORKDIR)



# Cron tool handlers

def run_schedule_cron(cron: str, prompt: str,
                      recurring: bool = True, durable: bool = True) -> str:
    result = schedule_job(cron, prompt, recurring, durable)
    if isinstance(result, str):
        return f"Error: {result}"
    return f"Scheduled {result.id}: '{cron}' → {prompt}"


def run_list_crons() -> str:
    jobs = list_scheduled_jobs()
    if not jobs:
        return "No cron jobs. Use schedule_cron to add one."
    lines = []
    for j in jobs:
        tag = "recurring" if j.recurring else "one-shot"
        dur = "durable" if j.durable else "session"
        lines.append(f"  {j.id}: '{j.cron}' → {j.prompt[:40]} "
                     f"[{tag}, {dur}]")
    return "\n".join(lines)


def run_cancel_cron(job_id: str) -> str:
    return cancel_job(job_id)


# ── MessageBus (s15 new) ──
# Teaching version uses simple file append + unlink.
# Real CC uses proper-lockfile for concurrent write safety.

MAILBOX_DIR = WORKDIR / ".mailboxes"
MAILBOX_DIR.mkdir(exist_ok=True)


class MessageBus:
    """File-based message bus. Each agent has a .jsonl inbox.
    Read is destructive: read_text + unlink (consumes messages).
    Teaching version: no file locking; real CC uses proper-lockfile."""

    def send(self, from_agent: str, to_agent: str, content: str,
             msg_type: str = "message"):
        msg = {"from": from_agent, "to": to_agent,
               "content": content, "type": msg_type,
               "ts": time.time()}
        inbox = MAILBOX_DIR / f"{to_agent}.jsonl"
        with open(inbox, "a") as f:
            f.write(json.dumps(msg) + "\n")
        print(f"  \033[33m[bus] {from_agent} → {to_agent}: "
              f"{content[:50]}\033[0m")

    def read_inbox(self, agent: str) -> list[dict]:
        inbox = MAILBOX_DIR / f"{agent}.jsonl"
        if not inbox.exists():
            return []
        msgs = [json.loads(line) for line in inbox.read_text().splitlines()
                if line.strip()]
        inbox.unlink()  # consume: read + delete
        return msgs

    def peek(self, agent: str) -> bool:
        """Non-destructive: True if the agent has unread inbox messages.
        The Lead's inbox poller uses this to decide whether to wake a turn
        without consuming the mailbox."""
        inbox = MAILBOX_DIR / f"{agent}.jsonl"
        return inbox.exists() and inbox.stat().st_size > 0


BUS = MessageBus()

# Track spawned teammates
active_teammates: dict[str, bool] = {}


# ── Teammate Thread (s15 new) ──

def spawn_teammate_thread(name: str, role: str, prompt: str) -> str:
    """Spawn a teammate agent in a background thread.
    Teaching version: max 10 rounds per teammate.
    Real CC: teammates use idle loop (wait for inbox, work, repeat)
    until shutdown_request."""
    if name in active_teammates:
        return f"Teammate '{name}' already exists"

    system = (f"You are '{name}', a {role}. "
              f"Use tools to complete tasks. "
              f"Send results via send_message to 'lead'.")

    def run():
        messages = [{"role": "user", "content": prompt}]
        sub_tools = [
            {"name": "bash", "description": "Run a shell command.",
             "input_schema": {"type": "object",
                              "properties": {"command": {"type": "string"}},
                              "required": ["command"]}},
            {"name": "read_file", "description": "Read file contents.",
             "input_schema": {"type": "object",
                              "properties": {"path": {"type": "string"}},
                              "required": ["path"]}},
            {"name": "write_file", "description": "Write content to a file.",
             "input_schema": {"type": "object",
                              "properties": {"path": {"type": "string"},
                                             "content": {"type": "string"}},
                              "required": ["path", "content"]}},
            {"name": "send_message",
             "description": "Send a message to another agent.",
             "input_schema": {"type": "object",
                              "properties": {"to": {"type": "string"},
                                             "content": {"type": "string"}},
                              "required": ["to", "content"]}},
        ]
        sub_handlers = {
            "bash": run_bash, "read_file": run_read, "write_file": run_write,
            "send_message": lambda to, content: (BUS.send(name, to, content),
                                                  "Sent")[1],
        }

        for _ in range(10):
            inbox = BUS.read_inbox(name)
            if inbox:
                messages.append({"role": "user",
                                 "content": f"<inbox>{json.dumps(inbox)}</inbox>"})
            try:
                response = client.messages.create(
                    model=MODEL, system=system, messages=messages[-20:],
                    tools=sub_tools, max_tokens=8000)
            except Exception:
                break
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                break
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


# ── Team Tool Handlers (s15 new) ──

def run_spawn_teammate(name: str, role: str, prompt: str) -> str:
    return spawn_teammate_thread(name, role, prompt)


def run_send_message(to: str, content: str) -> str:
    BUS.send("lead", to, content)
    return f"Sent to {to}"


def run_check_inbox() -> str:
    msgs = BUS.read_inbox("lead")
    if not msgs:
        return "(inbox empty)"
    lines = []
    for m in msgs:
        lines.append(f"  [{m['from']}] {m['content'][:200]}")
    return "\n".join(lines)


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
    {"name": "schedule_cron",
     "description": "Schedule a cron job. cron is 5-field: min hour dom month dow.",
     "input_schema": {"type": "object",
                      "properties": {
                          "cron": {"type": "string",
                                   "description": "5-field cron expression"},
                          "prompt": {"type": "string",
                                     "description": "Message to inject when fired"},
                          "recurring": {"type": "boolean",
                                        "description": "True=recurring, False=one-shot"},
                          "durable": {"type": "boolean",
                                      "description": "True=persist to disk"}},
                      "required": ["cron", "prompt"]}},
    {"name": "list_crons",
     "description": "List all registered cron jobs.",
     "input_schema": {"type": "object", "properties": {},
                      "required": []}},
    {"name": "cancel_cron",
     "description": "Cancel a cron job by ID.",
     "input_schema": {"type": "object",
                      "properties": {"job_id": {"type": "string"}},
                      "required": ["job_id"]}},
    {"name": "spawn_teammate",
     "description": "Spawn a teammate agent in a background thread.",
     "input_schema": {"type": "object",
                      "properties": {
                          "name": {"type": "string"},
                          "role": {"type": "string"},
                          "prompt": {"type": "string"}},
                      "required": ["name", "role", "prompt"]}},
    {"name": "send_message",
     "description": "Send a message to a teammate via MessageBus.",
     "input_schema": {"type": "object",
                      "properties": {"to": {"type": "string"},
                                     "content": {"type": "string"}},
                      "required": ["to", "content"]}},
    {"name": "check_inbox",
     "description": "Check Lead's inbox for teammate messages.",
     "input_schema": {"type": "object", "properties": {},
                      "required": []}},
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
# Teaching code keeps a basic agent loop. S11's full error recovery is omitted.
# Cron queue is consumed when agent_loop is called; real CC auto-wakes via
# queue processor (useQueueProcessor.ts) when items arrive.

def agent_loop(messages: list, context: dict):
    system = get_system_prompt(context)
    while True:
        # Consume fired cron jobs → inject as messages
        fired = consume_cron_queue()
        for job in fired:
            messages.append({"role": "user",
                             "content": f"[Scheduled] {job.prompt}"})
            print(f"  \033[35m[inject cron] {job.prompt[:50]}\033[0m")

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
    print("s15: agent teams")
    print("Enter a question, press Enter to send. Type q to quit.\n")
    history = []
    context = update_context({}, [])

    # input() and a 1s poller (teammate inbox or background results) feed one
    # event queue (issues #291, #46).
    events = queue.Queue()

    def input_reader():
        while True:
            try:
                line = input("\033[36ms15 >> \033[0m")
            except (EOFError, KeyboardInterrupt):
                events.put(("quit", None))
                return
            events.put(("user", line))

    def inbox_poller():
        # Poll ~1s and wake the Lead when async results are ready: teammate
        # inbox messages or completed background tasks. Don't gate on
        # active_teammates: a teammate sends its result and then removes itself,
        # so the final message can outlive its registry entry.
        while True:
            time.sleep(1)
            if BUS.peek("lead") or has_pending_background():
                events.put(("wake", None))

    threading.Thread(target=input_reader, daemon=True).start()
    threading.Thread(target=inbox_poller, daemon=True).start()

    had_teammates = False
    while True:
        kind, payload = events.get()
        if kind == "quit":
            break
        if kind == "user":
            if payload.strip().lower() in ("q", "exit", ""):
                break
            history.append({"role": "user", "content": payload})
        else:  # "wake": teammate inbox or background results are ready
            parts = []
            inbox = BUS.read_inbox("lead")
            if inbox:
                parts.append("[Inbox]\n" + "\n".join(
                    f"From {m['from']}: {m['content'][:200]}" for m in inbox))
            bg = collect_background_results()
            parts.extend(bg)
            if not parts:
                continue  # already drained by an earlier wake (idempotent)
            history.append({"role": "user", "content": "\n".join(parts)})
            print(f"\n\033[33m[wake: {len(inbox)} inbox + {len(bg)} background "
                  f"-> new turn]\033[0m")

        # One turn for whichever source woke us.
        agent_loop(history, context)
        context = update_context(context, history)
        for block in history[-1]["content"]:
            if getattr(block, "type", None) == "text":
                print(block.text)
            elif isinstance(block, dict) and block.get("type") == "text":
                print(block.get("text", ""))

        # Announce once when every teammate has finished and its output drained.
        if active_teammates:
            had_teammates = True
        elif had_teammates and not BUS.peek("lead") and not has_pending_background():
            print("\033[32m[all teammates done]\033[0m")
            had_teammates = False
        print()
