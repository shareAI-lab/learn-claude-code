"""Explicit MCP connection state, mock discovery, and snapshot composition."""

from __future__ import annotations

import re
import threading
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Callable


class MCPClient:
    def __init__(self, name: str):
        self.name = name
        self.tools: list[dict] = []
        self._handlers: dict[str, Callable] = {}

    def register(self, tool_defs: list[dict], handlers: dict[str, Callable]) -> None:
        self.tools = tool_defs
        self._handlers = handlers

    def call_tool(self, tool_name: str, args: dict) -> str:
        handler = self._handlers.get(tool_name)
        if not handler:
            return f"MCP error: unknown tool '{tool_name}'"
        try:
            return handler(**args)
        except Exception as exc:
            return f"MCP error: {exc}"


@dataclass(slots=True)
class MCPState:
    clients: dict[str, MCPClient] = field(default_factory=dict)
    metadata: dict[str, dict] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)


MCP_CONNECTION_TOOL_SCHEMA = {
    "name": "connect_mcp",
    "description": "Connect to an MCP server (docs, deploy) and discover tools.",
    "input_schema": {"type": "object",
                     "properties": {"name": {"type": "string"}},
                     "required": ["name"]},
}


def register_mcp_connection_tool(registry, mcp_state) -> None:
    """Register the explicit MCP connection entry point, not discovered tools."""
    registry.register(
        MCP_CONNECTION_TOOL_SCHEMA,
        lambda name: connect_mcp(mcp_state, name, registry.snapshot),
    )


_DISALLOWED_CHARS = re.compile(r"[^a-zA-Z0-9_-]")


def normalize_mcp_name(name: str) -> str:
    return _DISALLOWED_CHARS.sub("_", name)


def _mock_server_docs() -> MCPClient:
    client = MCPClient("docs")
    client.register([
        {"name": "search", "description": "Search documentation. (readOnly)",
         "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
         "annotations": {"readOnly": True, "destructive": False}},
        {"name": "get_version", "description": "Get API version. (readOnly)",
         "inputSchema": {"type": "object", "properties": {}, "required": []}},
    ], {"search": lambda query: f"[docs] Found 3 results for '{query}'", "get_version": lambda: "[docs] API v2.1.0"})
    return client


def _mock_server_deploy() -> MCPClient:
    client = MCPClient("deploy")
    client.register([
        {"name": "trigger", "description": "Trigger a deployment. (destructive — requires approval in real CC)",
         "inputSchema": {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]},
         "annotations": {"readOnly": False, "destructive": True}},
        {"name": "status", "description": "Check deployment status. (readOnly)",
         "inputSchema": {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]},
         "annotations": {"readOnly": True, "destructive": False}},
    ], {"trigger": lambda service: f"[deploy] Triggered: {service}", "status": lambda service: f"[deploy] {service}: running (v1.4.2)"})
    return client


MOCK_SERVERS = {"docs": _mock_server_docs, "deploy": _mock_server_deploy}


def connect_mcp(state: MCPState, name: str, builtin_snapshot=None) -> str:
    factory = MOCK_SERVERS.get(name)
    if not factory:
        return f"Unknown server '{name}'. Available: {', '.join(MOCK_SERVERS)}"
    with state.lock:
        if name in state.clients:
            return f"MCP server '{name}' already connected"
        client = factory()
        state.clients[name] = client
        if builtin_snapshot:
            try:
                snapshot_mcp_tools(state, *builtin_snapshot())
            except ValueError as exc:
                state.clients.pop(name, None)
                return f"Error connecting to MCP server '{name}': {exc}"
    tools = [tool["name"] for tool in client.tools]
    print(f"  \033[31m[mcp] connected: {name} → {tools}\033[0m")
    return f"Connected to MCP server '{name}'. Discovered {len(tools)} tools: {', '.join(tools)}"


def snapshot_mcp_tools(
    state: MCPState, builtin_tools: list[dict], builtin_handlers: dict[str, Callable]
) -> tuple[list[dict], dict[str, Callable]]:
    tools = deepcopy(builtin_tools)
    handlers = dict(builtin_handlers)
    metadata: dict[str, dict] = {}
    with state.lock:
        clients = list(sorted(state.clients.items()))
    for server_name, client in clients:
        for tool_def in sorted(client.tools, key=lambda item: item["name"]):
            original_name = tool_def["name"]
            prefixed = f"mcp__{normalize_mcp_name(server_name)}__{normalize_mcp_name(original_name)}"
            if prefixed in handlers or any(tool["name"] == prefixed for tool in tools):
                raise ValueError(f"Duplicate MCP tool name: {prefixed}")
            schema = deepcopy(tool_def.get("inputSchema", {"type": "object", "properties": {}}))
            tools.append({"name": prefixed, "description": tool_def.get("description", ""), "input_schema": schema})
            handlers[prefixed] = lambda _client=client, _name=original_name, **kwargs: _client.call_tool(_name, kwargs)
            annotations = tool_def.get("annotations", {})
            metadata[prefixed] = {
                "server": server_name,
                "original_name": original_name,
                "readOnly": bool(annotations.get("readOnly", False)),
                "destructive": bool(
                    annotations.get(
                        "destructive", annotations.get("destructiveHint", False)
                    )
                ),
            }
    with state.lock:
        state.metadata.clear()
        state.metadata.update(metadata)
    return tools, handlers
