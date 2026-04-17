from __future__ import annotations

import re
from typing import Literal

from langchain.tools import ToolRuntime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MemoryType = Literal["user", "feedback", "project", "reference"]
MEMORY_TYPE_ORDER: tuple[MemoryType, ...] = (
    "feedback",
    "project",
    "reference",
    "user",
)
MEMORY_TYPE_PRIORITY: dict[MemoryType, int] = {
    memory_type: index for index, memory_type in enumerate(MEMORY_TYPE_ORDER)
}
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class _MemoryFields(BaseModel):
    type: MemoryType = Field(..., description="Long-term memory type.")
    source: str = Field(default="agent", description="Source label for this memory entry.")

    profile: str | None = Field(
        default=None, description="Durable user background or collaboration profile."
    )
    why_it_matters: str | None = Field(
        default=None, description="Why this user profile matters for collaboration."
    )

    rule: str | None = Field(
        default=None, description="Behavioral rule validated or corrected by the user."
    )
    why: str | None = Field(
        default=None, description="Why this memory matters or why the rule/decision exists."
    )
    how_to_apply: str | None = Field(
        default=None, description="How to apply this memory in future work."
    )

    fact_or_decision: str | None = Field(
        default=None, description="Non-derivable project fact or decision."
    )
    effective_date: str | None = Field(
        default=None,
        description="Absolute effective date in YYYY-MM-DD when time is part of the project memory.",
    )

    label: str | None = Field(
        default=None, description="Short label for an external reference."
    )
    pointer: str | None = Field(
        default=None, description="External pointer such as a URL, channel, or system identifier."
    )
    purpose: str | None = Field(
        default=None, description="What the external reference is used for."
    )

    @field_validator(
        "source",
        "profile",
        "why_it_matters",
        "rule",
        "why",
        "how_to_apply",
        "fact_or_decision",
        "effective_date",
        "label",
        "pointer",
        "purpose",
        mode="before",
    )
    @classmethod
    def _strip_optional_text(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            raise ValueError("value required")
        return value

    @model_validator(mode="after")
    def _validate_type_shape(self) -> _MemoryFields:
        required_by_type: dict[MemoryType, tuple[str, ...]] = {
            "user": ("profile", "why_it_matters", "how_to_apply"),
            "feedback": ("rule", "why", "how_to_apply"),
            "project": ("fact_or_decision", "why", "how_to_apply"),
            "reference": ("label", "pointer", "purpose", "how_to_apply"),
        }
        allowed_by_type: dict[MemoryType, set[str]] = {
            "user": {"profile", "why_it_matters", "how_to_apply"},
            "feedback": {"rule", "why", "how_to_apply"},
            "project": {"fact_or_decision", "why", "how_to_apply", "effective_date"},
            "reference": {"label", "pointer", "purpose", "how_to_apply"},
        }
        for field_name in required_by_type[self.type]:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required when type={self.type}")

        for field_name in (
            "profile",
            "why_it_matters",
            "rule",
            "why",
            "how_to_apply",
            "fact_or_decision",
            "effective_date",
            "label",
            "pointer",
            "purpose",
        ):
            if (
                field_name not in allowed_by_type[self.type]
                and getattr(self, field_name) is not None
            ):
                raise ValueError(f"{field_name} is not allowed when type={self.type}")

        if self.effective_date is not None and not _DATE_PATTERN.fullmatch(
            self.effective_date
        ):
            raise ValueError("effective_date must use YYYY-MM-DD")
        return self


class MemoryRecord(_MemoryFields):
    model_config = ConfigDict(extra="forbid")

    def identity_text(self) -> str:
        if self.type == "user":
            return "\n".join(
                (self.profile or "", self.why_it_matters or "", self.how_to_apply or "")
            )
        if self.type == "feedback":
            return "\n".join((self.rule or "", self.why or "", self.how_to_apply or ""))
        if self.type == "project":
            return "\n".join(
                (
                    self.fact_or_decision or "",
                    self.why or "",
                    self.how_to_apply or "",
                    self.effective_date or "",
                )
            )
        return "\n".join(
            (
                self.label or "",
                self.pointer or "",
                self.purpose or "",
                self.how_to_apply or "",
            )
        )

    def search_text(self) -> str:
        return self.identity_text()

    @property
    def priority(self) -> int:
        return MEMORY_TYPE_PRIORITY[self.type]


class SaveMemoryInput(_MemoryFields):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    runtime: ToolRuntime


class ListMemoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    type: MemoryType | None = Field(
        default=None,
        description="Optional memory type filter. Omit to list every long-term memory type.",
    )
    limit: int = Field(
        default=20, ge=1, le=100, description="Maximum number of memory entries to return."
    )
    runtime: ToolRuntime


class DeleteMemoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    type: MemoryType = Field(..., description="Memory type that owns the entry.")
    key: str = Field(..., min_length=1, description="Exact memory entry key to delete.")
    runtime: ToolRuntime

    @field_validator("key")
    @classmethod
    def _key_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value required")
        return value
