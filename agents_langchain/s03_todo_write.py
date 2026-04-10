#!/usr/bin/env python3
# LangChain track: planning -- keep session plan state outside the model's head.
"""
s03_todo_write.py - Session Planning with LangChain tools

LangChain owns the model/tool loop, but it does not remove the need for visible
harness state.  ``TodoManager`` remains local Python state and is exposed through
a tool, matching the original chapter's "plan outside the model's head" lesson.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from .common import (
        WORKDIR,
        bash,
        create_agent_runtime,
        edit_file,
        extract_text,
        invoke_and_append,
        read_file,
        write_file,
    )
except ImportError:
    from common import (
        WORKDIR,
        bash,
        create_agent_runtime,
        edit_file,
        extract_text,
        invoke_and_append,
        read_file,
        write_file,
    )

PLAN_REMINDER_INTERVAL = 3
SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use the todo tool for multi-step work.
Keep exactly one step in_progress when a task has multiple steps.
Refresh the plan as work advances. Prefer tools over prose."""


@dataclass
class PlanItem:
    content: str
    status: str = "pending"
    active_form: str = ""


@dataclass
class PlanningState:
    items: list[PlanItem] = field(default_factory=list)
    rounds_since_update: int = 0


class TodoManager:
    def __init__(self) -> None:
        self.state = PlanningState()

    def update(self, items: list[dict[str, Any]]) -> str:
        if len(items) > 12:
            raise ValueError("Keep the session plan short (max 12 items)")

        normalized: list[PlanItem] = []
        in_progress_count = 0
        for index, raw_item in enumerate(items):
            content = str(raw_item.get("content", "")).strip()
            status = str(raw_item.get("status", "pending")).lower()
            active_form = str(raw_item.get("activeForm", "")).strip()

            if not content:
                raise ValueError(f"Item {index}: content required")
            if status not in {"pending", "in_progress", "completed"}:
                raise ValueError(f"Item {index}: invalid status '{status}'")
            if status == "in_progress":
                in_progress_count += 1

            normalized.append(PlanItem(content=content, status=status, active_form=active_form))

        if in_progress_count > 1:
            raise ValueError("Only one plan item can be in_progress")

        self.state.items = normalized
        self.state.rounds_since_update = 0
        return self.render()

    def note_round_without_update(self) -> None:
        self.state.rounds_since_update += 1

    def reminder(self) -> str | None:
        if not self.state.items:
            return None
        if self.state.rounds_since_update < PLAN_REMINDER_INTERVAL:
            return None
        return "<reminder>Refresh your current plan before continuing.</reminder>"

    def render(self) -> str:
        if not self.state.items:
            return "No session plan yet."

        lines: list[str] = []
        for item in self.state.items:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[item.status]
            line = f"{marker} {item.content}"
            if item.status == "in_progress" and item.active_form:
                line += f" ({item.active_form})"
            lines.append(line)

        completed = sum(1 for item in self.state.items if item.status == "completed")
        lines.append(f"\n({completed}/{len(self.state.items)} completed)")
        return "\n".join(lines)


TODO = TodoManager()


def todo(items: list[dict[str, Any]]) -> str:
    """Rewrite the current session plan for multi-step work."""

    return TODO.update(items)


TOOLS = [bash, read_file, write_file, edit_file, todo]


def build_agent():
    return create_agent_runtime(SYSTEM, TOOLS)


def agent_loop(messages: list[dict[str, Any]]) -> str:
    # If the plan has gone stale, inject a harness-owned reminder before LangChain runs.
    reminder = TODO.reminder()
    input_messages = list(messages)
    if reminder:
        input_messages.append({"role": "user", "content": reminder})

    final_text = invoke_and_append(build_agent(), input_messages)
    messages.append({"role": "assistant", "content": final_text})
    TODO.note_round_without_update()
    return final_text


if __name__ == "__main__":
    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input("\033[36ms03-lc >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})
        try:
            final = agent_loop(history)
        except RuntimeError as exc:
            print(f"Error: {exc}")
            continue
        print(extract_text(final) or "(no response)")
        print()
