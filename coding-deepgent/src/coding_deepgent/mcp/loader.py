from __future__ import annotations

import asyncio
import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from coding_deepgent.mcp.adapters import (
    MCPResourceRegistry,
    adapt_mcp_tool_descriptors,
    langchain_mcp_adapters_available,
)
from coding_deepgent.mcp.schemas import MCPSourceMetadata, MCPToolDescriptor
from coding_deepgent.tool_system import ToolCapability

MCP_CONFIG_FILE_NAME = ".mcp.json"


class MCPServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transport: str = Field(default="stdio", min_length=1)
    command: str | None = None
    args: tuple[str, ...] = ()
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_transport(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if "transport" in data and "type" in data and data["transport"] != data["type"]:
            raise ValueError("transport and type must match when both are provided")
        if "transport" not in data and "type" in data:
            data["transport"] = data.pop("type")
        data.setdefault("transport", "stdio")
        return data

    @model_validator(mode="after")
    def _validate_shape(self) -> "MCPServerConfig":
        if self.transport == "stdio":
            if self.command is None or not self.command.strip():
                raise ValueError("stdio MCP server requires command")
            if self.url is not None:
                raise ValueError("stdio MCP server must not define url")
            return self
        if self.transport in {"http", "sse"}:
            if self.url is None or not self.url.strip():
                raise ValueError(f"{self.transport} MCP server requires url")
            if self.command is not None:
                raise ValueError(f"{self.transport} MCP server must not define command")
            return self
        raise ValueError(f"Unsupported MCP transport: {self.transport}")


class MCPConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mcpServers: dict[str, MCPServerConfig] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LoadedMCPConfig:
    path: Path
    config: MCPConfig


@dataclass(frozen=True, slots=True)
class MCPRuntimeLoadResult:
    loaded_config: LoadedMCPConfig | None
    capabilities: tuple[ToolCapability, ...]
    resources: MCPResourceRegistry
    adapter_available: bool
    reason: str | None = None


def mcp_config_path(workdir: Path) -> Path:
    return workdir.resolve() / MCP_CONFIG_FILE_NAME


def load_local_mcp_config(*, workdir: Path) -> LoadedMCPConfig | None:
    path = mcp_config_path(workdir)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return LoadedMCPConfig(path=path, config=MCPConfig.model_validate(data))


def _server_client_config(server: MCPServerConfig) -> dict[str, object]:
    payload: dict[str, object] = {"transport": server.transport}
    if server.command is not None:
        payload["command"] = server.command
    if server.args:
        payload["args"] = list(server.args)
    if server.env:
        payload["env"] = dict(server.env)
    if server.url is not None:
        payload["url"] = server.url
    if server.headers:
        payload["headers"] = dict(server.headers)
    return payload


def _default_client_factory() -> Callable[[dict[str, Any]], Any] | None:
    if not langchain_mcp_adapters_available():
        return None
    client_module = importlib.import_module("langchain_mcp_adapters.client")
    client_cls = getattr(client_module, "MultiServerMCPClient")
    return lambda config: client_cls(config)


async def _load_server_tools(
    server_name: str,
    server: MCPServerConfig,
    *,
    client_factory: Callable[[dict[str, Any]], Any],
) -> tuple[MCPToolDescriptor, ...]:
    client = client_factory({server_name: _server_client_config(server)})
    tools = await client.get_tools()
    return tuple(
        MCPToolDescriptor(
            name=str(getattr(tool, "name", type(tool).__name__)),
            tool=tool,
            source=MCPSourceMetadata(
                server_name=server_name, transport=server.transport
            ),
            description=str(getattr(tool, "description", "") or ""),
        )
        for tool in tools
    )


def load_mcp_runtime_extensions(
    *,
    workdir: Path,
    client_factory: Callable[[dict[str, Any]], Any] | None = None,
) -> MCPRuntimeLoadResult:
    loaded_config = load_local_mcp_config(workdir=workdir)
    if loaded_config is None:
        return MCPRuntimeLoadResult(
            loaded_config=None,
            capabilities=(),
            resources=MCPResourceRegistry(),
            adapter_available=langchain_mcp_adapters_available(),
            reason="no_mcp_config",
        )

    factory = client_factory or _default_client_factory()
    if factory is None:
        return MCPRuntimeLoadResult(
            loaded_config=loaded_config,
            capabilities=(),
            resources=MCPResourceRegistry(),
            adapter_available=False,
            reason="langchain_mcp_adapters_unavailable",
        )

    descriptors: list[MCPToolDescriptor] = []
    for server_name, server in loaded_config.config.mcpServers.items():
        descriptors.extend(
            asyncio.run(_load_server_tools(server_name, server, client_factory=factory))
        )
    return MCPRuntimeLoadResult(
        loaded_config=loaded_config,
        capabilities=adapt_mcp_tool_descriptors(descriptors),
        resources=MCPResourceRegistry(),
        adapter_available=True,
    )
