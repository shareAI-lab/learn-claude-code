from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langchain.tools import ToolRuntime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SkillMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)

    @field_validator("name", "description")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value required")
        return value


@dataclass(frozen=True, slots=True)
class LoadedSkill:
    metadata: SkillMetadata
    body: str
    path: Path

    def render(self, *, max_chars: int = 4000) -> str:
        body = (
            self.body
            if len(self.body) <= max_chars
            else self.body[:max_chars] + "\n...[skill truncated]"
        )
        return f"# Skill: {self.metadata.name}\n\n{self.metadata.description}\n\n{body}"


class LoadSkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    name: str = Field(..., min_length=1, description="Local skill name to load.")
    runtime: ToolRuntime

    @field_validator("name")
    @classmethod
    def _name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name required")
        return value
