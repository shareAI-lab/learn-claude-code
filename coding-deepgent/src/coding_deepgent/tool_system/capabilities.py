from __future__ import annotations

from collections.abc import Sequence
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
from coding_deepgent.todo.tools import todo_write


@dataclass(frozen=True)
class ToolCapability:
    name: str
    tool: BaseTool
    domain: str
    read_only: bool
    destructive: bool
    concurrency_safe: bool
    enabled: bool = True
    source: str = "builtin"
    trusted: bool = True
    family: str = "unknown"
    mutation: str = "unknown"
    execution: str = "plain_tool"
    exposure: str = "main"
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

    def names_for_exposure(
        self,
        *exposures: str,
        enabled_only: bool = True,
    ) -> list[str]:
        return [
            capability.name
            for capability in self._capabilities.values()
            if (not enabled_only or capability.enabled)
            and capability.exposure in exposures
        ]

    def tools_for_exposure(
        self,
        *exposures: str,
        enabled_only: bool = True,
    ) -> list[BaseTool]:
        return [
            capability.tool
            for capability in self._capabilities.values()
            if (not enabled_only or capability.enabled)
            and capability.exposure in exposures
        ]

    def main_tools(self) -> list[BaseTool]:
        return self.tools_for_exposure("main", "extension")

    def main_names(self) -> list[str]:
        return self.names_for_exposure("main", "extension")

    def child_names(self) -> list[str]:
        return self.names_for_exposure("child_only")

    def declarable_names(self) -> list[str]:
        return self.names_for_exposure("main", "extension")

    def metadata(self) -> dict[str, ToolCapability]:
        return dict(self._capabilities)


def build_default_registry(*, include_discovery: bool = False) -> CapabilityRegistry:
    capabilities = list(
        build_builtin_capabilities(
            filesystem_tools=(
                bash,
                read_file,
                write_file,
                edit_file,
            ),
            discovery_tools=((glob_search, grep_search) if include_discovery else ()),
            todo_tools=(todo_write,),
            memory_tools=(),
            skill_tools=(),
            task_tools=(),
            subagent_tools=(),
        )
    )
    return build_capability_registry(
        builtin_capabilities=capabilities,
        extension_capabilities=(),
    )


def build_capability_registry(
    *,
    builtin_capabilities: Sequence[ToolCapability],
    extension_capabilities: Sequence[ToolCapability],
) -> CapabilityRegistry:
    return CapabilityRegistry([*builtin_capabilities, *extension_capabilities])


def build_builtin_capabilities(
    *,
    filesystem_tools: Sequence[BaseTool],
    discovery_tools: Sequence[BaseTool] = (),
    todo_tools: Sequence[BaseTool],
    memory_tools: Sequence[BaseTool],
    skill_tools: Sequence[BaseTool],
    task_tools: Sequence[BaseTool],
    subagent_tools: Sequence[BaseTool],
) -> tuple[ToolCapability, ...]:
    tool_by_name = {
        getattr(tool, "name", type(tool).__name__): tool
        for tool in [
            *filesystem_tools,
            *discovery_tools,
            *todo_tools,
            *memory_tools,
            *skill_tools,
            *task_tools,
            *subagent_tools,
        ]
    }
    capabilities: list[ToolCapability] = [
        ToolCapability(
            name="bash",
            tool=tool_by_name["bash"],
            domain="filesystem",
            read_only=False,
            destructive=True,
            concurrency_safe=False,
            family="filesystem",
            mutation="workspace_write",
            execution="plain_tool",
            tags=("shell", "workspace"),
        ),
        ToolCapability(
            name="read_file",
            tool=tool_by_name["read_file"],
            domain="filesystem",
            read_only=True,
            destructive=False,
            concurrency_safe=True,
            family="filesystem",
            mutation="read",
            execution="plain_tool",
            tags=("read", "workspace"),
        ),
        ToolCapability(
            name="write_file",
            tool=tool_by_name["write_file"],
            domain="filesystem",
            read_only=False,
            destructive=True,
            concurrency_safe=False,
            family="filesystem",
            mutation="workspace_write",
            execution="plain_tool",
            tags=("write", "workspace"),
        ),
        ToolCapability(
            name="edit_file",
            tool=tool_by_name["edit_file"],
            domain="filesystem",
            read_only=False,
            destructive=True,
            concurrency_safe=False,
            family="filesystem",
            mutation="workspace_write",
            execution="plain_tool",
            tags=("edit", "workspace"),
        ),
        ToolCapability(
            name="TodoWrite",
            tool=tool_by_name["TodoWrite"],
            domain="todo",
            read_only=False,
            destructive=False,
            concurrency_safe=False,
            family="todo",
            mutation="state_update",
            execution="command_update",
            tags=("state", "planning"),
        ),
    ]
    if "glob" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="glob",
                tool=tool_by_name["glob"],
                domain="filesystem",
                read_only=True,
                destructive=False,
                concurrency_safe=True,
                family="filesystem",
                mutation="read",
                execution="plain_tool",
                exposure="child_only",
                tags=("discovery", "workspace"),
            )
        )
    if "grep" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="grep",
                tool=tool_by_name["grep"],
                domain="filesystem",
                read_only=True,
                destructive=False,
                concurrency_safe=True,
                family="filesystem",
                mutation="read",
                execution="plain_tool",
                exposure="child_only",
                tags=("discovery", "workspace"),
            )
        )
    if "save_memory" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="save_memory",
                tool=tool_by_name["save_memory"],
                domain="memory",
                family="memory",
                mutation="durable_store",
                execution="plain_tool",
                read_only=False,
                destructive=False,
                concurrency_safe=False,
                source="builtin",
                trusted=True,
                exposure="main",
                tags=("memory",),
            )
        )
    if "load_skill" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="load_skill",
                tool=tool_by_name["load_skill"],
                domain="skills",
                family="skills",
                mutation="capability_load",
                execution="local_loader",
                read_only=True,
                destructive=False,
                concurrency_safe=True,
                source="builtin",
                trusted=True,
                exposure="main",
                tags=("skill",),
            )
        )
    if "task_create" in tool_by_name:
        capabilities.extend(
            [
                ToolCapability(
                    name="task_create",
                    tool=tool_by_name["task_create"],
                    domain="tasks",
                    family="tasks",
                    mutation="durable_store",
                    execution="plain_tool",
                    read_only=False,
                    destructive=False,
                    concurrency_safe=False,
                    source="builtin",
                    trusted=True,
                    exposure="main",
                    tags=("task",),
                ),
                ToolCapability(
                    name="task_get",
                    tool=tool_by_name["task_get"],
                    domain="tasks",
                    family="tasks",
                    mutation="read",
                    execution="plain_tool",
                    read_only=True,
                    destructive=False,
                    concurrency_safe=True,
                    source="builtin",
                    trusted=True,
                    exposure="main",
                    tags=("task", "read"),
                ),
                ToolCapability(
                    name="task_list",
                    tool=tool_by_name["task_list"],
                    domain="tasks",
                    family="tasks",
                    mutation="read",
                    execution="plain_tool",
                    read_only=True,
                    destructive=False,
                    concurrency_safe=True,
                    source="builtin",
                    trusted=True,
                    exposure="main",
                    tags=("task", "read"),
                ),
                ToolCapability(
                    name="task_update",
                    tool=tool_by_name["task_update"],
                    domain="tasks",
                    family="tasks",
                    mutation="durable_store",
                    execution="plain_tool",
                    read_only=False,
                    destructive=False,
                    concurrency_safe=False,
                    source="builtin",
                    trusted=True,
                    exposure="main",
                    tags=("task",),
                ),
            ]
        )
    if "plan_save" in tool_by_name:
        capabilities.extend(
            [
                ToolCapability(
                    name="plan_save",
                    tool=tool_by_name["plan_save"],
                    domain="tasks",
                    family="plan",
                    mutation="durable_store",
                    execution="plain_tool",
                    read_only=False,
                    destructive=False,
                    concurrency_safe=False,
                    source="builtin",
                    trusted=True,
                    exposure="main",
                    tags=("plan", "workflow"),
                ),
                ToolCapability(
                    name="plan_get",
                    tool=tool_by_name["plan_get"],
                    domain="tasks",
                    family="plan",
                    mutation="read",
                    execution="plain_tool",
                    read_only=True,
                    destructive=False,
                    concurrency_safe=True,
                    source="builtin",
                    trusted=True,
                    exposure="main",
                    tags=("plan", "read", "workflow"),
                ),
            ]
        )
    if "run_subagent" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="run_subagent",
                tool=tool_by_name["run_subagent"],
                domain="subagents",
                family="subagents",
                mutation="orchestration",
                execution="child_agent_bridge",
                read_only=False,
                destructive=False,
                concurrency_safe=False,
                source="builtin",
                trusted=True,
                exposure="main",
                tags=("subagent",),
            )
        )
    return tuple(capabilities)
