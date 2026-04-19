from __future__ import annotations

from pathlib import Path

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool

from coding_deepgent.filesystem import glob_search, grep_search, read_file
from coding_deepgent.runtime import RuntimeContext
from coding_deepgent.subagents.loader import (
    discover_local_subagent_definitions,
    discover_plugin_subagent_definitions,
)
from coding_deepgent.subagents.schemas import AgentDefinition
from coding_deepgent.tasks import plan_get, task_get, task_list
from coding_deepgent.tool_system.capabilities import (
    CapabilityRegistry,
    ToolCapability,
    build_capability_registry,
)

FILE_ONLY_CHILD_TOOLS = ("read_file", "glob", "grep")
DEFAULT_CHILD_TOOLS = ("read_file", "glob", "grep", "task_get", "task_list", "plan_get")
EXPLORE_CHILD_TOOLS = FILE_ONLY_CHILD_TOOLS
PLAN_CHILD_TOOLS = DEFAULT_CHILD_TOOLS
VERIFIER_EXTRA_TOOLS = ()
FORBIDDEN_CHILD_TOOLS = (
    "bash",
    "write_file",
    "edit_file",
    "TodoWrite",
    "save_memory",
    "task_create",
    "task_update",
    "plan_save",
    "load_skill",
    "run_subagent",
    "run_fork",
)
CHILD_TOOL_OBJECTS: dict[str, BaseTool] = {
    "read_file": read_file,
    "glob": glob_search,
    "grep": grep_search,
    "task_get": task_get,
    "task_list": task_list,
    "plan_get": plan_get,
}

BUILTIN_AGENT_DEFINITIONS: dict[str, AgentDefinition] = {
    "general": AgentDefinition(
        agent_type="general",
        description="Read-only general-purpose research subagent.",
        when_to_use=(
            "Use for bounded codebase research, file inspection, and durable "
            "task/plan reads that do not modify workspace or state."
        ),
        instructions=(
            "You are a read-only general-purpose research subagent. Inspect the "
            "workspace and durable task/plan state, then return a concise answer "
            "to the parent agent."
        ),
        tool_allowlist=DEFAULT_CHILD_TOOLS,
        disallowed_tools=FORBIDDEN_CHILD_TOOLS,
        max_turns=25,
        model_profile=None,
    ),
    "verifier": AgentDefinition(
        agent_type="verifier",
        description="Read-only verification specialist for saved plan artifacts.",
        when_to_use=(
            "Use after implementation to inspect evidence against a durable "
            "plan and return PASS, FAIL, or PARTIAL."
        ),
        instructions=(
            "You are a verification specialist. Your role is to verify the "
            "implementation against the plan and try to find breakage, not to "
            "confirm success quickly."
        ),
        tool_allowlist=DEFAULT_CHILD_TOOLS,
        disallowed_tools=FORBIDDEN_CHILD_TOOLS,
        max_turns=5,
        model_profile=None,
    ),
    "explore": AgentDefinition(
        agent_type="explore",
        description="Read-only code exploration specialist.",
        when_to_use=(
            "Use for targeted repository exploration, relevant-file discovery, "
            "and grounded codebase explanation."
        ),
        instructions=(
            "You are a read-only exploration specialist. Inspect the repository, "
            "identify the most relevant files and concrete code paths, and report "
            "findings without speculating beyond the evidence you can read."
        ),
        tool_allowlist=EXPLORE_CHILD_TOOLS,
        disallowed_tools=FORBIDDEN_CHILD_TOOLS,
        max_turns=12,
        model_profile=None,
    ),
    "plan": AgentDefinition(
        agent_type="plan",
        description="Read-only planning specialist for implementation shaping.",
        when_to_use=(
            "Use for turning a goal into a concrete implementation plan, risk "
            "list, and execution order grounded in current repository state."
        ),
        instructions=(
            "You are a read-only planning specialist. Use the repository and "
            "durable task/plan state to produce a concrete implementation plan, "
            "call out risks, and keep recommendations tightly grounded in the "
            "current codebase."
        ),
        tool_allowlist=PLAN_CHILD_TOOLS,
        disallowed_tools=FORBIDDEN_CHILD_TOOLS,
        max_turns=15,
        model_profile=None,
    ),
}


def _child_tool_capability(name: str) -> ToolCapability:
    tool_object = CHILD_TOOL_OBJECTS[name]
    if name in {"task_get", "task_list", "plan_get"}:
        return ToolCapability(
            name=name,
            tool=tool_object,
            domain="task",
            read_only=True,
            destructive=False,
            concurrency_safe=True,
            family="task",
            mutation="read",
            execution="plain_tool",
            source="builtin",
            trusted=True,
            exposure="child_only",
            rendering_result="tool_message",
            tags=("read", "durable_store"),
        )
    return ToolCapability(
        name=name,
        tool=tool_object,
        domain="filesystem",
        read_only=True,
        destructive=False,
        concurrency_safe=True,
        family="filesystem",
        mutation="read",
        execution="plain_tool",
        source="builtin",
        trusted=True,
        exposure="child_only",
        rendering_result="tool_message",
        tags=("read", "workspace"),
    )


def agent_definition(agent_type: str) -> AgentDefinition:
    return BUILTIN_AGENT_DEFINITIONS[agent_type]


def child_tool_allowlist(agent_type: str) -> tuple[str, ...]:
    return agent_definition(agent_type).tool_allowlist


def child_capability_registry() -> CapabilityRegistry:
    return build_capability_registry(
        builtin_capabilities=tuple(
            _child_tool_capability(name) for name in CHILD_TOOL_OBJECTS
        ),
        extension_capabilities=(),
    )


def _validate_agent_definition(definition: AgentDefinition) -> None:
    unknown_tools = sorted(
        item for item in definition.tool_allowlist if item not in CHILD_TOOL_OBJECTS
    )
    if unknown_tools:
        raise ValueError(
            f"Unknown child tools in `{definition.agent_type}`: {', '.join(unknown_tools)}"
        )
    unknown_disallowed = sorted(
        item
        for item in definition.disallowed_tools
        if item not in CHILD_TOOL_OBJECTS and item not in FORBIDDEN_CHILD_TOOLS
    )
    if unknown_disallowed:
        raise ValueError(
            "Unknown disallowed tools in "
            f"`{definition.agent_type}`: {', '.join(unknown_disallowed)}"
        )


def _runtime_workdir(runtime: ToolRuntime | None) -> Path | None:
    context = getattr(runtime, "context", None)
    if isinstance(context, RuntimeContext):
        return context.workdir
    return None


def _runtime_plugin_dir(runtime: ToolRuntime | None) -> Path:
    context = getattr(runtime, "context", None)
    if isinstance(context, RuntimeContext):
        return context.plugin_dir
    return Path("plugins")


def _agent_definitions_for_workdir(
    workdir: Path | None,
    *,
    plugin_dir: Path,
) -> dict[str, AgentDefinition]:
    definitions: dict[str, AgentDefinition] = dict(BUILTIN_AGENT_DEFINITIONS)
    if workdir is None:
        return definitions
    for definition in discover_plugin_subagent_definitions(
        workdir=workdir,
        plugin_dir=plugin_dir,
    ):
        if definition.agent_type in definitions:
            raise ValueError(
                f"Subagent definition `{definition.agent_type}` collides with an existing agent"
            )
        _validate_agent_definition(definition)
        definitions[definition.agent_type] = definition
    for definition in discover_local_subagent_definitions(workdir=workdir):
        if definition.agent_type in definitions:
            raise ValueError(
                f"Subagent definition `{definition.agent_type}` collides with an existing agent"
            )
        _validate_agent_definition(definition)
        definitions[definition.agent_type] = definition
    return definitions


def resolve_agent_definition(
    agent_type: str, *, runtime: ToolRuntime | None = None
) -> AgentDefinition:
    definitions = _agent_definitions_for_workdir(
        _runtime_workdir(runtime),
        plugin_dir=_runtime_plugin_dir(runtime),
    )
    try:
        return definitions[agent_type]
    except KeyError as exc:
        raise KeyError(f"Unknown subagent definition: {agent_type}") from exc
