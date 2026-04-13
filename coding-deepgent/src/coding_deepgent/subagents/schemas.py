from __future__ import annotations

from typing import Literal

from langchain.tools import ToolRuntime
from pydantic import BaseModel, ConfigDict, Field, field_validator

SubagentType = Literal["general", "verifier"]


class RunSubagentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    task: str = Field(
        ...,
        min_length=1,
        description="Single task for a synchronous stateless subagent.",
    )
    runtime: ToolRuntime
    agent_type: SubagentType = Field(
        default="general", description="Bounded local subagent type."
    )
    max_turns: int = Field(
        default=1,
        ge=1,
        le=1,
        description="Stage 6-min supports exactly one synchronous turn.",
    )

    @field_validator("task")
    @classmethod
    def _task_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("task required")
        return value
