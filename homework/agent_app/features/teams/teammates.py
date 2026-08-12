"""Persistent teammate lifecycle with all application dependencies injected."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


TEAM_TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 1000}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "send_message", "description": "Send a message to another agent.",
     "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "content": {"type": "string"}}, "required": ["to", "content"]}},
    {"name": "submit_plan", "description": "Submit a plan for Lead approval.",
     "input_schema": {"type": "object", "properties": {"plan": {"type": "string"}}, "required": ["plan"]}},
    {"name": "list_tasks", "description": "List all tasks on the board.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "claim_task", "description": "Claim a pending task.",
     "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}},
    {"name": "complete_task", "description": "Mark an in-progress task as completed.",
     "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}},
]


@dataclass(slots=True)
class TeamState:
    active: dict[str, dict] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)


def idle_poll(
    bus,
    agent_name: str,
    messages: list,
    name: str,
    worktree_context: dict | None,
    *,
    scan_unclaimed: Callable[[], list[dict]],
    claim_task: Callable,
    worktree_path: Callable[[str], Path],
    sleep: Callable[[float], None],
    poll_interval: float,
    timeout: float,
) -> str:
    polls = int(timeout // poll_interval) if poll_interval else 0
    for _ in range(polls):
        sleep(poll_interval)
        inbox = bus.read_inbox(agent_name)
        if inbox:
            for message in inbox:
                if message.get("type") == "shutdown_request":
                    request_id = message.get("metadata", {}).get("request_id", "")
                    bus.send(name, "lead", "Shutting down gracefully.", "shutdown_response",
                             {"request_id": request_id, "approve": True})
                    print(f"  \033[35m[protocol] {name} approved shutdown in idle ({request_id})\033[0m")
                    return "shutdown"
            messages.append({"role": "user", "content": "<inbox>" + json.dumps(inbox) + "</inbox>"})
            print(f"  \033[36m[idle] {name} found inbox messages\033[0m")
            return "work"
        unclaimed = scan_unclaimed()
        if unclaimed:
            task = unclaimed[0]
            result = claim_task(task["id"], name)
            if "Claimed" in result:
                worktree_name = task.get("worktree")
                if worktree_context is not None:
                    worktree_context["path"] = str(worktree_path(worktree_name)) if worktree_name else None
                messages.append({"role": "user", "content": f"<auto-claimed>Task {task['id']}: {task['subject']}</auto-claimed>"})
                print(f"  \033[32m[idle] {name} auto-claimed: {task['subject']}\033[0m")
                return "work"
            print(f"  \033[33m[idle] {name} claim failed: {result}\033[0m")
    print(f"  \033[31m[idle] {name} timeout ({timeout}s)\033[0m")
    return "timeout"


def spawn_teammate_thread(
    state: TeamState,
    bus,
    llm: Callable,
    *,
    name: str,
    role: str,
    prompt: str,
    workdir: Path,
    handlers: dict,
    hooks,
    validate_name: Callable,
    guarded_tools: set[str],
    guarded_tool: Callable,
    idle: Callable,
    max_tokens: int,
    thread_factory: Callable = threading.Thread,
) -> str:
    try:
        validate_name(name, allow_lead=False)
    except (TypeError, ValueError) as exc:
        return f"Invalid teammate: {exc}"
    if not role.strip():
        return "Invalid teammate: role is required"
    if not prompt.strip():
        return "Invalid teammate: prompt is required"
    with state.lock:
        if name in state.active:
            return f"Teammate {name} already exists"
        state.active[name] = {"name": name, "role": role, "status": "running"}

    handler_snapshot = dict(handlers)
    system = (
        f"You are '{name}', role: {role}.\nWorkspace: {workdir}\n"
        f"Available tools: {', '.join(tool['name'] for tool in TEAM_TOOLS)}\n"
        "You must send your final result to lead using send_message.\n"
        "Do not create subagents or additional teammates.\n"
        "bash and write_file require permission from Lead. "
        "When permission is approved, you will execute the tool yourself. "
        "Do not claim that a protected operation succeeded until its tool_result confirms success."
    )

    def run():
        messages = [{"role": "user", "content": prompt}]
        summary = "Stopped after 10 teammate rounds."
        deferred_inbox: list[dict] = []
        worktree_context = {"path": None}
        waiting_plan = None
        try:
            while True:
                if len(messages) <= 3:
                    messages.insert(0, {"role": "user", "content": f"<identity>You are '{name}', role: {role}. Continue your work.</identity>"})
                work_completed = False
                lifecycle_done = False
                for _ in range(10):
                    inbox = deferred_inbox + bus.read_inbox(name)
                    deferred_inbox.clear()
                    for message in inbox:
                        msg_type = message.get("type", "message")
                        metadata = message.get("metadata", {})
                        request_id = metadata.get("request_id", "")
                        if msg_type == "shutdown_request":
                            bus.send(name, "lead", "Shutting down gracefully.", "shutdown_response", {"request_id": request_id, "approve": True})
                            lifecycle_done = True
                            break
                        if msg_type == "plan_approval_response" and request_id == waiting_plan:
                            waiting_plan = None
                            if metadata.get("approve", False):
                                messages.append({"role": "user", "content": "[Plan approved] Proceed with the task."})
                            else:
                                messages.append({"role": "user", "content": f"[Plan rejected] Feedback: {message['content']}"})
                    if lifecycle_done:
                        break
                    non_protocol = [message for message in inbox if message.get("type") == "message"]
                    if non_protocol:
                        messages.append({"role": "user", "content": f"<inbox>{json.dumps(non_protocol)}</inbox>"})
                    if waiting_plan:
                        continue
                    try:
                        response = llm(system=system, messages=messages[-20:], tools=TEAM_TOOLS, max_tokens=max_tokens)
                    except Exception as exc:
                        summary = f"Teammate error: {type(exc).__name__}: {exc}"
                        lifecycle_done = True
                        break
                    messages.append({"role": "assistant", "content": response.content})
                    if not any(getattr(block, "type", None) == "tool_use" for block in response.content):
                        summary = "\n".join(getattr(block, "text", "") for block in response.content if getattr(block, "type", None) == "text") or summary
                        work_completed = True
                        break
                    results = []
                    for block in response.content:
                        if getattr(block, "type", None) != "tool_use":
                            continue
                        handler = handler_snapshot.get(block.name)
                        if not handler:
                            output, is_error = f"Unknown tool: {block.name}", True
                        elif block.name == "submit_plan":
                            output = handler(**block.input)
                            match = re.search(r"\((req_[^)]+)\)", str(output))
                            waiting_plan = match.group(1) if match else None
                            is_error = not bool(match)
                            if is_error:
                                output = f"Invalid plan submission response: {output}"
                        elif block.name in guarded_tools:
                            cwd = Path(worktree_context["path"]) if worktree_context["path"] else None
                            scoped_handler = lambda **input: handler(**input, cwd=cwd)
                            output, is_error = guarded_tool(name, block, deferred_inbox, scoped_handler, cwd)
                            if not is_error:
                                hooks.trigger("PostToolUse", block, output)
                        else:
                            if block.name in {"bash", "read_file", "write_file"}:
                                cwd = Path(worktree_context["path"]) if worktree_context["path"] else None
                                output = handler(**block.input, cwd=cwd)
                            else:
                                output = handler(**block.input)
                            is_error = False
                        result = {"type": "tool_result", "tool_use_id": block.id, "content": str(output)}
                        if is_error:
                            result["is_error"] = True
                        results.append(result)
                        if waiting_plan:
                            break
                    messages.append({"role": "user", "content": results})
                    if waiting_plan:
                        break
                if lifecycle_done:
                    break
                if waiting_plan:
                    continue
                if not work_completed:
                    summary = "Stopped after 10 teammate tool rounds."
                    break
                with state.lock:
                    if name in state.active:
                        state.active[name]["status"] = "idle"
                idle_result = idle(name, messages, name, role, worktree_context)
                if idle_result == "work":
                    with state.lock:
                        if name in state.active:
                            state.active[name]["status"] = "running"
                    continue
                break
        except Exception as exc:
            summary = f"Teammate error: {type(exc).__name__}: {exc}"
        finally:
            try:
                bus.send(name, "lead", summary, "result")
            except Exception as exc:
                print(f"  \033[31m[teammate result error]{name}: {exc}\033[0m")
            with state.lock:
                state.active.pop(name, None)
            print(f"  \033[32m[teammate] {name} finished\033[0m")

    thread_factory(target=run, daemon=True).start()
    print(f"  \033[36m[teammate] {name} spawned as {role}\033[0m")
    return f"Teammate '{name}' spawned as {role}"
