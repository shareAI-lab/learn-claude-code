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
    WritePlanInput,
    PlanItemInput,
    normalize_plan_items,
)

__all__ = [
    "PLAN_REMINDER_INTERVAL",
    "_write_plan_command",
    "reminder_text",
    "render_plan_items",
    "write_plan",
]


def _write_plan_command(
    items: list[PlanItemInput],
    tool_call_id: str | None = None,
) -> Command:
    """Implementation helper for the write_plan tool."""

    if tool_call_id is None:
        raise ValueError("tool_call_id is required for write_plan tool execution")

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
    "write_plan",
    args_schema=WritePlanInput,
    description=(
        "Create or replace the session plan for complex multi-step work. Use this "
        "when explicit progress tracking helps; skip it for simple one-step or "
        "purely conversational requests. Input must be the full current plan in "
        "items[]. Do not call this tool multiple times in parallel within the same response."
    ),
)
def write_plan(
    items: list[PlanItemInput],
    tool_call_id: str | None = None,
) -> Command:
    """Create or replace the session plan for complex multi-step work."""

    return _write_plan_command(items, tool_call_id)
