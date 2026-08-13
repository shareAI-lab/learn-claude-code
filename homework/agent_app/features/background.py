"""Owned state and worker lifecycle for background tool execution."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable
from xml.sax.saxutils import escape

from ..tools.executor import execute_tool


@dataclass(slots=True)
class BackgroundState:
    counter: int = 0
    tasks: dict[str, dict] = field(default_factory=dict)
    results: dict[str, str] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)


def start_background_task(
    state: BackgroundState,
    block,
    handlers: dict,
    *,
    post_tool: Callable,
    persist_output: Callable[[str, str], str],
) -> str:
    handler_snapshot = dict(handlers)

    with state.lock:
        state.counter += 1
        background_id = f"bg_{state.counter:04d}"
        state.tasks[background_id] = {
            "id": background_id,
            "tool_use_id": block.id,
            "tool_name": block.name,
            "command": block.input.get("command", ""),
            "status": "running",
            "error": None,
        }

    def worker():
        status = "completed"
        error = None
        output = ""
        try:
            output = str(execute_tool(block, handler_snapshot))
            post_tool(block, output)
            output = persist_output(block.id, output)
        except Exception as exc:
            status = "failed"
            error = f"{type(exc).__name__}: {exc}"
            print(f"  \033[31m[background error] {background_id}: {error}\033[0m")
        finally:
            with state.lock:
                task = state.tasks.get(background_id)
                if task:
                    task["status"] = status
                    task["error"] = error
                    state.results[background_id] = output

    threading.Thread(target=worker, daemon=True).start()
    return background_id


def collect_background_results(state: BackgroundState) -> list[str]:
    with state.lock:
        ready_ids = [
            background_id
            for background_id, task in state.tasks.items()
            if task["status"] in {"completed", "failed"}
        ]

    notifications = []
    for background_id in ready_ids:
        with state.lock:
            task = state.tasks.pop(background_id)
            output = state.results.pop(background_id, "")
        summary_source = task.get("error") or output
        summary = summary_source[:200] if len(summary_source) > 200 else summary_source
        notifications.append(
            f"<task_notification>\n"
            f"  <task_id>{escape(str(background_id))}</task_id>\n"
            f"  <status>{escape(str(task['status']))}</status>\n"
            f"  <command>{escape(str(task['command']))}</command>\n"
            f"  <summary>{escape(str(summary))}</summary>\n"
            f"</task_notification>"
        )
        print(
            f"  \033[32m[background done] {background_id}: "
            f"{task['command'][:40]} ({len(output)} chars)\033[0m"
        )
    return notifications
