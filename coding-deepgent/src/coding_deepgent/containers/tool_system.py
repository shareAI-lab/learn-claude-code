from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from dependency_injector import containers, providers

from coding_deepgent.permissions import PermissionManager
from coding_deepgent.tool_system import (
    CapabilityRegistry,
    ToolCapability,
    ToolGuardMiddleware,
    ToolPolicy,
)

READ_ONLY_TOOL_NAMES = frozenset({"read_file", "glob", "grep"})
DESTRUCTIVE_TOOL_NAMES = frozenset({"bash", "write_file", "edit_file"})


def _combine_tools(*groups: Sequence[object]) -> list[object]:
    combined: list[object] = []
    for group in groups:
        combined.extend(group)
    return combined


def _tool_name(tool: object) -> str:
    return str(getattr(tool, "name", getattr(tool, "__name__", type(tool).__name__)))


def _tool_domain(name: str) -> str:
    if name == "TodoWrite":
        return "todo"
    if name in READ_ONLY_TOOL_NAMES | DESTRUCTIVE_TOOL_NAMES:
        return "filesystem"
    return "unknown"


def _tool_capability(tool: object) -> ToolCapability:
    name = _tool_name(tool)
    return ToolCapability(
        name=name,
        tool=tool,  # type: ignore[arg-type]
        domain=_tool_domain(name),
        read_only=name in READ_ONLY_TOOL_NAMES,
        destructive=name in DESTRUCTIVE_TOOL_NAMES,
        concurrency_safe=name in READ_ONLY_TOOL_NAMES,
    )


def _capability_registry(tools: Sequence[object]) -> CapabilityRegistry:
    return CapabilityRegistry(_tool_capability(tool) for tool in tools)


def _singleton_list(item: object) -> list[object]:
    return [item]


class ToolSystemContainer(containers.DeclarativeContainer):
    filesystem_tools: Any = providers.Dependency(default=providers.Object([]))
    todo_tools: Any = providers.Dependency(default=providers.Object([]))
    permission_mode: Any = providers.Dependency(default=providers.Object("default"))
    event_sink: Any = providers.Dependency(default=providers.Object(None))

    tools: Any = providers.Callable(_combine_tools, filesystem_tools, todo_tools)
    capability_registry: Any = providers.Callable(_capability_registry, tools)
    permission_manager: Any = providers.Factory(
        PermissionManager,
        mode=permission_mode,
    )
    policy: Any = providers.Factory(
        ToolPolicy,
        registry=capability_registry,
        permission_manager=permission_manager,
    )
    middleware: Any = providers.Factory(
        ToolGuardMiddleware,
        registry=capability_registry,
        policy=policy,
        event_sink=event_sink,
    )
    middleware_list: Any = providers.Callable(_singleton_list, middleware)
