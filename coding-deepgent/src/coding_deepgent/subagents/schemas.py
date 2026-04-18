from __future__ import annotations

from typing import Literal

from langchain.tools import ToolRuntime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SubagentType = Literal["general", "verifier"]


class AgentDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_type: SubagentType
    description: str = Field(..., min_length=1)
    when_to_use: str = Field(..., min_length=1)
    tool_allowlist: tuple[str, ...] = Field(default_factory=tuple)
    disallowed_tools: tuple[str, ...] = Field(default_factory=tuple)
    max_turns: int = Field(..., ge=1, le=25)
    model_profile: str | None = Field(default=None, min_length=1)

    @field_validator(
        "description",
        "when_to_use",
        "model_profile",
        mode="before",
    )
    @classmethod
    def _optional_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            raise ValueError("value required")
        return value

    @field_validator("tool_allowlist", "disallowed_tools")
    @classmethod
    def _tools_must_not_be_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(item.strip() for item in value)
        if any(not item for item in cleaned):
            raise ValueError("tool names must not be blank")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("tool names must be unique")
        return cleaned

    @model_validator(mode="after")
    def _tool_sets_must_not_overlap(self) -> "AgentDefinition":
        overlap = set(self.tool_allowlist) & set(self.disallowed_tools)
        if overlap:
            raise ValueError("tool_allowlist and disallowed_tools overlap")
        return self


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
        default=25,
        ge=1,
        le=25,
        description="Requested child turn ceiling. Agent definitions may impose a lower limit.",
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


class RunForkInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    intent: str = Field(
        ...,
        min_length=1,
        description="Short branch-specific intent for a same-config sibling fork.",
    )
    runtime: ToolRuntime
    max_turns: int = Field(
        default=25,
        ge=1,
        le=25,
        description="Requested child turn ceiling for the forked sibling branch.",
    )

    @field_validator("intent")
    @classmethod
    def _intent_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("intent required")
        return value


class ToolSurfaceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    visible_order: int = Field(..., ge=0)
    schema_fingerprint: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)


class ToolPoolIdentitySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fingerprint: str = Field(..., min_length=1)
    tools: list[ToolSurfaceSnapshot] = Field(default_factory=list)


class ForkPlaceholderLayout(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(..., min_length=1)
    paired_tool_call_ids: list[str] = Field(default_factory=list)
    replacement_state_hook: str = Field(..., min_length=1)


class VerifierSubagentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_type: Literal["verifier"] = "verifier"
    plan_id: str = Field(..., min_length=1)
    plan_title: str = Field(..., min_length=1)
    verification: str = Field(..., min_length=1)
    task_ids: list[str] = Field(default_factory=list)
    tool_allowlist: list[str] = Field(default_factory=list)
    content: str = Field(..., min_length=1)
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    total_duration_ms: int = Field(..., ge=0)
    total_tool_use_count: int = Field(..., ge=0)


class SubagentResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_type: SubagentType
    content: str = Field(..., min_length=1)
    tool_allowlist: list[str] = Field(default_factory=list)
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    total_duration_ms: int = Field(..., ge=0)
    total_tool_use_count: int = Field(..., ge=0)


class ForkResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["fork"] = "fork"
    content: str = Field(..., min_length=1)
    fork_run_id: str = Field(..., min_length=1)
    parent_thread_id: str = Field(..., min_length=1)
    child_thread_id: str = Field(..., min_length=1)
    rendered_prompt_fingerprint: str = Field(..., min_length=1)
    tool_pool_identity: ToolPoolIdentitySnapshot
    placeholder_layout: ForkPlaceholderLayout
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    total_duration_ms: int = Field(..., ge=0)
    total_tool_use_count: int = Field(..., ge=0)
