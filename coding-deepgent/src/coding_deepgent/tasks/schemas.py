from __future__ import annotations

from typing import Literal

from langchain.tools import ToolRuntime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TaskStatus = Literal["pending", "in_progress", "blocked", "completed", "cancelled"]
TERMINAL_TASK_STATUSES: frozenset[TaskStatus] = frozenset({"completed", "cancelled"})
ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    "pending": frozenset({"in_progress", "blocked", "cancelled"}),
    "in_progress": frozenset({"blocked", "completed", "cancelled"}),
    "blocked": frozenset({"pending", "in_progress", "cancelled"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}


class TaskRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str = Field(..., min_length=1)
    description: str = ""
    status: TaskStatus = "pending"
    depends_on: list[str] = Field(default_factory=list)
    owner: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("id", "title", "description", mode="before")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return str(value).strip()

    @field_validator("title")
    @classmethod
    def _title_must_not_be_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("title required")
        return value


class TaskCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    title: str = Field(..., min_length=1)
    description: str = ""
    depends_on: list[str] = Field(default_factory=list)
    owner: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    runtime: ToolRuntime


class TaskGetInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    task_id: str = Field(..., min_length=1)
    runtime: ToolRuntime


class TaskListInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    include_terminal: bool = False
    runtime: ToolRuntime


class TaskUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    task_id: str = Field(..., min_length=1)
    status: TaskStatus | None = None
    depends_on: list[str] | None = None
    owner: str | None = None
    metadata: dict[str, str] | None = None
    runtime: ToolRuntime

    @model_validator(mode="after")
    def _has_update(self) -> "TaskUpdateInput":
        if (
            self.status is None
            and self.depends_on is None
            and self.owner is None
            and self.metadata is None
        ):
            raise ValueError("at least one update field is required")
        return self
