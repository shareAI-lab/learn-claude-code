from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_:-]*$")


class PluginManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    skills: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()

    @field_validator("name", "description", "version")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value required")
        return value

    @field_validator("name")
    @classmethod
    def _name_must_be_identifier(cls, value: str) -> str:
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError("name must be a local identifier")
        return value

    @field_validator("skills", "tools", "resources")
    @classmethod
    def _entries_must_be_identifiers(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        cleaned: list[str] = []
        for value in values:
            item = value.strip()
            if not item:
                raise ValueError("empty identifier")
            if not _IDENTIFIER.fullmatch(item):
                raise ValueError("values must be local identifiers")
            cleaned.append(item)
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("duplicate identifiers are not allowed")
        return tuple(cleaned)


@dataclass(frozen=True, slots=True)
class LoadedPluginManifest:
    manifest: PluginManifest
    root: Path
    path: Path
