from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from dependency_injector import containers, providers


def _combine_tools(*groups: Sequence[object]) -> list[object]:
    combined: list[object] = []
    for group in groups:
        combined.extend(group)
    return combined


def _capability_registry(tools: Sequence[object]) -> dict[str, object]:
    return {
        getattr(tool, "name", getattr(tool, "__name__", type(tool).__name__)): tool
        for tool in tools
    }


class ToolSystemContainer(containers.DeclarativeContainer):
    filesystem_tools: Any = providers.Dependency(default=providers.Object([]))
    todo_tools: Any = providers.Dependency(default=providers.Object([]))
    tools: Any = providers.Callable(_combine_tools, filesystem_tools, todo_tools)
    capability_registry: Any = providers.Callable(_capability_registry, tools)
