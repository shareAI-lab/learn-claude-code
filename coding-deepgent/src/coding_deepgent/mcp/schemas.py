from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MCPSourceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server_name: str = Field(..., min_length=1)
    transport: str = Field(default="local", min_length=1)

    @field_validator("server_name", "transport")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value required")
        return value


class MCPToolHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    read_only: bool = False
    destructive: bool = False


class MCPResourceDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uri: str = Field(..., min_length=1)
    name: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    mime_type: str | None = Field(default=None, min_length=1)
    source: MCPSourceMetadata

    @field_validator("uri")
    @classmethod
    def _uri_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("uri required")
        return value


@dataclass(frozen=True, slots=True)
class MCPToolDescriptor:
    name: str
    tool: BaseTool
    source: MCPSourceMetadata
    description: str | None = None
    hints: MCPToolHint = field(default_factory=MCPToolHint)
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("tool name required")
        object.__setattr__(self, "name", name)
        if not self.description:
            object.__setattr__(
                self,
                "description",
                str(getattr(self.tool, "description", "") or ""),
            )
