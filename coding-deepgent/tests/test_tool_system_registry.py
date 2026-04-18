from __future__ import annotations

from pathlib import Path

import pytest
from dependency_injector import providers
from langchain.tools import tool

from coding_deepgent.containers import AppContainer
from coding_deepgent.settings import Settings
from coding_deepgent.tool_system import (
    TOOL_PROJECTION_EXPOSURES,
    ToolCapability,
    build_builtin_capabilities,
    build_capability_registry,
)


EXPECTED_MAIN_TOOL_NAMES = [
    "bash",
    "read_file",
    "write_file",
    "edit_file",
    "TodoWrite",
    "save_memory",
    "list_memory",
    "delete_memory",
    "load_skill",
    "ToolSearch",
    "invoke_deferred_tool",
    "task_create",
    "task_get",
    "task_list",
    "task_update",
    "plan_save",
    "plan_get",
    "run_subagent",
    "run_fork",
]

EXPECTED_DEFERRED_TOOL_NAMES = [
    "run_subagent_background",
    "subagent_status",
    "subagent_send_input",
    "subagent_stop",
    "resume_subagent",
    "resume_fork",
]


def _container(tmp_path: Path) -> AppContainer:
    return AppContainer(
        settings=providers.Object(Settings(workdir=tmp_path)),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(lambda **kwargs: object()),
    )


def test_capability_inventory_exposes_child_only_and_main_projections(
    tmp_path: Path,
) -> None:
    registry = _container(tmp_path).capability_registry()

    assert "glob" in registry.names()
    assert "grep" in registry.names()
    assert registry.child_names() == ["glob", "grep"]
    assert "glob" not in registry.main_names()
    assert "grep" not in registry.main_names()
    assert "glob" not in registry.declarable_names()
    assert "grep" not in registry.declarable_names()
    assert "save_memory" in registry.main_names()
    assert "task_create" in registry.main_names()


def test_main_projection_preserves_current_product_tool_surface(
    tmp_path: Path,
) -> None:
    registry = _container(tmp_path).capability_registry()

    tool_names = [
        getattr(tool, "name", type(tool).__name__) for tool in registry.main_tools()
    ]

    assert tool_names == EXPECTED_MAIN_TOOL_NAMES


def test_role_based_projection_api_is_deterministic(tmp_path: Path) -> None:
    registry = _container(tmp_path).capability_registry()
    main_projection = registry.project("main")
    child_projection = registry.project("child")

    assert TOOL_PROJECTION_EXPOSURES == {
        "main": ("main", "extension"),
        "child": ("child_only",),
        "extension": ("extension",),
        "deferred": ("deferred",),
    }
    assert main_projection.name == "main"
    assert child_projection.name == "child"
    assert main_projection.names() == EXPECTED_MAIN_TOOL_NAMES
    assert child_projection.names() == ["glob", "grep"]
    assert [tool.name for tool in child_projection.tools()] == ["glob", "grep"]
    assert set(child_projection.metadata()) == {"glob", "grep"}
    assert registry.names_for_projection("main") == EXPECTED_MAIN_TOOL_NAMES
    assert registry.names_for_projection("child") == ["glob", "grep"]
    assert registry.names_for_projection("extension") == []
    assert registry.names_for_projection("deferred") == EXPECTED_DEFERRED_TOOL_NAMES
    assert [tool.name for tool in registry.tools_for_projection("child")] == [
        "glob",
        "grep",
    ]
    with pytest.raises(ValueError, match="Unknown tool projection"):
        registry.names_for_projection("missing")


@tool("duplicate_tool", description="First duplicate tool.")
def duplicate_tool_first() -> str:
    return "first"


@tool("duplicate_tool", description="Second duplicate tool.")
def duplicate_tool_second() -> str:
    return "second"


@tool("mcp__docs__lookup", description="Lookup docs by query.")
def extension_lookup(query: str) -> str:
    return query


@tool("disabled_demo", description="Disabled demo capability.")
def disabled_demo() -> str:
    return "disabled"


@tool("audit_tool", description="Audit test tool.")
def audit_tool(query: str) -> str:
    return query


def test_build_builtin_capabilities_rejects_duplicate_tool_names() -> None:
    with pytest.raises(ValueError, match="Duplicate builtin tool name: duplicate_tool"):
        build_builtin_capabilities(
            filesystem_tools=(duplicate_tool_first, duplicate_tool_second),
            todo_tools=(),
            memory_tools=(),
            skill_tools=(),
            deferred_bridge_tools=(),
            task_tools=(),
            subagent_tools=(),
        )


def test_registered_capabilities_have_five_factor_metadata_and_schema(
    tmp_path: Path,
) -> None:
    registry = _container(tmp_path).capability_registry()

    for capability in registry.metadata().values():
        assert capability.name == getattr(capability.tool, "name")
        assert capability.tool.args_schema is not None
        assert capability.tool.tool_call_schema is not None
        assert capability.domain
        assert capability.source
        assert capability.family
        assert capability.mutation
        assert capability.execution
        assert capability.exposure in {"main", "extension", "child_only", "deferred"}
        assert capability.rendering_result
        public_schema = capability.tool.tool_call_schema.model_json_schema()
        public_fields = set(public_schema.get("properties", {}))
        assert "runtime" not in public_fields
        assert "tool_call_id" not in public_fields


def test_builtin_capability_safe_opt_ins_are_explicit(tmp_path: Path) -> None:
    registry = _container(tmp_path).capability_registry()
    persisted_tools = {
        capability.name
        for capability in registry.metadata().values()
        if capability.persist_large_output
    }
    microcompact_tools = {
        capability.name
        for capability in registry.metadata().values()
        if capability.microcompact_eligible
    }

    assert persisted_tools == {"bash", "read_file", "glob", "grep"}
    assert microcompact_tools == persisted_tools
    for capability in registry.metadata().values():
        if capability.persist_large_output:
            assert capability.max_inline_result_chars == 4000
            assert capability.rendering_result == "tool_message_or_persisted_output"
        if capability.mutation in {
            "workspace_write",
            "state_update",
            "durable_store",
            "orchestration",
        }:
            assert capability.read_only is False
            assert capability.concurrency_safe is False


def test_capability_registry_rejects_name_mismatch_and_unknown_metadata() -> None:
    with pytest.raises(ValueError, match="must match tool name"):
        build_capability_registry(
            builtin_capabilities=(
                ToolCapability(
                    name="wrong_name",
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
                    exposure="main",
                    rendering_result="tool_message",
                ),
            ),
            extension_capabilities=(),
        )

    with pytest.raises(ValueError, match="invalid rendering_result"):
        build_capability_registry(
            builtin_capabilities=(
                ToolCapability(
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
                    exposure="main",
                    rendering_result="unknown",
                ),
            ),
            extension_capabilities=(),
        )


def test_capability_registry_enabled_and_extension_projections_are_explicit() -> None:
    base_registry = _container(Path.cwd()).capability_registry()
    extension_capability = ToolCapability(
        name="mcp__docs__lookup",
        tool=extension_lookup,
        domain="mcp",
        read_only=True,
        destructive=False,
        concurrency_safe=True,
        source="mcp:docs",
        trusted=False,
        family="mcp",
        mutation="read",
        execution="plain_tool",
        exposure="extension",
        rendering_result="tool_message",
        tags=("read", "server:docs"),
    )
    disabled_capability = ToolCapability(
        name="disabled_demo",
        tool=disabled_demo,
        domain="demo",
        read_only=True,
        destructive=False,
        concurrency_safe=True,
        source="builtin",
        trusted=True,
        family="demo",
        mutation="read",
        execution="plain_tool",
        enabled=False,
        exposure="main",
        rendering_result="tool_message",
    )
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
        extension_capabilities=(
            extension_capability,
            disabled_capability,
            deferred_capability,
        ),
    )

    assert "mcp__docs__lookup" in registry.main_names()
    assert "mcp__docs__lookup" in registry.declarable_names()
    assert "disabled_demo" not in registry.main_names()
    assert "disabled_demo" not in registry.declarable_names()
    assert registry.names_for_projection("extension") == ["mcp__docs__lookup"]
    assert registry.names_for_projection("deferred") == [
        *EXPECTED_DEFERRED_TOOL_NAMES,
        "audit_tool",
    ]
    assert "audit_tool" not in registry.main_names()


def test_app_container_threads_permission_settings_into_tool_system(tmp_path: Path) -> None:
    trusted_root = (tmp_path / "shared").resolve()
    trusted_root.mkdir(parents=True)
    settings = Settings(
        workdir=tmp_path,
        permission_mode="plan",
        trusted_workdirs=(trusted_root,),
    )
    container = AppContainer(
        settings=providers.Object(settings),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(lambda **kwargs: object()),
    )

    permission_manager = container.tool_system.permission_manager()

    assert permission_manager.mode == "plan"
    assert permission_manager.workdir == tmp_path.resolve()
    assert permission_manager.trusted_workdirs == (trusted_root,)
