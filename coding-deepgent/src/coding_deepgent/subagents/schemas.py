from __future__ import annotations

from typing import Literal

from langchain.tools import ToolRuntime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    plan_id: str | None = Field(
        default=None,
        min_length=1,
        description="Durable plan artifact id. Required for verifier subagents.",
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

    @model_validator(mode="after")
    def _verifier_requires_plan(self) -> "RunSubagentInput":
        if self.agent_type == "verifier" and self.plan_id is None:
            raise ValueError("verifier subagents require plan_id")
        return self


class VerifierSubagentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_type: Literal["verifier"] = "verifier"
    plan_id: str = Field(..., min_length=1)
    plan_title: str = Field(..., min_length=1)
    verification: str = Field(..., min_length=1)
    task_ids: list[str] = Field(default_factory=list)
    tool_allowlist: list[str] = Field(default_factory=list)
    content: str = Field(..., min_length=1)
