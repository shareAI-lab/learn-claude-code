from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _StrictSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"additionalProperties": False},
    )


class BashInput(_StrictSchema):
    command: str = Field(
        ..., min_length=1, description="Shell command to run inside the workspace."
    )

    @field_validator("command")
    @classmethod
    def _command_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("command is required")
        return value


class ReadFileInput(_StrictSchema):
    path: str = Field(..., min_length=1, description="Workspace-relative path to read.")
    limit: int | None = Field(
        default=None,
        ge=1,
        le=10_000,
        description="Optional maximum number of lines to return.",
    )

    @field_validator("path")
    @classmethod
    def _path_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("path is required")
        return value


class WriteFileInput(_StrictSchema):
    path: str = Field(
        ..., min_length=1, description="Workspace-relative path to write."
    )
    content: str = Field(..., description="Exact file content to write.")

    @field_validator("path")
    @classmethod
    def _path_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("path is required")
        return value


class EditFileInput(_StrictSchema):
    path: str = Field(..., min_length=1, description="Workspace-relative path to edit.")
    old_text: str = Field(..., description="Exact text fragment to replace once.")
    new_text: str = Field(
        ..., description="Replacement text for the first matching fragment."
    )

    @field_validator("path")
    @classmethod
    def _path_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("path is required")
        return value


class GlobInput(_StrictSchema):
    pattern: str = Field(
        ..., min_length=1, description="Workspace-relative glob pattern to match."
    )
    limit: int = Field(
        default=200, ge=1, le=2_000, description="Maximum number of matches to return."
    )

    @field_validator("pattern")
    @classmethod
    def _pattern_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("pattern is required")
        return value


class GrepInput(_StrictSchema):
    pattern: str = Field(
        ..., min_length=1, description="Regular expression to search for."
    )
    include: str = Field(
        default="**/*", min_length=1, description="Glob for files to scan."
    )
    limit: int = Field(
        default=200, ge=1, le=2_000, description="Maximum number of matches to return."
    )

    @field_validator("pattern", "include")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value is required")
        return value
