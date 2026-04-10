#!/usr/bin/env python3
# LangChain track: planning -- keep the current session plan outside the model's hidden state.
"""
s03_todo_write.py - Session Planning with LangChain tools

LangChain owns the agent runtime; the harness still owns visible Todo state.  The
model updates the plan through a tool, and the next turn's system prompt includes
the current rendered plan plus reminders when the plan has gone stale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool

try:
    from agents_langchain._common import (
        WORKDIR,
        build_openai_chat_model,
        edit_file as edit_file_impl,
        latest_text,
        read_file as read_file_impl,
        run_bash,
        write_file as write_file_impl,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script fallback
    from _common import (
        WORKDIR,
        build_openai_chat_model,
        edit_file as edit_file_impl,
        latest_text,
        read_file as read_file_impl,
        run_bash,
        write_file as write_file_impl,
    )

PLAN_REMINDER_INTERVAL = 3
BASE_SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use update_todo for multi-step work.
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
        self.update_count = 0

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
        self.update_count += 1
        return self.render()

    def note_round_without_update(self) -> None:
        self.state.rounds_since_update += 1

    def reminder(self) -> str | None:
        if not self.state.items:
            return None
        if self.state.rounds_since_update < PLAN_REMINDER_INTERVAL:
            return None
        return "<reminder>Refresh your current plan with update_todo before continuing.</reminder>"

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


@tool
def bash(command: str) -> str:
    """Run a shell command in the current workspace."""

    return run_bash(command)


@tool
def read_file(path: str, limit: int | None = None) -> str:
    """Read file contents from the workspace, optionally limiting lines."""

    return read_file_impl(path, limit)


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a workspace file."""

    return write_file_impl(path, content)


@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace one exact text occurrence in a workspace file."""

    return edit_file_impl(path, old_text, new_text)


@tool
def update_todo(items: list[dict[str, Any]]) -> str:
    """Rewrite the current short session plan with pending/in_progress/completed items."""

    return TODO.update(items)


TOOLS = [bash, read_file, write_file, edit_file, update_todo]


def build_system_prompt() -> str:
    reminder = TODO.reminder()
    parts = [BASE_SYSTEM, "\nCurrent session plan:\n" + TODO.render()]
    if reminder:
        parts.append(reminder)
    return "\n\n".join(parts)


def invoke_agent(messages: list[Any], query: str) -> list[Any]:
    before = TODO.update_count
    agent = create_agent(build_openai_chat_model(), tools=TOOLS, system_prompt=build_system_prompt())
    result = agent.invoke({"messages": [*messages, {"role": "user", "content": query}]})
    if TODO.update_count == before:
        TODO.note_round_without_update()
    return list(result["messages"])


if __name__ == "__main__":
    history: list[Any] = []
    while True:
        try:
            query = input("\033[36mlc-s03 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history = invoke_agent(history, query)
        print(latest_text(history))
        print()
