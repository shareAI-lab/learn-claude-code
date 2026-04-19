from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from dependency_injector import providers
from langgraph.types import Command
from langchain.tools import tool
from pydantic import ValidationError

from coding_deepgent.containers import AppContainer
from coding_deepgent.hooks import LocalHookRegistry
from coding_deepgent.mcp import MCPSourceMetadata, MCPToolDescriptor, adapt_mcp_tool_descriptor
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext
from coding_deepgent.settings import Settings
from coding_deepgent.tool_system import ToolCapability, ToolPolicy, build_capability_registry
from coding_deepgent.tool_system.deferred import (
    InvokeDeferredToolInput,
    ToolSearchInput,
    ToolSearchResult,
    invoke_deferred_tool,
    tool_search,
)


@tool("audit_tool", description="Audit one candidate by query.")
def audit_tool(query: str) -> str:
    return f"audit:{query}"


@tool("update_tool", description="Update one candidate by query.")
def update_tool(query: str) -> Command:
    return Command(update={"audit_query": query})


@tool("mcp__docs__lookup", description="Lookup docs by query.")
def docs_lookup(query: str) -> str:
    return f"docs:{query}"


def runtime_for(registry, *, workdir: Path):
    return SimpleNamespace(
        tool_call_id="call-1",
        state={},
        store=None,
        context=RuntimeContext(
            session_id="session-1",
            workdir=workdir,
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="test-agent",
            skill_dir=workdir / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=LocalHookRegistry(),
            tool_policy=ToolPolicy(registry=registry),
            visible_tool_projection=registry.project("main"),
        ),
    )


def product_registry(workdir: Path):
    container = AppContainer(
        settings=providers.Object(Settings(workdir=workdir)),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(lambda **kwargs: object()),
    )
    return container.capability_registry()


def test_tool_search_schema_is_strict_and_hides_runtime() -> None:
    schema = cast(Any, tool_search.tool_call_schema).model_json_schema()

    assert tool_search.name == "ToolSearch"
    assert "runtime" not in schema["properties"]

    with pytest.raises(ValidationError):
        ToolSearchInput.model_validate({"query": " "})
    with pytest.raises(ValidationError):
        ToolSearchInput.model_validate({"query": "search", "extra": True})
    with pytest.raises(ValidationError):
        InvokeDeferredToolInput.model_validate(
            {"tool_name": "audit_tool", "arguments": {}, "extra": True}
        )


def test_tool_search_returns_deferred_builtin_subagent_controls(tmp_path: Path) -> None:
    registry = product_registry(tmp_path)
    runtime = runtime_for(registry, workdir=tmp_path)

    result = ToolSearchResult.model_validate_json(
        cast(Any, tool_search).func("background subagent", runtime)
    )

    names = [item.name for item in result.matches]
    assert result.total_deferred_tools >= 6
    assert "run_subagent_background" in names
    assert "subagent_list" in names
    assert "subagent_status" in names


def test_tool_search_selects_exact_deferred_mcp_tool(tmp_path: Path) -> None:
    base_registry = product_registry(tmp_path)
    capability = adapt_mcp_tool_descriptor(
        MCPToolDescriptor(
            name="mcp__docs__lookup",
            tool=docs_lookup,
            source=MCPSourceMetadata(server_name="docs", transport="stdio"),
        )
    )
    registry = build_capability_registry(
        builtin_capabilities=tuple(base_registry.metadata().values()),
        extension_capabilities=(capability,),
    )
    runtime = runtime_for(registry, workdir=tmp_path)

    result = ToolSearchResult.model_validate_json(
        cast(Any, tool_search).func("select:mcp__docs__lookup", runtime)
    )

    assert [item.name for item in result.matches] == ["mcp__docs__lookup"]
    assert result.matches[0].source == "mcp:docs"


def test_invoke_deferred_tool_executes_custom_deferred_capability(tmp_path: Path) -> None:
    base_registry = product_registry(tmp_path)
    deferred_capability = ToolCapability(
        name="audit_tool",
        tool=audit_tool,
        domain="demo",
        read_only=True,
        destructive=False,
        concurrency_safe=True,
        source="builtin",
        trusted=True,
        family="demo",
        mutation="read",
        execution="plain_tool",
        exposure="deferred",
        rendering_result="tool_message",
    )
    registry = build_capability_registry(
        builtin_capabilities=tuple(base_registry.metadata().values()),
        extension_capabilities=(deferred_capability,),
    )
    runtime = runtime_for(registry, workdir=tmp_path)

    output = cast(Any, invoke_deferred_tool).func(
        "audit_tool",
        {"query": "safety check"},
        runtime,
    )

    assert str(output.content) == "audit:safety check"


def test_invoke_deferred_tool_preserves_command_update_results(tmp_path: Path) -> None:
    base_registry = product_registry(tmp_path)
    deferred_capability = ToolCapability(
        name="update_tool",
        tool=update_tool,
        domain="demo",
        read_only=False,
        destructive=False,
        concurrency_safe=False,
        source="builtin",
        trusted=True,
        family="demo",
        mutation="orchestration",
        execution="plain_tool",
        exposure="deferred",
        rendering_result="command",
    )
    registry = build_capability_registry(
        builtin_capabilities=tuple(base_registry.metadata().values()),
        extension_capabilities=(deferred_capability,),
    )
    runtime = runtime_for(registry, workdir=tmp_path)

    output = cast(Any, invoke_deferred_tool).func(
        "update_tool",
        {"query": "state sync"},
        runtime,
    )

    assert isinstance(output, Command)
    assert output.update == {"audit_query": "state sync"}


def test_invoke_deferred_tool_executes_deferred_mcp_capability(tmp_path: Path) -> None:
    base_registry = product_registry(tmp_path)
    capability = adapt_mcp_tool_descriptor(
        MCPToolDescriptor(
            name="mcp__docs__lookup",
            tool=docs_lookup,
            source=MCPSourceMetadata(server_name="docs", transport="stdio"),
        )
    )
    registry = build_capability_registry(
        builtin_capabilities=tuple(base_registry.metadata().values()),
        extension_capabilities=(capability,),
    )
    runtime = runtime_for(registry, workdir=tmp_path)

    output = cast(Any, invoke_deferred_tool).func(
        "mcp__docs__lookup",
        {"query": "tool search"},
        runtime,
    )

    assert str(output.content) == "docs:tool search"
