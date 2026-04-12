from __future__ import annotations

from typing import Annotated, Literal

from langchain.tools import InjectedToolCallId
from pydantic import BaseModel, ConfigDict, Field, field_validator


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
