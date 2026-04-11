from __future__ import annotations

from langchain.messages import ToolMessage
from langchain.tools import tool
from langgraph.types import Command

from coding_deepgent.renderers.planning import (
    PLAN_REMINDER_INTERVAL,
    reminder_text,
    render_plan_items,
)
from coding_deepgent.state import (
    TodoItemInput,
    TodoWriteInput,
    normalize_todos,
)

__all__ = [
    "PLAN_REMINDER_INTERVAL",
    "_todo_write_command",
    "reminder_text",
    "render_plan_items",
    "todo_write",
]


def _todo_write_command(
    todos: list[TodoItemInput],
    tool_call_id: str | None = None,
) -> Command:
    """Implementation helper for the TodoWrite tool."""

    if tool_call_id is None:
        raise ValueError("tool_call_id is required for TodoWrite tool execution")

    normalized = normalize_todos(todos)

    rendered = render_plan_items(normalized)
    return Command(
        update={
            "todos": normalized,
            "rounds_since_update": 0,
            "messages": [ToolMessage(content=rendered, tool_call_id=tool_call_id)],
        }
    )


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
