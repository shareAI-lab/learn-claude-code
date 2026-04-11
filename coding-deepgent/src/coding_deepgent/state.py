from __future__ import annotations

from typing import Annotated, Any, Literal

from langchain.agents import AgentState
from langchain.tools import InjectedToolCallId
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import NotRequired, TypedDict


class TodoItemState(TypedDict):
    content: str
    status: Literal["pending", "in_progress", "completed"]
    activeForm: str


class PlanningState(AgentState):
    todos: NotRequired[list[TodoItemState]]
    rounds_since_update: NotRequired[int]


def default_session_state() -> dict[str, Any]:
    return {
        "todos": [],
        "rounds_since_update": 0,
    }


class TodoItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(
        ...,
        min_length=1,
        description="Imperative description of this todo item.",
    )
    status: Literal["pending", "in_progress", "completed"] = Field(
        ...,
        description="Current todo status. Exactly one item should be in_progress.",
    )
    activeForm: str = Field(
        ...,
        min_length=1,
        description="Present-continuous form shown while this todo is active.",
    )

    @field_validator("content", "activeForm")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value required")
        return value


class TodoWriteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    todos: list[TodoItemInput] = Field(
        ...,
        min_length=1,
        max_length=12,
        description=(
            "Complete current todo list. Every todo must have content, status, "
            "and activeForm; use pending, in_progress, or completed."
        ),
    )
    tool_call_id: Annotated[str | None, InjectedToolCallId] = None


def normalize_todos(
    todos: list[TodoItemInput | dict[str, Any]],
) -> list[TodoItemState]:
    if len(todos) > 12:
        raise ValueError("Keep the todo list short (max 12 todos)")

    validated = TodoWriteInput(todos=todos)

    normalized: list[TodoItemState] = []
    in_progress_count = 0
    for todo_input in validated.todos:
        if todo_input.status == "in_progress":
            in_progress_count += 1

        normalized.append(
            {
                "content": todo_input.content,
                "status": todo_input.status,
                "activeForm": todo_input.activeForm,
            }
        )

    if in_progress_count > 1:
        raise ValueError("Only one todo item can be in_progress")

    return normalized
