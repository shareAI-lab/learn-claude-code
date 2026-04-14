from __future__ import annotations

from importlib.util import find_spec
from typing import Iterable

from coding_deepgent.mcp.schemas import MCPResourceDescriptor, MCPToolDescriptor
from coding_deepgent.tool_system import ToolCapability


def langchain_mcp_adapters_available() -> bool:
    """Return whether the official LangChain MCP adapter package is installed."""

    return find_spec("langchain_mcp_adapters") is not None


def adapt_mcp_tool_descriptor(descriptor: MCPToolDescriptor) -> ToolCapability:
    """Convert one already-discovered MCP tool into a local capability entry."""

    return ToolCapability(
        name=descriptor.name,
        tool=descriptor.tool,
        domain="mcp",
        read_only=descriptor.hints.read_only,
        destructive=descriptor.hints.destructive,
        concurrency_safe=descriptor.hints.read_only
        and not descriptor.hints.destructive,
        source=f"mcp:{descriptor.source.server_name}",
        trusted=False,
        family="mcp",
        mutation=(
            "read"
            if descriptor.hints.read_only and not descriptor.hints.destructive
            else "workspace_write"
            if descriptor.hints.destructive
            else "unknown"
        ),
        execution="plain_tool",
        exposure="extension",
        tags=(
            "mcp",
            f"server:{descriptor.source.server_name}",
            f"transport:{descriptor.source.transport}",
            *descriptor.tags,
        ),
    )


def adapt_mcp_tool_descriptors(
    descriptors: Iterable[MCPToolDescriptor],
) -> tuple[ToolCapability, ...]:
    """Convert descriptors in input order; duplicate names fail in the registry."""

    return tuple(adapt_mcp_tool_descriptor(descriptor) for descriptor in descriptors)


class MCPResourceRegistry:
    """Separate read-surface registry for MCP resources.

    Stage 7 keeps resources out of executable capability binding.
    """

    def __init__(self, resources: Iterable[MCPResourceDescriptor] = ()) -> None:
        ordered = tuple(resources)
        self._resources = ordered
        self._by_uri = {resource.uri: resource for resource in ordered}
        if len(self._by_uri) != len(ordered):
            raise ValueError("MCP resource URIs must be unique")

    def uris(self) -> list[str]:
        return list(self._by_uri)

    def get(self, uri: str) -> MCPResourceDescriptor | None:
        return self._by_uri.get(uri)

    def by_server(self, server_name: str) -> list[MCPResourceDescriptor]:
        return [
            resource
            for resource in self._resources
            if resource.source.server_name == server_name
        ]

    def all(self) -> tuple[MCPResourceDescriptor, ...]:
        return self._resources
