from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PermissionRuleSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(..., min_length=1)
    content: str | None = None
    domain: str | None = None
    capability_source: str | None = None
    trusted: bool | None = None
    rule_source: str = "settings"

    @field_validator(
        "tool_name",
        "content",
        "domain",
        "capability_source",
        "rule_source",
    )
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("value required")
        return stripped
