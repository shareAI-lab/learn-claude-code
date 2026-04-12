from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from langchain_core.tools import BaseTool

from coding_deepgent.filesystem import (
    bash,
    edit_file,
    glob_search,
    grep_search,
    read_file,
    write_file,
)
from coding_deepgent.tools.planning import todo_write


@dataclass(frozen=True)
class ToolCapability:
    name: str
    tool: BaseTool
    domain: str
    read_only: bool
    destructive: bool
    concurrency_safe: bool
    enabled: bool = True
    tags: tuple[str, ...] = field(default_factory=tuple)


class CapabilityRegistry:
    def __init__(self, capabilities: Iterable[ToolCapability]):
        ordered = list(capabilities)
        self._capabilities = {capability.name: capability for capability in ordered}
        if len(self._capabilities) != len(ordered):
            raise ValueError("Tool capability names must be unique")

    def names(self) -> list[str]:
        return list(self._capabilities)

    def get(self, name: str) -> ToolCapability | None:
        return self._capabilities.get(name)

    def require(self, name: str) -> ToolCapability:
        capability = self.get(name)
        if capability is None:
            raise KeyError(f"Unknown tool capability: {name}")
        return capability

    def tools(self, *, enabled_only: bool = True) -> list[BaseTool]:
        capabilities = [
            capability
            for capability in self._capabilities.values()
            if not enabled_only or capability.enabled
        ]
        return [capability.tool for capability in capabilities]

    def metadata(self) -> dict[str, ToolCapability]:
        return dict(self._capabilities)


def build_default_registry(*, include_discovery: bool = False) -> CapabilityRegistry:
    capabilities = [
        ToolCapability(
            name="bash",
            tool=bash,
            domain="filesystem",
            read_only=False,
            destructive=True,
            concurrency_safe=False,
            tags=("shell", "workspace"),
        ),
        ToolCapability(
            name="read_file",
            tool=read_file,
            domain="filesystem",
            read_only=True,
            destructive=False,
            concurrency_safe=True,
            tags=("read", "workspace"),
        ),
        ToolCapability(
            name="write_file",
            tool=write_file,
            domain="filesystem",
            read_only=False,
            destructive=True,
            concurrency_safe=False,
            tags=("write", "workspace"),
        ),
        ToolCapability(
            name="edit_file",
            tool=edit_file,
            domain="filesystem",
            read_only=False,
            destructive=True,
            concurrency_safe=False,
            tags=("edit", "workspace"),
        ),
        ToolCapability(
            name="TodoWrite",
            tool=todo_write,
            domain="todo",
            read_only=False,
            destructive=False,
            concurrency_safe=False,
            tags=("state", "planning"),
        ),
    ]

    if include_discovery:
        capabilities.extend(
            [
                ToolCapability(
                    name="glob",
                    tool=glob_search,
                    domain="filesystem",
                    read_only=True,
                    destructive=False,
                    concurrency_safe=True,
                    tags=("discovery", "workspace"),
                ),
                ToolCapability(
                    name="grep",
                    tool=grep_search,
                    domain="filesystem",
                    read_only=True,
                    destructive=False,
                    concurrency_safe=True,
                    tags=("discovery", "workspace"),
                ),
            ]
        )

    return CapabilityRegistry(capabilities)
