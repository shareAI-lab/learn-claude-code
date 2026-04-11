from __future__ import annotations

from langchain.messages import ToolMessage
from langchain.tools import tool
from langgraph.types import Command

from coding_deepgent.renderers.planning import render_plan_items
from coding_deepgent.state import (
    TodoInput,
    TodoPlanItemInput,
    normalize_plan_items,
)


def _todo_command(
    items: list[TodoPlanItemInput],
    tool_call_id: str | None = None,
) -> Command:
    """Implementation helper for the todo tool."""

    if tool_call_id is None:
        raise ValueError("tool_call_id is required for todo tool execution")

    normalized = normalize_plan_items(items)

    rendered = render_plan_items(normalized)
    return Command(
        update={
            "items": normalized,
            "rounds_since_update": 0,
            "messages": [ToolMessage(content=rendered, tool_call_id=tool_call_id)],
        }
    )


@tool(
    "todo",
    args_schema=TodoInput,
    description=(
        "Create or replace the session plan for complex multi-step work. Use this "
        "when explicit progress tracking helps; skip it for simple one-step or "
        "purely conversational requests. Input must be the full current plan in "
        "items[]. Do not call this tool multiple times in parallel within the same response."
    ),
)
def todo(
    items: list[TodoPlanItemInput],
    tool_call_id: str | None = None,
) -> Command:
    """Create or replace the session plan for complex multi-step work."""

    return _todo_command(items, tool_call_id)
