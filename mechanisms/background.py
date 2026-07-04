"""
mechanisms/background.py — Background Tasks mechanism, sourced from s13 (origin).

First-appearance rule: s13 introduces this inline. s14-s16 reuse it verbatim
except for ``execute_tool`` (which is lesson-specific — the handler dict
differs per lesson). s20 carries a variant (``start_background_task(block,
handlers)`` accepts handlers as a parameter instead of a closure) and keeps
its own inline version.

Design — ``is_slow_operation`` and ``should_run_background`` are pure
module-level functions (no state). ``make_background(execute_fn)`` is a
factory that returns ``(start_background_task, collect_background_results,
has_pending_background)`` with closure-private state (counter + dicts + lock).
Each lesson passes its own ``execute_tool`` so the handler dict stays local.
"""

import threading


def is_slow_operation(tool_name: str, tool_input: dict) -> bool:
    """Fallback heuristic: commands likely to take > 30s."""
    if tool_name != "bash":
        return False
    cmd = tool_input.get("command", "").lower()
    slow_keywords = ["install", "build", "test", "deploy", "compile",
                     "docker build", "pip install", "npm install",
                     "cargo build", "pytest", "make"]
    return any(kw in cmd for kw in slow_keywords)


def should_run_background(tool_name: str, tool_input: dict) -> bool:
    """Model explicit request takes priority; fallback to heuristic."""
    if tool_input.get("run_in_background"):
        return True
    return is_slow_operation(tool_name, tool_input)


def make_background(execute_fn):
    """Build background-task closures bound to *execute_fn*.

    Args:
        execute_fn: callable(block) -> str. Each lesson passes its own
            ``execute_tool`` which knows the lesson-specific handler dict.

    Returns:
        (start_background_task, collect_background_results, has_pending_background)
    """
    state = {"counter": 0, "tasks": {}, "results": {}}
    lock = threading.Lock()

    def start_background_task(block) -> str:
        """Run tool in a daemon thread. Returns background task ID."""
        state["counter"] += 1
        bg_id = f"bg_{state['counter']:04d}"
        cmd = block.input.get("command", block.name)

        def worker():
            result = execute_fn(block)
            with lock:
                state["tasks"][bg_id]["status"] = "completed"
                state["results"][bg_id] = result

        with lock:
            state["tasks"][bg_id] = {
                "tool_use_id": block.id,
                "command": cmd,
                "status": "running",
            }
        threading.Thread(target=worker, daemon=True).start()
        print(f"  \033[33m[background] dispatched {bg_id}: {cmd[:40]}\033[0m")
        return bg_id

    def collect_background_results() -> list[str]:
        """Collect completed background results as task_notification messages."""
        with lock:
            ready_ids = [bid for bid, task in state["tasks"].items()
                         if task["status"] == "completed"]
        notifications = []
        for bg_id in ready_ids:
            with lock:
                task = state["tasks"].pop(bg_id)
                output = state["results"].pop(bg_id, "")
            summary = output[:200] if len(output) > 200 else output
            notifications.append(
                f"<task_notification>\n"
                f"  <task_id>{bg_id}</task_id>\n"
                f"  <status>completed</status>\n"
                f"  <command>{task['command']}</command>\n"
                f"  <summary>{summary}</summary>\n"
                f"</task_notification>")
            print(f"  \033[32m[background done] {bg_id}: "
                  f"{task['command'][:40]} ({len(output)} chars)\033[0m")
        return notifications

    def has_pending_background() -> bool:
        """Non-destructive: True if any completed task waits to be collected."""
        with lock:
            return any(t["status"] == "completed" for t in state["tasks"].values())

    return start_background_task, collect_background_results, has_pending_background
