from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence, cast

import pytest
from dependency_injector import providers
from langchain.tools import tool

from coding_deepgent.containers import AppContainer
from coding_deepgent.mcp import (
    MCPConfig,
    MCPResourceDescriptor,
    MCPResourceRegistry,
    MCPRuntimeLoadResult,
    MCPServerConfig,
    MCPSourceMetadata,
    MCPToolDescriptor,
    MCPToolHint,
    adapt_mcp_tool_descriptor,
    adapt_mcp_tool_descriptors,
    langchain_mcp_adapters_available,
    load_local_mcp_config,
    load_mcp_runtime_extensions,
    mcp_config_path,
)
from coding_deepgent.settings import Settings
from coding_deepgent.tool_system import CapabilityRegistry


@tool("mcp__docs__lookup", description="Lookup docs by query.")
def docs_lookup(query: str) -> str:
    """Lookup docs by query."""

    return query


def test_mcp_tool_descriptor_maps_to_capability_with_source_metadata() -> None:
    descriptor = MCPToolDescriptor(
        name="mcp__docs__lookup",
        tool=docs_lookup,
        source=MCPSourceMetadata(server_name="docs", transport="stdio"),
        hints=MCPToolHint(read_only=True),
    )

    capability = adapt_mcp_tool_descriptor(descriptor)

    assert capability.name == "mcp__docs__lookup"
    assert capability.tool is docs_lookup
    assert capability.domain == "mcp"
    assert capability.read_only is True
    assert capability.destructive is False
    assert capability.concurrency_safe is True
    assert capability.source == "mcp:docs"
    assert capability.trusted is False
    assert "server:docs" in capability.tags
    assert "transport:stdio" in capability.tags


def test_mcp_resources_stay_separate_from_executable_capabilities() -> None:
    source = MCPSourceMetadata(server_name="docs", transport="stdio")
    resource = MCPResourceDescriptor(
        uri="file:///docs/guide.md",
        name="guide",
        description="Guide",
        mime_type="text/markdown",
        source=source,
    )
    registry = MCPResourceRegistry([resource])
    capabilities = adapt_mcp_tool_descriptors(
        [
            MCPToolDescriptor(
                name="mcp__docs__lookup",
                tool=docs_lookup,
                source=source,
            )
        ]
    )

    assert registry.uris() == ["file:///docs/guide.md"]
    assert registry.by_server("docs") == [resource]
    assert [capability.name for capability in capabilities] == ["mcp__docs__lookup"]
    assert "file:///docs/guide.md" not in [
        capability.name for capability in capabilities
    ]

    with pytest.raises(ValueError):
        MCPResourceRegistry([resource, resource])


def test_mcp_extension_capabilities_are_agent_bindable_without_replacing_runtime(
    tmp_path,
) -> None:
    captured: dict[str, object] = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return object()

    capability = adapt_mcp_tool_descriptor(
        MCPToolDescriptor(
            name="mcp__docs__lookup",
            tool=docs_lookup,
            source=MCPSourceMetadata(server_name="docs", transport="stdio"),
            hints=MCPToolHint(read_only=True),
        )
    )
    settings = Settings(workdir=tmp_path)
    container = AppContainer(
        settings=providers.Object(settings),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(fake_create_agent),
        extension_capabilities=providers.Object([capability]),
    )

    assert container.agent() is not None
    assert captured["name"] == "coding-deepgent"
    tool_names = [
        getattr(tool_item, "name", type(tool_item).__name__)
        for tool_item in cast(Sequence[object], captured["tools"])
    ]
    assert tool_names[-1] == "mcp__docs__lookup"
    assert "mcp__docs__lookup" in container.capability_registry().names()
    assert isinstance(container.capability_registry(), CapabilityRegistry)


def test_langchain_mcp_adapter_probe_is_optional_and_side_effect_free() -> None:
    assert isinstance(langchain_mcp_adapters_available(), bool)


def test_mcp_config_schema_and_loader_are_strict(tmp_path: Path) -> None:
    path = mcp_config_path(tmp_path)
    path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "docs": {
                        "command": "python",
                        "args": ["server.py"],
                        "env": {"TOKEN": "x"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    loaded = load_local_mcp_config(workdir=tmp_path)

    assert loaded is not None
    assert loaded.path == path
    assert isinstance(loaded.config, MCPConfig)
    assert loaded.config.mcpServers["docs"].transport == "stdio"

    with pytest.raises(Exception):
        MCPServerConfig.model_validate({"transport": "stdio", "extra": True})


def test_mcp_server_transport_alias_and_http_sse_contracts() -> None:
    http = MCPServerConfig.model_validate(
        {"type": "http", "url": "https://example.invalid/mcp"}
    )
    sse = MCPServerConfig.model_validate(
        {"transport": "sse", "url": "https://example.invalid/events"}
    )

    assert http.transport == "http"
    assert sse.transport == "sse"

    with pytest.raises(ValueError, match="transport and type must match"):
        MCPServerConfig.model_validate(
            {"transport": "stdio", "type": "http", "command": "server"}
        )
    with pytest.raises(ValueError, match="http MCP server requires url"):
        MCPServerConfig.model_validate({"transport": "http"})
    with pytest.raises(ValueError, match="http MCP server must not define command"):
        MCPServerConfig.model_validate(
            {
                "transport": "http",
                "url": "https://example.invalid/mcp",
                "command": "server",
            }
        )


def test_mcp_runtime_load_fails_soft_without_adapter(
    monkeypatch, tmp_path: Path
) -> None:
    mcp_config_path(tmp_path).write_text(
        json.dumps(
            {
                "mcpServers": {
                    "docs": {
                        "command": "python",
                        "args": ["server.py"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "coding_deepgent.mcp.loader.langchain_mcp_adapters_available",
        lambda: False,
    )
    result = load_mcp_runtime_extensions(workdir=tmp_path)

    assert isinstance(result, MCPRuntimeLoadResult)
    assert result.loaded_config is not None
    assert result.capabilities == ()
    assert result.reason == "langchain_mcp_adapters_unavailable"


def test_mcp_runtime_load_uses_client_factory_when_available(tmp_path: Path) -> None:
    mcp_config_path(tmp_path).write_text(
        json.dumps(
            {
                "mcpServers": {
                    "docs": {
                        "command": "python",
                        "args": ["server.py"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    class FakeClient:
        def __init__(self, config):
            self.config = config

        async def get_tools(self):
            return [docs_lookup]

    result = load_mcp_runtime_extensions(
        workdir=tmp_path,
        client_factory=lambda config: FakeClient(config),
    )

    assert result.adapter_available is True
    assert [capability.name for capability in result.capabilities] == [
        "mcp__docs__lookup"
    ]
    assert result.resources.uris() == []


def test_app_container_merges_loaded_mcp_capabilities(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return object()

    capability = adapt_mcp_tool_descriptor(
        MCPToolDescriptor(
            name="mcp__docs__lookup",
            tool=docs_lookup,
            source=MCPSourceMetadata(server_name="docs", transport="stdio"),
            hints=MCPToolHint(read_only=True),
        )
    )
    settings = Settings(workdir=tmp_path)
    container = AppContainer(
        settings=providers.Object(settings),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(fake_create_agent),
    )
    container.mcp_runtime_load_result.override(
        providers.Object(
            MCPRuntimeLoadResult(
                loaded_config=None,
                capabilities=(capability,),
                resources=MCPResourceRegistry(),
                adapter_available=True,
            )
        )
    )

    assert container.agent() is not None
    tool_names = [
        getattr(tool_item, "name", type(tool_item).__name__)
        for tool_item in cast(Sequence[object], captured["tools"])
    ]
    assert "mcp__docs__lookup" in tool_names
