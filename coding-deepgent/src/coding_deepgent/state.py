from __future__ import annotations

from typing import Annotated, Any, Literal

from langchain.agents import AgentState
from langchain.tools import InjectedToolCallId
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import NotRequired, TypedDict


class PlanItemState(TypedDict):
    content: str
    status: Literal["pending", "in_progress", "completed"]
    activeForm: NotRequired[str]


class PlanningState(AgentState):
    items: NotRequired[list[PlanItemState]]
    rounds_since_update: NotRequired[int]


def default_session_state() -> dict[str, Any]:
    return {
        "items": [],
        "rounds_since_update": 0,
    }


class TodoPlanItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(
        ...,
        min_length=1,
        description="Non-empty description of this plan step.",
    )
    status: Literal["pending", "in_progress", "completed"] = Field(
        ...,
        description="Current step status. Exactly one item should be in_progress.",
    )
    activeForm: str | None = Field(
        default=None,
        description="Short gerund phrase for the current in-progress step.",
    )

    @field_validator("content")
    @classmethod
    def _content_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content required")
        return value

    @field_validator("activeForm")
    @classmethod
    def _active_form_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class TodoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TodoPlanItemInput] = Field(
        ...,
        min_length=1,
        max_length=12,
        description=(
            "Complete current plan. Every item must have content and status; "
            "use pending, in_progress, or completed."
        ),
    )
    tool_call_id: Annotated[str | None, InjectedToolCallId] = None


def normalize_plan_items(
    items: list[TodoPlanItemInput | dict[str, Any]],
) -> list[PlanItemState]:
    if len(items) > 12:
        raise ValueError("Keep the session plan short (max 12 items)")

    validated = TodoInput(items=items)

    normalized: list[PlanItemState] = []
    in_progress_count = 0
    for item_input in validated.items:
        if item_input.status == "in_progress":
            in_progress_count += 1

        item: PlanItemState = {
            "content": item_input.content,
            "status": item_input.status,
        }
        if item_input.activeForm:
            item["activeForm"] = item_input.activeForm
        normalized.append(item)

    if in_progress_count > 1:
        raise ValueError("Only one plan item can be in_progress")

    return normalized
