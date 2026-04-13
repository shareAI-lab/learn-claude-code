from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

HookEventName = Literal[
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PermissionDenied",
]
HookDecision = Literal["approve", "block"]


class HookPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: HookEventName
    data: dict[str, object] = Field(default_factory=dict)


class HookResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    continue_: bool = Field(default=True, alias="continue")
    decision: HookDecision | None = None
    reason: str | None = None
    additional_context: str | None = None
