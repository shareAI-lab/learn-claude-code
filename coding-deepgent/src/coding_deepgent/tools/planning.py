from __future__ import annotations

from typing import Any

from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime
from langgraph.types import Command

from coding_deepgent.state import PlanItem, PlanningState, normalize_plan_items

PLAN_REMINDER_INTERVAL = 3


def render_plan_items(items: list[dict[str, str]]) -> str:
    if not items:
        return "No session plan yet."

    lines: list[str] = []
    for raw_item in items:
        item = PlanItem(**raw_item)
        marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[item.status]
        line = f"{marker} {item.content}"
        if item.status == "in_progress" and item.active_form:
            line += f" ({item.active_form})"
        lines.append(line)

    completed = sum(1 for item in items if item["status"] == "completed")
    lines.append(f"\n({completed}/{len(items)} completed)")
    return "\n".join(lines)


def reminder_text(items: list[dict[str, str]], rounds_since_update: int) -> str | None:
    if not items or rounds_since_update < PLAN_REMINDER_INTERVAL:
        return None
    return "<reminder>Refresh your current plan before continuing.</reminder>"


def todo(items: list[dict[str, Any]], runtime: ToolRuntime[None, PlanningState]) -> Command:
    normalized = normalize_plan_items(items)
    rendered = render_plan_items(normalized)
    return Command(
        update={
            "plan_items": normalized,
            "rounds_since_update": 0,
            "updated_this_turn": True,
            "messages": [ToolMessage(content=rendered, tool_call_id=runtime.tool_call_id)],
        }
    )
