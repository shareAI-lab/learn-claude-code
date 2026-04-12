from __future__ import annotations

from collections.abc import Mapping, Sequence

from langchain.tools import tool
from langgraph.types import Command

from coding_deepgent.todo.renderers import (
    PLAN_REMINDER_INTERVAL,
    reminder_text,
    render_plan_items,
)
from coding_deepgent.todo.schemas import TodoItemInput, TodoWriteInput
from coding_deepgent.todo.service import build_todo_update

__all__ = [
    "PLAN_REMINDER_INTERVAL",
    "_todo_write_command",
    "reminder_text",
    "render_plan_items",
    "todo_write",
]


def _todo_write_command(
    todos: Sequence[TodoItemInput | Mapping[str, object]],
    tool_call_id: str | None = None,
) -> Command:
    """Implementation helper for the TodoWrite tool."""

    return build_todo_update(todos, tool_call_id=tool_call_id)


@tool(
    "TodoWrite",
    args_schema=TodoWriteInput,
    description=(
        "Create or replace the current session todo list for complex multi-step work. Use this proactively "
        "when explicit progress tracking helps; skip it for simple one-step or "
        "purely conversational requests. Input must be the full current todo list in "
        "todos[]. Every todo requires content, status, and activeForm. Do not call "
        "TodoWrite multiple times in parallel within the same response."
    ),
)
def todo_write(
    todos: list[TodoItemInput],
    tool_call_id: str | None = None,
) -> Command:
    """Create or replace the current session todo list for complex multi-step work."""

    return _todo_write_command(todos, tool_call_id)
