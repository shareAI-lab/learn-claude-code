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

KNOWN_TOOL_EXPOSURES = frozenset({"main", "child_only", "extension", "deferred"})
TOOL_PROJECTION_EXPOSURES = {
    "main": ("main", "extension"),
    "child": ("child_only",),
    "extension": ("extension",),
    "deferred": ("deferred",),
}


@dataclass(frozen=True)
class ToolCapability:
    name: str
    tool: BaseTool
    domain: str
    read_only: bool
    destructive: bool
    concurrency_safe: bool
    source: str
    trusted: bool
    family: str
    mutation: str
    execution: str
    exposure: str
    rendering_result: str
    enabled: bool = True
    tags: tuple[str, ...] = field(default_factory=tuple)
    persist_large_output: bool = False
    max_inline_result_chars: int | None = None
    microcompact_eligible: bool = False


@dataclass(frozen=True)
class ToolPoolProjection:
    name: str
    capabilities: tuple[ToolCapability, ...]

    def names(self) -> list[str]:
        return [capability.name for capability in self.capabilities]

    def tools(self) -> list[BaseTool]:
        return [capability.tool for capability in self.capabilities]

    def metadata(self) -> dict[str, ToolCapability]:
        return {capability.name: capability for capability in self.capabilities}


class CapabilityRegistry:
    def __init__(self, capabilities: Iterable[ToolCapability]):
        ordered = list(capabilities)
        self._capabilities = {capability.name: capability for capability in ordered}
        if len(self._capabilities) != len(ordered):
            raise ValueError("Tool capability names must be unique")
        for capability in ordered:
            _validate_capability(capability)

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

    def capabilities_for_exposure(
        self,
        *exposures: str,
        enabled_only: bool = True,
    ) -> tuple[ToolCapability, ...]:
        return tuple(
            capability
            for capability in self._capabilities.values()
            if (not enabled_only or capability.enabled)
            and capability.exposure in exposures
        )

    def names_for_exposure(
        self,
        *exposures: str,
        enabled_only: bool = True,
    ) -> list[str]:
        return [
            capability.name
            for capability in self.capabilities_for_exposure(
                *exposures,
                enabled_only=enabled_only,
            )
        ]

    def tools_for_exposure(
        self,
        *exposures: str,
        enabled_only: bool = True,
    ) -> list[BaseTool]:
        return [
            capability.tool
            for capability in self.capabilities_for_exposure(
                *exposures,
                enabled_only=enabled_only,
            )
        ]

    def capabilities_for_projection(
        self,
        projection: str,
        *,
        enabled_only: bool = True,
    ) -> tuple[ToolCapability, ...]:
        exposures = TOOL_PROJECTION_EXPOSURES.get(projection)
        if exposures is None:
            raise ValueError(f"Unknown tool projection: {projection}")
        return self.capabilities_for_exposure(*exposures, enabled_only=enabled_only)

    def project(
        self,
        projection: str,
        *,
        enabled_only: bool = True,
    ) -> ToolPoolProjection:
        return ToolPoolProjection(
            name=projection,
            capabilities=self.capabilities_for_projection(
                projection,
                enabled_only=enabled_only,
            ),
        )

    def names_for_projection(
        self,
        projection: str,
        *,
        enabled_only: bool = True,
    ) -> list[str]:
        return [
            capability.name
            for capability in self.capabilities_for_projection(
                projection,
                enabled_only=enabled_only,
            )
        ]

    def tools_for_projection(
        self,
        projection: str,
        *,
        enabled_only: bool = True,
    ) -> list[BaseTool]:
        return self.project(projection, enabled_only=enabled_only).tools()

    def tools_for_names(self, names: Sequence[str]) -> list[BaseTool]:
        return [self.require(name).tool for name in names]

    def main_tools(self) -> list[BaseTool]:
        return self.tools_for_projection("main")

    def main_names(self) -> list[str]:
        return self.names_for_projection("main")

    def child_names(self) -> list[str]:
        return self.names_for_projection("child")

    def declarable_names(self) -> list[str]:
        return self.names_for_exposure("main", "extension", "deferred")

    def metadata(self) -> dict[str, ToolCapability]:
        return dict(self._capabilities)


def _validate_capability(capability: ToolCapability) -> None:
    tool_name = str(getattr(capability.tool, "name", type(capability.tool).__name__))
    if capability.name != tool_name:
        raise ValueError(
            f"Tool capability name {capability.name!r} must match tool name {tool_name!r}"
        )
    for field_name in (
        "name",
        "domain",
        "source",
        "family",
        "mutation",
        "execution",
        "exposure",
        "rendering_result",
    ):
        value = getattr(capability, field_name)
        if not isinstance(value, str) or not value.strip() or value == "unknown":
            raise ValueError(
                f"Tool capability {capability.name!r} has invalid {field_name}"
            )
    if capability.exposure not in KNOWN_TOOL_EXPOSURES:
        raise ValueError(
            f"Tool capability {capability.name!r} has invalid exposure {capability.exposure!r}"
        )
    if getattr(capability.tool, "args_schema", None) is None:
        raise ValueError(f"Tool capability {capability.name!r} is missing args_schema")
    if getattr(capability.tool, "tool_call_schema", None) is None:
        raise ValueError(
            f"Tool capability {capability.name!r} is missing tool_call_schema"
        )
    if capability.persist_large_output and (
        capability.max_inline_result_chars is None
        or capability.max_inline_result_chars < 1
    ):
        raise ValueError(
            f"Tool capability {capability.name!r} must set max_inline_result_chars"
        )
    if capability.microcompact_eligible and not capability.persist_large_output:
        raise ValueError(
            f"Tool capability {capability.name!r} must persist output before microcompact"
        )


def build_default_registry(*, include_discovery: bool = False) -> CapabilityRegistry:
    from .deferred import invoke_deferred_tool, tool_search

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
            deferred_bridge_tools=(tool_search, invoke_deferred_tool),
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
    deferred_bridge_tools: Sequence[BaseTool],
    task_tools: Sequence[BaseTool],
    subagent_tools: Sequence[BaseTool],
) -> tuple[ToolCapability, ...]:
    ordered_tools = [
        *filesystem_tools,
        *discovery_tools,
        *todo_tools,
        *memory_tools,
        *skill_tools,
        *deferred_bridge_tools,
        *task_tools,
        *subagent_tools,
    ]
    tool_by_name: dict[str, BaseTool] = {}
    for tool in ordered_tools:
        name = getattr(tool, "name", type(tool).__name__)
        if name in tool_by_name:
            raise ValueError(f"Duplicate builtin tool name: {name}")
        tool_by_name[name] = tool
    capabilities: list[ToolCapability] = [
        ToolCapability(
            name="bash",
            tool=tool_by_name["bash"],
            domain="filesystem",
            read_only=False,
            destructive=True,
            concurrency_safe=False,
            source="builtin",
            trusted=True,
            family="filesystem",
            mutation="workspace_write",
            execution="plain_tool",
            exposure="main",
            rendering_result="tool_message_or_persisted_output",
            tags=("shell", "workspace"),
            persist_large_output=True,
            max_inline_result_chars=4000,
            microcompact_eligible=True,
        ),
        ToolCapability(
            name="read_file",
            tool=tool_by_name["read_file"],
            domain="filesystem",
            read_only=True,
            destructive=False,
            concurrency_safe=True,
            source="builtin",
            trusted=True,
            family="filesystem",
            mutation="read",
            execution="plain_tool",
            exposure="main",
            rendering_result="tool_message_or_persisted_output",
            tags=("read", "workspace"),
            persist_large_output=True,
            max_inline_result_chars=4000,
            microcompact_eligible=True,
        ),
        ToolCapability(
            name="write_file",
            tool=tool_by_name["write_file"],
            domain="filesystem",
            read_only=False,
            destructive=True,
            concurrency_safe=False,
            source="builtin",
            trusted=True,
            family="filesystem",
            mutation="workspace_write",
            execution="plain_tool",
            exposure="main",
            rendering_result="tool_message",
            tags=("write", "workspace"),
        ),
        ToolCapability(
            name="edit_file",
            tool=tool_by_name["edit_file"],
            domain="filesystem",
            read_only=False,
            destructive=True,
            concurrency_safe=False,
            source="builtin",
            trusted=True,
            family="filesystem",
            mutation="workspace_write",
            execution="plain_tool",
            exposure="main",
            rendering_result="tool_message",
            tags=("edit", "workspace"),
        ),
        ToolCapability(
            name="TodoWrite",
            tool=tool_by_name["TodoWrite"],
            domain="todo",
            read_only=False,
            destructive=False,
            concurrency_safe=False,
            source="builtin",
            trusted=True,
            family="todo",
            mutation="state_update",
            execution="command_update",
            exposure="main",
            rendering_result="command_update",
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
                source="builtin",
                trusted=True,
                family="filesystem",
                mutation="read",
                execution="plain_tool",
                exposure="child_only",
                rendering_result="tool_message_or_persisted_output",
                tags=("discovery", "workspace"),
                persist_large_output=True,
                max_inline_result_chars=4000,
                microcompact_eligible=True,
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
                source="builtin",
                trusted=True,
                family="filesystem",
                mutation="read",
                execution="plain_tool",
                exposure="child_only",
                rendering_result="tool_message_or_persisted_output",
                tags=("discovery", "workspace"),
                persist_large_output=True,
                max_inline_result_chars=4000,
                microcompact_eligible=True,
            )
        )
    for tool_name, read_only, destructive, mutation in (
        ("save_memory", False, False, "durable_store"),
        ("list_memory", True, False, "read"),
        ("delete_memory", False, False, "durable_store"),
    ):
        if tool_name in tool_by_name:
            capabilities.append(
                ToolCapability(
                    name=tool_name,
                    tool=tool_by_name[tool_name],
                    domain="memory",
                    family="memory",
                    mutation=mutation,
                    execution="plain_tool",
                    read_only=read_only,
                    destructive=destructive,
                    concurrency_safe=read_only,
                    source="builtin",
                    trusted=True,
                    exposure="main",
                    rendering_result="tool_message",
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
                rendering_result="tool_message",
                tags=("skill",),
            )
        )
    if "ToolSearch" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="ToolSearch",
                tool=tool_by_name["ToolSearch"],
                domain="tool_system",
                family="tool_system",
                mutation="read",
                execution="plain_tool",
                read_only=True,
                destructive=False,
                concurrency_safe=True,
                source="builtin",
                trusted=True,
                exposure="main",
                rendering_result="tool_message",
                tags=("tool_search", "deferred"),
            )
        )
    if "invoke_deferred_tool" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="invoke_deferred_tool",
                tool=tool_by_name["invoke_deferred_tool"],
                domain="tool_system",
                family="tool_system",
                mutation="orchestration",
                execution="plain_tool",
                read_only=False,
                destructive=False,
                concurrency_safe=False,
                source="builtin",
                trusted=True,
                exposure="main",
                rendering_result="tool_message",
                tags=("tool_search", "deferred"),
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
                    rendering_result="tool_message",
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
                    rendering_result="tool_message",
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
                    rendering_result="tool_message",
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
                    rendering_result="tool_message",
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
                    rendering_result="tool_message",
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
                    rendering_result="tool_message",
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
                rendering_result="tool_message",
                tags=("subagent",),
            )
        )
    if "run_subagent_background" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="run_subagent_background",
                tool=tool_by_name["run_subagent_background"],
                domain="subagents",
                family="subagents",
                mutation="orchestration",
                execution="child_agent_bridge",
                read_only=False,
                destructive=False,
                concurrency_safe=False,
                source="builtin",
                trusted=True,
                exposure="deferred",
                rendering_result="tool_message",
                tags=("subagent", "background"),
            )
        )
    if "subagent_status" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="subagent_status",
                tool=tool_by_name["subagent_status"],
                domain="subagents",
                family="subagents",
                mutation="read",
                execution="plain_tool",
                read_only=True,
                destructive=False,
                concurrency_safe=True,
                source="builtin",
                trusted=True,
                exposure="deferred",
                rendering_result="tool_message",
                tags=("subagent", "background", "read"),
            )
        )
    if "subagent_list" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="subagent_list",
                tool=tool_by_name["subagent_list"],
                domain="subagents",
                family="subagents",
                mutation="read",
                execution="plain_tool",
                read_only=True,
                destructive=False,
                concurrency_safe=True,
                source="builtin",
                trusted=True,
                exposure="deferred",
                rendering_result="tool_message",
                tags=("subagent", "background", "read", "list"),
            )
        )
    if "subagent_send_input" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="subagent_send_input",
                tool=tool_by_name["subagent_send_input"],
                domain="subagents",
                family="subagents",
                mutation="orchestration",
                execution="plain_tool",
                read_only=False,
                destructive=False,
                concurrency_safe=False,
                source="builtin",
                trusted=True,
                exposure="deferred",
                rendering_result="tool_message",
                tags=("subagent", "background"),
            )
        )
    if "subagent_stop" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="subagent_stop",
                tool=tool_by_name["subagent_stop"],
                domain="subagents",
                family="subagents",
                mutation="orchestration",
                execution="plain_tool",
                read_only=False,
                destructive=False,
                concurrency_safe=False,
                source="builtin",
                trusted=True,
                exposure="deferred",
                rendering_result="tool_message",
                tags=("subagent", "background"),
            )
        )
    if "resume_subagent" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="resume_subagent",
                tool=tool_by_name["resume_subagent"],
                domain="subagents",
                family="subagents",
                mutation="orchestration",
                execution="child_agent_bridge",
                read_only=False,
                destructive=False,
                concurrency_safe=False,
                source="builtin",
                trusted=True,
                exposure="deferred",
                rendering_result="tool_message",
                tags=("subagent", "resume"),
            )
        )
    if "resume_fork" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="resume_fork",
                tool=tool_by_name["resume_fork"],
                domain="subagents",
                family="subagents",
                mutation="orchestration",
                execution="fork_bridge",
                read_only=False,
                destructive=False,
                concurrency_safe=False,
                source="builtin",
                trusted=True,
                exposure="deferred",
                rendering_result="tool_message",
                tags=("subagent", "fork", "resume"),
            )
        )
    if "run_fork" in tool_by_name:
        capabilities.append(
            ToolCapability(
                name="run_fork",
                tool=tool_by_name["run_fork"],
                domain="subagents",
                family="subagents",
                mutation="orchestration",
                execution="fork_bridge",
                read_only=False,
                destructive=False,
                concurrency_safe=False,
                source="builtin",
                trusted=True,
                exposure="main",
                rendering_result="tool_message",
                tags=("subagent", "fork"),
            )
        )
    return tuple(capabilities)
