from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain.agents import AgentState
from typing_extensions import NotRequired


@dataclass
class PlanItem:
    content: str
    status: str = "pending"
    active_form: str = ""


class PlanningState(AgentState):
    plan_items: NotRequired[list[dict[str, str]]]
    rounds_since_update: NotRequired[int]
    updated_this_turn: NotRequired[bool]


VALID_STATUSES = {"pending", "in_progress", "completed"}


def default_session_state() -> dict[str, Any]:
    return {
        "plan_items": [],
        "rounds_since_update": 0,
        "updated_this_turn": False,
    }


def normalize_plan_items(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    if len(items) > 12:
        raise ValueError("Keep the session plan short (max 12 items)")

    normalized: list[dict[str, str]] = []
    in_progress_count = 0
    for index, raw_item in enumerate(items):
        content = str(raw_item.get("content", "")).strip()
        status = str(raw_item.get("status", "pending")).lower()
        active_form = str(raw_item.get("activeForm", raw_item.get("active_form", ""))).strip()

        if not content:
            raise ValueError(f"Item {index}: content required")
        if status not in VALID_STATUSES:
            raise ValueError(f"Item {index}: invalid status '{status}'")
        if status == "in_progress":
            in_progress_count += 1

        normalized.append(
            {
                "content": content,
                "status": status,
                "active_form": active_form,
            }
        )

    if in_progress_count > 1:
        raise ValueError("Only one plan item can be in_progress")

    return normalized
