from __future__ import annotations

from typing import Literal

from langchain.tools import ToolRuntime
from pydantic import BaseModel, ConfigDict, Field, field_validator

MemoryNamespace = Literal["project", "user", "local"]


class MemoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., min_length=1, description="Reusable memory content.")
    namespace: MemoryNamespace = Field(
        default="project", description="Long-term memory namespace."
    )
    source: str = Field(default="agent", description="Source that saved this memory.")

    @field_validator("content", "source")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value required")
        return value


class SaveMemoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    content: str = Field(
        ...,
        min_length=1,
        description="Durable reusable knowledge or preference to store as long-term memory. Do not store current todos, transient plans, or task status.",
    )
    namespace: MemoryNamespace = Field(
        default="project",
        description="Memory namespace. Use project for repository facts, user for durable user preferences, and local for machine-local notes.",
    )
    source: str = Field(
        default="agent", description="Source label for this memory entry."
    )
    runtime: ToolRuntime

    @field_validator("content", "source")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value required")
        return value
