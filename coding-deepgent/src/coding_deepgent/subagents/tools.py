from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool

from coding_deepgent.compact.runtime_pressure import estimate_message_tokens
from coding_deepgent.filesystem import glob_search, grep_search, read_file
from coding_deepgent.rendering import latest_assistant_text
from coding_deepgent.runtime import RuntimeContext, RuntimeEvent, RuntimeInvocation
from coding_deepgent.sessions.evidence_events import append_runtime_event_evidence
from coding_deepgent.sessions.records import LoadedSession, SessionContext, SessionSidechainMessage
from coding_deepgent.sessions.store_jsonl import JsonlSessionStore
from coding_deepgent.settings import build_openai_model
from coding_deepgent.subagents.loader import (
    discover_local_subagent_definitions,
    discover_plugin_subagent_definitions,
)
from coding_deepgent.subagents.schemas import (
    AgentDefinition,
    ForkPlaceholderLayout,
    ForkResultEnvelope,
    RunSubagentInput,
    RunForkInput,
    SubagentType,
    SubagentResultEnvelope,
    ToolPoolIdentitySnapshot,
    ToolSurfaceSnapshot,
    VerifierSubagentResult,
)
from coding_deepgent.tasks import plan_get, task_get, task_list
from coding_deepgent.tasks.store import get_plan
from coding_deepgent.tool_system import (
    CapabilityRegistry,
    ToolCapability,
    ToolGuardMiddleware,
    ToolPoolProjection,
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
VERDICT_PATTERN = re.compile(
    r"^\s*VERDICT:\s*(PASS|FAIL|PARTIAL)\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)
VERDICT_STATUS = {
    "PASS": "passed",
    "FAIL": "failed",
    "PARTIAL": "partial",
}
FORK_RECURSION_GUARD_MARKER = "<CODING_DEEPGENT_FORK>"
FORK_PLACEHOLDER_LAYOUT_VERSION = "fork_tool_result_v1"
FORK_REPLACEMENT_STATE_HOOK = "preserve_tool_result_ids"
SUBAGENT_RESUME_VERSION = "subagent_resume_v1"
FORK_RESUME_VERSION = "fork_resume_v1"
DEFAULT_RESUME_FOLLOW_UP = "Continue the current task from the recorded sidechain state."
DEFAULT_FORK_RESUME_FOLLOW_UP = "Continue the current branch from the recorded fork state."
READ_ONLY_BOUNDARY_PROMPT = (
    "You are strictly read-only. Do not modify files, tasks, plans, memory, or "
    "invoke nested subagents. If a task requires mutation, explain what the "
    "parent agent should do instead."
)
FORK_MAX_TURNS = 25

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


@dataclass(frozen=True, slots=True)
class SubagentResult:
    content: str
    agent_type: str
    tool_allowlist: tuple[str, ...]
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    total_duration_ms: int = 0
    total_tool_use_count: int = 0
    plan_id: str | None = None
    plan_title: str | None = None
    verification: str | None = None
    task_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ForkResult:
    content: str
    fork_run_id: str
    parent_thread_id: str
    child_thread_id: str
    rendered_prompt_fingerprint: str
    tool_pool_identity: ToolPoolIdentitySnapshot
    placeholder_layout: ForkPlaceholderLayout
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    total_duration_ms: int = 0
    total_tool_use_count: int = 0


ChildAgentFactory = Callable[[str, Sequence[str]], Callable[[str], str]]


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


def _fingerprint_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


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


def _tool_surface_snapshot(projection: ToolPoolProjection) -> ToolPoolIdentitySnapshot:
    tools: list[ToolSurfaceSnapshot] = []
    for visible_order, capability in enumerate(projection.capabilities):
        schema = cast(Any, capability.tool.tool_call_schema).model_json_schema()
        tools.append(
            ToolSurfaceSnapshot(
                name=capability.name,
                visible_order=visible_order,
                schema_fingerprint=_fingerprint_text(_stable_json(schema)),
                description=str(getattr(capability.tool, "description", "")).strip()
                or capability.name,
            )
        )
    fingerprint = _fingerprint_text(
        _stable_json([tool.model_dump() for tool in tools])
    )
    return ToolPoolIdentitySnapshot(fingerprint=fingerprint, tools=tools)


def _fork_placeholder_layout(messages: Sequence[BaseMessage]) -> ForkPlaceholderLayout:
    paired_tool_call_ids = [
        message.tool_call_id.strip()
        for message in messages
        if isinstance(message, ToolMessage)
        and isinstance(message.tool_call_id, str)
        and message.tool_call_id.strip()
    ]
    return ForkPlaceholderLayout(
        version=FORK_PLACEHOLDER_LAYOUT_VERSION,
        paired_tool_call_ids=paired_tool_call_ids,
        placeholder_messages=[
            f"<fork-tool-result:{tool_call_id}>"
            for tool_call_id in paired_tool_call_ids
        ],
        replacement_state_hook=FORK_REPLACEMENT_STATE_HOOK,
    )


def _fork_directive(intent: str) -> str:
    return "\n".join(
        [
            FORK_RECURSION_GUARD_MARKER,
            "Fork child contract: inherit the parent rendered prompt and visible tools exactly.",
            f"Branch intent: {intent.strip()}",
            "Return only the branch result needed by the parent.",
        ]
    )


def _verifier_task_prompt(
    *,
    task: str,
    plan_id: str,
    plan_title: str,
    content: str,
    verification: str,
    task_ids: Sequence[str],
) -> str:
    task_refs = ", ".join(task_ids) if task_ids else "(none)"
    return "\n".join(
        [
            "Verifier task:",
            task,
            "",
            f"Plan ID: {plan_id}",
            f"Plan title: {plan_title}",
            f"Verification criteria: {verification}",
            f"Referenced task IDs: {task_refs}",
            "",
            "Plan content:",
            content,
        ]
    )


def _agent_system_prompt(*, definition: AgentDefinition, context: RuntimeContext) -> str:
    allowed_tools = ", ".join(definition.tool_allowlist)
    sections = [
        definition.instructions
        or "You are a read-only subagent. Use the available tools only when they materially improve the result.",
        READ_ONLY_BOUNDARY_PROMPT,
    ]
    if definition.agent_type == "verifier":
        sections.append(
            "Use only the available tools when they materially improve the verification result. "
            "Cite concrete evidence from commands or tool reads in your final answer."
        )
    sections.extend(
        [
            f"Workspace: {context.workdir}",
            f"Allowed tools: {allowed_tools}",
        ]
    )
    if definition.agent_type == "verifier":
        sections.append(
            "End with a final line exactly `VERDICT: PASS`, `VERDICT: FAIL`, or `VERDICT: PARTIAL`."
        )
    return "\n\n".join(sections)


def _effective_max_turns(definition: AgentDefinition, requested_max_turns: int | None) -> int:
    if requested_max_turns is None:
        return definition.max_turns
    return min(requested_max_turns, definition.max_turns)


def _recursion_limit_for_max_turns(max_turns: int) -> int:
    return max(3, (max_turns * 2) + 1)


def _build_thread_config(*, thread_id: str, max_turns: int) -> dict[str, Any]:
    return {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": _recursion_limit_for_max_turns(max_turns),
    }


def _runtime_visible_tool_projection(runtime: ToolRuntime) -> ToolPoolProjection:
    context = getattr(runtime, "context", None)
    projection = getattr(context, "visible_tool_projection", None)
    if not isinstance(projection, ToolPoolProjection):
        raise RuntimeError("Fork requires a visible tool projection in runtime context")
    return projection


def _runtime_rendered_system_prompt(runtime: ToolRuntime) -> str:
    context = getattr(runtime, "context", None)
    prompt = getattr(context, "rendered_system_prompt", None)
    if not isinstance(prompt, str) or not prompt.strip():
        raise RuntimeError("Fork requires a rendered system prompt in runtime context")
    return prompt


def _runtime_tool_policy(runtime: ToolRuntime) -> Any:
    context = getattr(runtime, "context", None)
    return cast(Any, getattr(context, "tool_policy", None))


def _child_runtime_invocation(
    *,
    runtime: ToolRuntime,
    definition: AgentDefinition,
    max_turns: int,
    run_id: str | None = None,
) -> RuntimeInvocation:
    context = getattr(runtime, "context", None)
    if not isinstance(context, RuntimeContext):
        raise RuntimeError("Subagent requires runtime context")
    parent_config = getattr(runtime, "config", None)
    parent_thread_id = context.session_id
    if isinstance(parent_config, dict):
        configurable = parent_config.get("configurable", {})
        if isinstance(configurable, dict):
            parent_thread_id = str(configurable.get("thread_id", parent_thread_id))
    suffix = f":{run_id}" if run_id else ""
    return RuntimeInvocation(
        context=replace(
            context,
            agent_name=f"{context.agent_name}-{definition.agent_type}",
            entrypoint=f"run_subagent:{definition.agent_type}",
        ),
        config=_build_thread_config(
            thread_id=f"{parent_thread_id}:{definition.agent_type}{suffix}",
            max_turns=max_turns,
        ),
    )


def _fork_runtime_invocation(
    *,
    runtime: ToolRuntime,
    max_turns: int,
    run_id: str,
) -> RuntimeInvocation:
    context = getattr(runtime, "context", None)
    if not isinstance(context, RuntimeContext):
        raise RuntimeError("Fork requires runtime context")
    parent_thread_id = _runtime_thread_id(runtime)
    visible_tool_projection = _runtime_visible_tool_projection(runtime)
    rendered_system_prompt = _runtime_rendered_system_prompt(runtime)
    return RuntimeInvocation(
        context=replace(
            context,
            agent_name=f"{context.agent_name}-fork",
            entrypoint="run_fork",
            rendered_system_prompt=rendered_system_prompt,
            visible_tool_projection=visible_tool_projection,
            tool_policy=_runtime_tool_policy(runtime),
        ),
        config=_build_thread_config(
            thread_id=f"{parent_thread_id}:fork:{run_id}",
            max_turns=max_turns,
        ),
    )


def _child_tools(definition: AgentDefinition) -> list[BaseTool]:
    return child_capability_registry().tools_for_names(definition.tool_allowlist)


def _child_middleware(definition: AgentDefinition) -> list[ToolGuardMiddleware]:
    registry = child_capability_registry()
    return [ToolGuardMiddleware(registry=registry)]


def _fork_middleware(runtime: ToolRuntime, projection: ToolPoolProjection) -> list[ToolGuardMiddleware]:
    registry = CapabilityRegistry(projection.capabilities)
    return [
        ToolGuardMiddleware(
            registry=registry,
            policy=cast(Any, _runtime_tool_policy(runtime)),
        )
    ]


def _fork_source_messages(runtime: ToolRuntime) -> list[BaseMessage]:
    state = getattr(runtime, "state", None)
    if not isinstance(state, dict):
        raise RuntimeError("Fork requires runtime state messages")
    messages = state.get("messages")
    if not isinstance(messages, list) or not all(
        isinstance(message, BaseMessage) for message in messages
    ):
        raise RuntimeError("Fork requires runtime state messages")
    return list(messages)


def _message_tool_call_ids(message: BaseMessage) -> tuple[str, ...]:
    if isinstance(message, AIMessage):
        return tuple(
            str(item.get("id", "")).strip()
            for item in message.tool_calls
            if isinstance(item, dict) and str(item.get("id", "")).strip()
        )
    content = getattr(message, "content", None)
    if isinstance(content, list):
        return tuple(
            str(block.get("id", "")).strip()
            for block in content
            if isinstance(block, dict)
            and block.get("type") == "tool_use"
            and str(block.get("id", "")).strip()
        )
    return ()


def _tool_result_call_id(message: BaseMessage) -> str | None:
    if isinstance(message, ToolMessage):
        tool_call_id = getattr(message, "tool_call_id", None)
        if isinstance(tool_call_id, str) and tool_call_id.strip():
            return tool_call_id.strip()
    return None


def _normalize_fork_source_messages(
    source_messages: Sequence[BaseMessage],
) -> list[BaseMessage]:
    paired_tool_result_ids = {
        tool_call_id
        for message in source_messages
        if (tool_call_id := _tool_result_call_id(message)) is not None
    }
    normalized: list[BaseMessage] = []
    for message in source_messages:
        tool_call_ids = _message_tool_call_ids(message)
        if tool_call_ids and any(
            tool_call_id not in paired_tool_result_ids
            for tool_call_id in tool_call_ids
        ):
            continue
        normalized.append(message)
    return normalized


def _message_contains_marker(message: BaseMessage, marker: str) -> bool:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return marker in content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str) and marker in text:
                    return True
    return False


def _fork_recursion_guard(
    *,
    runtime: ToolRuntime,
    source_messages: Sequence[BaseMessage],
) -> str | None:
    context = getattr(runtime, "context", None)
    if isinstance(context, RuntimeContext) and context.entrypoint == "run_fork":
        return "Fork blocked: fork children cannot spawn nested forks."
    if any(
        _message_contains_marker(message, FORK_RECURSION_GUARD_MARKER)
        for message in source_messages
    ):
        return "Fork blocked: recursion guard marker already exists in the active message prefix."
    return None


def _fork_payload_messages(
    *,
    source_messages: Sequence[BaseMessage],
    intent: str,
) -> list[BaseMessage]:
    normalized_messages = _normalize_fork_source_messages(source_messages)
    return [*normalized_messages, HumanMessage(content=_fork_directive(intent))]


def _execute_child_subagent(
    *,
    task: str,
    runtime: ToolRuntime,
    definition: AgentDefinition,
    max_turns: int,
    run_id: str | None = None,
) -> dict[str, Any]:
    from coding_deepgent.agent_runtime_service import invoke_agent

    invocation = _child_runtime_invocation(
        runtime=runtime,
        definition=definition,
        max_turns=max_turns,
        run_id=run_id,
    )
    system_prompt = _agent_system_prompt(
        definition=definition, context=invocation.context
    )
    agent = cast(
        Any,
        create_agent,
    )(
        model=build_openai_model(model_name=definition.model_profile),
        tools=_child_tools(definition),
        system_prompt=system_prompt,
        middleware=_child_middleware(definition),
        context_schema=RuntimeContext,
        store=runtime.store,
        name=invocation.context.agent_name,
    )
    result = invoke_agent(
        agent,
        {"messages": [{"role": "user", "content": task}]},
        invocation,
    )
    content = _final_child_text(result).strip()
    if not content:
        raise RuntimeError("Subagent returned no assistant content")
    return {"content": content, "raw_result": result, "invocation": invocation}


def _enqueue_agent_private_memory(
    *,
    invocation: RuntimeInvocation,
    source: str,
    task: str,
    content: str,
) -> None:
    service = getattr(invocation.context, "memory_service", None)
    if service is None:
        return
    agent_scope = invocation.context.agent_name
    if not isinstance(agent_scope, str) or not agent_scope.strip():
        return
    service.enqueue_extraction(
        project_scope=str(invocation.context.workdir),
        agent_scope=agent_scope,
        source=source,
        text=f"Task: {task}\n\nAssistant: {content}",
    )


def _final_child_text(result: Any) -> str:
    content = latest_assistant_text(result).strip()
    if content:
        return content
    messages = result.get("messages", []) if isinstance(result, dict) else []
    for message in reversed(messages):
        if isinstance(message, dict):
            text = str(message.get("content") or "").strip()
        else:
            text = str(getattr(message, "content", "") or "").strip()
        if text:
            return text
    return ""


def _tool_use_count(result: Any) -> int:
    messages = result.get("messages", []) if isinstance(result, dict) else []
    count = 0
    for message in messages:
        if isinstance(message, AIMessage):
            count += len(message.tool_calls)
            continue
        if not isinstance(message, dict):
            continue
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            count += len(tool_calls)
        content = message.get("content")
        if isinstance(content, list):
            count += sum(
                1
                for block in content
                if isinstance(block, dict) and block.get("type") == "tool_use"
            )
    return count


def _result_metrics(
    *,
    task: str,
    content: str,
    raw_result: Any,
    duration_ms: int,
) -> dict[str, int]:
    input_tokens = estimate_message_tokens([HumanMessage(content=task)])
    output_tokens = estimate_message_tokens([HumanMessage(content=content)])
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "total_duration_ms": duration_ms,
        "total_tool_use_count": _tool_use_count(raw_result),
    }


def _definition_origin(agent_type: str) -> str:
    if agent_type in BUILTIN_AGENT_DEFINITIONS:
        return "builtin"
    if ":" in agent_type:
        return "plugin"
    return "local"


def _activity_summary(content: str, *, limit: int = 72) -> str:
    first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
    if not first_line:
        return "No summary yet."
    if len(first_line) <= limit:
        return first_line
    return f"{first_line[: limit - 3].rstrip()}..."


def _runtime_workdir_string(runtime: ToolRuntime | None) -> str:
    workdir = _runtime_workdir(runtime)
    if workdir is None:
        return ""
    return str(workdir.resolve())


def _validate_recorded_workdir(
    *,
    runtime: ToolRuntime,
    metadata: dict[str, Any],
) -> None:
    expected_workdir = metadata.get("workdir")
    if not isinstance(expected_workdir, str) or not expected_workdir.strip():
        return
    current_workdir = _runtime_workdir(runtime)
    if current_workdir is None:
        raise RuntimeError("Resume requires runtime workdir context")
    if str(current_workdir.resolve()) != expected_workdir.strip():
        raise RuntimeError("Resume requires the same recorded workdir")
    if not current_workdir.exists() or not current_workdir.is_dir():
        raise RuntimeError("Resume requires an existing recorded workdir")


def _subagent_resume_metadata(
    *,
    definition: AgentDefinition,
    runtime: ToolRuntime | None,
    requested_max_turns: int | None,
    effective_max_turns: int,
    plan_id: str | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "resume_version": SUBAGENT_RESUME_VERSION,
        "agent_origin": _definition_origin(definition.agent_type),
        "requested_max_turns": requested_max_turns,
        "effective_max_turns": effective_max_turns,
        "model_profile": definition.model_profile,
        "tool_allowlist": list(definition.tool_allowlist),
        "workdir": _runtime_workdir_string(runtime),
    }
    if plan_id is not None:
        metadata["plan_id"] = plan_id
    return metadata


def _fork_resume_metadata(
    *,
    runtime: ToolRuntime | None,
    run_id: str,
    requested_max_turns: int | None,
    effective_max_turns: int,
    tool_pool_identity: ToolPoolIdentitySnapshot,
    prompt_fingerprint: str,
    placeholder_layout: ForkPlaceholderLayout,
) -> dict[str, Any]:
    return {
        "resume_version": FORK_RESUME_VERSION,
        "fork_run_id": run_id,
        "requested_max_turns": requested_max_turns,
        "effective_max_turns": effective_max_turns,
        "tool_pool_fingerprint": tool_pool_identity.fingerprint,
        "rendered_prompt_fingerprint": prompt_fingerprint,
        "placeholder_layout_version": placeholder_layout.version,
        "placeholder_messages": list(placeholder_layout.placeholder_messages),
        "workdir": _runtime_workdir_string(runtime),
    }


def _sidechain_entry_metadata(message: Any) -> dict[str, Any] | None:
    metadata: dict[str, Any] = {}
    if isinstance(message, ToolMessage):
        tool_call_id = getattr(message, "tool_call_id", None)
        if isinstance(tool_call_id, str) and tool_call_id.strip():
            metadata["tool_call_id"] = tool_call_id.strip()
    if isinstance(message, AIMessage) and message.tool_calls:
        metadata["tool_calls"] = _json_clone(message.tool_calls)
    if isinstance(message, dict):
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            metadata["tool_calls"] = _json_clone(tool_calls)
        tool_call_id = message.get("tool_call_id")
        if isinstance(tool_call_id, str) and tool_call_id.strip():
            metadata["tool_call_id"] = tool_call_id.strip()
        content = message.get("content")
    else:
        content = getattr(message, "content", "")
    if isinstance(content, list) and content:
        metadata["structured_content"] = _json_clone(content)
    return metadata or None


def _merge_sidechain_metadata(
    root_metadata: dict[str, Any] | None,
    entry_metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if root_metadata is None and entry_metadata is None:
        return None
    merged: dict[str, Any] = {}
    if root_metadata is not None:
        merged.update(_json_clone(root_metadata))
    if entry_metadata is not None:
        merged["sidechain_entry"] = _json_clone(entry_metadata)
    return merged


def _record_sidechain_messages(
    *,
    runtime: ToolRuntime | None,
    agent_type: str,
    child_invocation: RuntimeInvocation,
    task: str,
    raw_result: Any,
    metadata: dict[str, Any] | None = None,
) -> bool:
    if runtime is None:
        return False
    context = getattr(runtime, "context", None)
    if not isinstance(context, RuntimeContext):
        return False
    session_context = context.session_context
    if not isinstance(session_context, SessionContext):
        return False
    store = JsonlSessionStore(session_context.store_dir)
    parent_message_id = store.latest_message_id(session_context)
    parent_thread_id = _runtime_thread_id(runtime)
    subagent_thread_id = str(
        child_invocation.config.get("configurable", {}).get(
            "thread_id", child_invocation.context.session_id
        )
    )
    store.append_sidechain_message(
        session_context,
        agent_type=agent_type,
        role="user",
        content=task,
        subagent_thread_id=subagent_thread_id,
        parent_message_id=parent_message_id,
        parent_thread_id=parent_thread_id,
        metadata=metadata,
    )
    for role, content, entry_metadata in _sidechain_message_entries(raw_result):
        store.append_sidechain_message(
            session_context,
            agent_type=agent_type,
            role=role,
            content=content,
            subagent_thread_id=subagent_thread_id,
            parent_message_id=parent_message_id,
            parent_thread_id=parent_thread_id,
            metadata=_merge_sidechain_metadata(metadata, entry_metadata),
        )
    return True


def _sidechain_message_entries(
    raw_result: Any,
) -> list[tuple[str, str, dict[str, Any] | None]]:
    messages = raw_result.get("messages", []) if isinstance(raw_result, dict) else []
    entries: list[tuple[str, str, dict[str, Any] | None]] = []
    for message in messages:
        role = _sidechain_message_role(message)
        content = _sidechain_message_text(message)
        if role is None or not content:
            continue
        entries.append((role, content, _sidechain_entry_metadata(message)))
    return entries


def _sidechain_thread_entries(
    loaded: LoadedSession, *, thread_id: str
) -> list[SessionSidechainMessage]:
    return [
        item for item in loaded.sidechain_messages if item.subagent_thread_id == thread_id
    ]


def _sidechain_root_metadata(
    entries: Sequence[SessionSidechainMessage],
) -> dict[str, Any]:
    if not entries:
        raise RuntimeError("No sidechain messages recorded for the requested thread")
    metadata = entries[0].metadata
    if not isinstance(metadata, dict):
        return {}
    return metadata


def _reconstruct_sidechain_message(entry: SessionSidechainMessage) -> BaseMessage:
    metadata = entry.metadata or {}
    sidechain_entry = metadata.get("sidechain_entry")
    structured_content = (
        sidechain_entry.get("structured_content")
        if isinstance(sidechain_entry, dict)
        else None
    )
    content: Any = structured_content if structured_content is not None else entry.content
    if entry.role == "assistant":
        tool_calls = (
            sidechain_entry.get("tool_calls")
            if isinstance(sidechain_entry, dict)
            else None
        )
        if isinstance(tool_calls, list) and tool_calls:
            return AIMessage(content=content, tool_calls=cast(Any, tool_calls))
        return AIMessage(content=content)
    if entry.role == "tool":
        tool_call_id = (
            sidechain_entry.get("tool_call_id")
            if isinstance(sidechain_entry, dict)
            else None
        )
        if not isinstance(tool_call_id, str) or not tool_call_id.strip():
            raise RuntimeError(
                f"Cannot resume tool sidechain message without tool_call_id for thread {entry.subagent_thread_id}"
            )
        return ToolMessage(content=content, tool_call_id=tool_call_id.strip())
    if entry.role == "system":
        return SystemMessage(content=content)
    return HumanMessage(content=content)


def _resume_sidechain_messages(
    loaded: LoadedSession, *, thread_id: str
) -> tuple[list[SessionSidechainMessage], list[BaseMessage]]:
    entries = _sidechain_thread_entries(loaded, thread_id=thread_id)
    if not entries:
        raise RuntimeError(f"Unknown sidechain thread: {thread_id}")
    return entries, [_reconstruct_sidechain_message(item) for item in entries]


def _recorded_effective_max_turns(
    metadata: dict[str, Any], *, fallback: int
) -> int:
    value = metadata.get("effective_max_turns")
    if isinstance(value, int) and value >= 1:
        return value
    return fallback


def _sidechain_message_role(message: Any) -> str | None:
    if isinstance(message, dict):
        role = message.get("role")
        return str(role) if isinstance(role, str) and role else None
    message_type = getattr(message, "type", None)
    if isinstance(message_type, str) and message_type:
        return "assistant" if message_type == "ai" else message_type
    return None


def _sidechain_message_text(message: Any) -> str:
    if isinstance(message, dict):
        content = message.get("content")
    else:
        content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        texts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())
        return "\n".join(texts).strip()
    return str(content).strip() if content else ""


def verifier_verdict(content: str) -> str | None:
    match = VERDICT_PATTERN.search(content)
    if match is None:
        return None
    return match.group(1).upper()


def verifier_evidence_summary(content: str, *, verdict: str) -> str:
    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not VERDICT_PATTERN.match(line)
    ]
    summary = lines[0] if lines else f"Verifier verdict: {verdict}"
    if len(summary) <= 240:
        return summary
    return f"{summary[:237].rstrip()}..."


def record_verifier_evidence(
    *,
    result: SubagentResult,
    runtime: ToolRuntime,
) -> bool:
    if result.agent_type != "verifier":
        return False
    verdict = verifier_verdict(result.content)
    if verdict is None:
        return False
    context = getattr(runtime, "context", None)
    session_context = getattr(context, "session_context", None)
    if not isinstance(session_context, SessionContext):
        return False
    parent_thread_id = _runtime_thread_id(runtime)
    child_thread_id = (
        f"{parent_thread_id}:verifier:{result.plan_id}"
        if result.plan_id
        else f"{parent_thread_id}:verifier"
    )
    verifier_agent_name = _runtime_agent_name(runtime)

    JsonlSessionStore(session_context.store_dir).append_evidence(
        session_context,
        kind="verification",
        summary=verifier_evidence_summary(result.content, verdict=verdict),
        status=VERDICT_STATUS[verdict],
        subject=result.plan_id,
        metadata={
            "plan_id": result.plan_id or "",
            "plan_title": result.plan_title or "",
            "verdict": verdict,
            "parent_session_id": session_context.session_id,
            "parent_thread_id": parent_thread_id,
            "child_thread_id": child_thread_id,
            "verifier_agent_name": verifier_agent_name,
            "task_ids": list(result.task_ids),
            "tool_allowlist": list(result.tool_allowlist),
        },
    )
    return True


def _runtime_thread_id(runtime: ToolRuntime) -> str:
    context = getattr(runtime, "context", None)
    fallback = str(getattr(context, "session_id", "unknown"))
    config = getattr(runtime, "config", None)
    if not isinstance(config, dict):
        return fallback
    configurable = config.get("configurable")
    if not isinstance(configurable, dict):
        return fallback
    return str(configurable.get("thread_id", fallback))


def _runtime_agent_name(runtime: ToolRuntime) -> str:
    context = getattr(runtime, "context", None)
    parent_agent_name = str(getattr(context, "agent_name", "coding-deepgent"))
    return f"{parent_agent_name}-verifier"


def _resumed_child_runtime_invocation(
    *,
    runtime: ToolRuntime,
    definition: AgentDefinition,
    thread_id: str,
    max_turns: int,
) -> RuntimeInvocation:
    context = getattr(runtime, "context", None)
    if not isinstance(context, RuntimeContext):
        raise RuntimeError("Subagent resume requires runtime context")
    return RuntimeInvocation(
        context=replace(
            context,
            agent_name=f"{context.agent_name}-{definition.agent_type}",
            entrypoint=f"run_subagent:{definition.agent_type}",
        ),
        config=_build_thread_config(thread_id=thread_id, max_turns=max_turns),
    )


def _resumed_fork_runtime_invocation(
    *,
    runtime: ToolRuntime,
    thread_id: str,
    max_turns: int,
) -> RuntimeInvocation:
    context = getattr(runtime, "context", None)
    if not isinstance(context, RuntimeContext):
        raise RuntimeError("Fork resume requires runtime context")
    rendered_system_prompt = _runtime_rendered_system_prompt(runtime)
    visible_tool_projection = _runtime_visible_tool_projection(runtime)
    return RuntimeInvocation(
        context=replace(
            context,
            agent_name=f"{context.agent_name}-fork",
            entrypoint="run_fork",
            rendered_system_prompt=rendered_system_prompt,
            visible_tool_projection=visible_tool_projection,
            tool_policy=_runtime_tool_policy(runtime),
        ),
        config=_build_thread_config(thread_id=thread_id, max_turns=max_turns),
    )


def _execute_fork_subagent(
    *,
    intent: str,
    runtime: ToolRuntime,
    max_turns: int,
    run_id: str,
) -> dict[str, Any]:
    from coding_deepgent.agent_runtime_service import invoke_agent

    projection = _runtime_visible_tool_projection(runtime)
    invocation = _fork_runtime_invocation(
        runtime=runtime,
        max_turns=max_turns,
        run_id=run_id,
    )
    source_messages = _fork_source_messages(runtime)
    guard_message = _fork_recursion_guard(runtime=runtime, source_messages=source_messages)
    if guard_message is not None:
        raise RuntimeError(guard_message)
    agent = cast(
        Any,
        create_agent,
    )(
        model=build_openai_model(),
        tools=projection.tools(),
        system_prompt=_runtime_rendered_system_prompt(runtime),
        middleware=_fork_middleware(runtime, projection),
        context_schema=RuntimeContext,
        store=runtime.store,
        name=invocation.context.agent_name,
    )
    result = invoke_agent(
        agent,
        {"messages": _fork_payload_messages(source_messages=source_messages, intent=intent)},
        invocation,
    )
    content = _final_child_text(result).strip()
    if not content:
        raise RuntimeError("Fork returned no assistant content")
    return {
        "content": content,
        "raw_result": result,
        "invocation": invocation,
        "projection": projection,
        "source_messages": source_messages,
    }


def _load_recorded_sidechain_thread(
    *, runtime: ToolRuntime, thread_id: str
) -> tuple[LoadedSession, list[SessionSidechainMessage], list[BaseMessage]]:
    context = getattr(runtime, "context", None)
    if not isinstance(context, RuntimeContext):
        raise RuntimeError("Sidechain resume requires runtime context")
    session_context = context.session_context
    if not isinstance(session_context, SessionContext):
        raise RuntimeError("Sidechain resume requires a recorded session context")
    loaded = JsonlSessionStore(session_context.store_dir).load_session(
        session_id=session_context.session_id,
        workdir=session_context.workdir,
    )
    entries, messages = _resume_sidechain_messages(loaded, thread_id=thread_id)
    return loaded, entries, messages


def resume_subagent_task(
    *,
    subagent_thread_id: str,
    runtime: ToolRuntime,
    follow_up: str | None = None,
) -> SubagentResult:
    from coding_deepgent.agent_runtime_service import invoke_agent

    _, entries, messages = _load_recorded_sidechain_thread(
        runtime=runtime,
        thread_id=subagent_thread_id,
    )
    agent_type = entries[0].agent_type
    if agent_type == "fork":
        raise ValueError("Use resume_fork_task() for fork sidechain threads")
    definition = resolve_agent_definition(agent_type, runtime=runtime)
    root_metadata = _sidechain_root_metadata(entries)
    _validate_recorded_workdir(runtime=runtime, metadata=root_metadata)
    effective_max_turns = _recorded_effective_max_turns(
        root_metadata,
        fallback=definition.max_turns,
    )
    invocation = _resumed_child_runtime_invocation(
        runtime=runtime,
        definition=definition,
        thread_id=subagent_thread_id,
        max_turns=effective_max_turns,
    )
    follow_up_prompt = (follow_up or DEFAULT_RESUME_FOLLOW_UP).strip()
    agent = cast(
        Any,
        create_agent,
    )(
        model=build_openai_model(model_name=definition.model_profile),
        tools=_child_tools(definition),
        system_prompt=_agent_system_prompt(definition=definition, context=invocation.context),
        middleware=_child_middleware(definition),
        context_schema=RuntimeContext,
        store=runtime.store,
        name=invocation.context.agent_name,
    )
    started_at = time.perf_counter()
    result = invoke_agent(
        agent,
        {"messages": [*messages, HumanMessage(content=follow_up_prompt)]},
        invocation,
    )
    content = _final_child_text(result).strip()
    if not content:
        raise RuntimeError("Resumed subagent returned no assistant content")
    _record_sidechain_messages(
        runtime=runtime,
        agent_type=definition.agent_type,
        child_invocation=invocation,
        task=follow_up_prompt,
        raw_result=result,
        metadata=root_metadata,
    )
    _enqueue_agent_private_memory(
        invocation=invocation,
        source=f"subagent_{definition.agent_type}_resume",
        task=follow_up_prompt,
        content=content,
    )
    metrics = _result_metrics(
        task=follow_up_prompt,
        content=content,
        raw_result=result,
        duration_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
    )
    return SubagentResult(
        content=content,
        agent_type=definition.agent_type,
        tool_allowlist=definition.tool_allowlist,
        input_tokens=metrics["input_tokens"],
        output_tokens=metrics["output_tokens"],
        total_tokens=metrics["total_tokens"],
        total_duration_ms=metrics["total_duration_ms"],
        total_tool_use_count=metrics["total_tool_use_count"],
        plan_id=cast(Any, root_metadata.get("plan_id")) if agent_type == "verifier" else None,
    )


def resume_fork_task(
    *,
    child_thread_id: str,
    runtime: ToolRuntime,
    follow_up: str | None = None,
) -> ForkResult:
    from coding_deepgent.agent_runtime_service import invoke_agent

    _, entries, messages = _load_recorded_sidechain_thread(
        runtime=runtime,
        thread_id=child_thread_id,
    )
    if entries[0].agent_type != "fork":
        raise ValueError("Requested sidechain thread is not a fork thread")
    root_metadata = _sidechain_root_metadata(entries)
    _validate_recorded_workdir(runtime=runtime, metadata=root_metadata)
    expected_prompt_fingerprint = root_metadata.get("rendered_prompt_fingerprint")
    current_prompt_fingerprint = _fingerprint_text(_runtime_rendered_system_prompt(runtime))
    if (
        isinstance(expected_prompt_fingerprint, str)
        and expected_prompt_fingerprint != current_prompt_fingerprint
    ):
        raise RuntimeError("Fork resume requires the same rendered system prompt fingerprint")
    current_projection = _runtime_visible_tool_projection(runtime)
    current_tool_pool = _tool_surface_snapshot(current_projection)
    expected_tool_pool = root_metadata.get("tool_pool_fingerprint")
    if isinstance(expected_tool_pool, str) and expected_tool_pool != current_tool_pool.fingerprint:
        raise RuntimeError("Fork resume requires the same visible tool projection fingerprint")
    effective_max_turns = _recorded_effective_max_turns(
        root_metadata,
        fallback=FORK_MAX_TURNS,
    )
    invocation = _resumed_fork_runtime_invocation(
        runtime=runtime,
        thread_id=child_thread_id,
        max_turns=effective_max_turns,
    )
    follow_up_prompt = (follow_up or DEFAULT_FORK_RESUME_FOLLOW_UP).strip()
    agent = cast(
        Any,
        create_agent,
    )(
        model=build_openai_model(),
        tools=current_projection.tools(),
        system_prompt=_runtime_rendered_system_prompt(runtime),
        middleware=_fork_middleware(runtime, current_projection),
        context_schema=RuntimeContext,
        store=runtime.store,
        name=invocation.context.agent_name,
    )
    started_at = time.perf_counter()
    result = invoke_agent(
        agent,
        {"messages": [*messages, HumanMessage(content=follow_up_prompt)]},
        invocation,
    )
    content = _final_child_text(result).strip()
    if not content:
        raise RuntimeError("Resumed fork returned no assistant content")
    placeholder_layout = ForkPlaceholderLayout.model_validate(
        {
            "version": str(root_metadata.get("placeholder_layout_version", FORK_PLACEHOLDER_LAYOUT_VERSION)),
            "paired_tool_call_ids": [],
            "placeholder_messages": list(root_metadata.get("placeholder_messages", []))
            if isinstance(root_metadata.get("placeholder_messages"), list)
            else [],
            "replacement_state_hook": FORK_REPLACEMENT_STATE_HOOK,
        }
    )
    _record_sidechain_messages(
        runtime=runtime,
        agent_type="fork",
        child_invocation=invocation,
        task=follow_up_prompt,
        raw_result=result,
        metadata=root_metadata,
    )
    _enqueue_agent_private_memory(
        invocation=invocation,
        source="fork_resume",
        task=follow_up_prompt,
        content=content,
    )
    metrics = _result_metrics(
        task=follow_up_prompt,
        content=content,
        raw_result=result,
        duration_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
    )
    return ForkResult(
        content=content,
        fork_run_id=str(root_metadata.get("fork_run_id", "resumed")),
        parent_thread_id=_runtime_thread_id(runtime),
        child_thread_id=child_thread_id,
        rendered_prompt_fingerprint=current_prompt_fingerprint,
        tool_pool_identity=current_tool_pool,
        placeholder_layout=placeholder_layout,
        input_tokens=metrics["input_tokens"],
        output_tokens=metrics["output_tokens"],
        total_tokens=metrics["total_tokens"],
        total_duration_ms=metrics["total_duration_ms"],
        total_tool_use_count=metrics["total_tool_use_count"],
    )


def run_subagent_task(
    *,
    task: str,
    agent_type: str = "general",
    runtime: ToolRuntime | None = None,
    plan_id: str | None = None,
    max_turns: int | None = None,
    run_id: str | None = None,
    child_agent_factory: ChildAgentFactory | None = None,
) -> SubagentResult:
    definition = resolve_agent_definition(agent_type, runtime=runtime)
    allowlist = definition.tool_allowlist
    effective_max_turns = _effective_max_turns(definition, max_turns)
    guard_message = _subagent_spawn_pressure_guard(runtime)
    if guard_message is not None:
        output_tokens = estimate_message_tokens([HumanMessage(content=guard_message)])
        return SubagentResult(
            content=guard_message,
            agent_type=agent_type,
            tool_allowlist=allowlist,
            output_tokens=output_tokens,
            total_tokens=output_tokens,
        )
    if agent_type == "verifier":
        if runtime is None or runtime.store is None:
            raise RuntimeError("Verifier subagent requires task store")
        if plan_id is None:
            raise ValueError("Verifier subagent requires plan_id")
        plan = get_plan(runtime.store, plan_id)
        verifier_task = _verifier_task_prompt(
            task=task,
            plan_id=plan.id,
            plan_title=plan.title,
            content=plan.content,
            verification=plan.verification,
            task_ids=plan.task_ids,
        )
        started_at = time.perf_counter()
        if child_agent_factory is None:
            execution = _execute_child_subagent(
                task=verifier_task,
                runtime=runtime,
                definition=definition,
                max_turns=effective_max_turns,
                run_id=run_id or plan.id,
            )
            content = str(execution["content"])
            raw_result = execution["raw_result"]
            _record_sidechain_messages(
                runtime=runtime,
                agent_type=definition.agent_type,
                child_invocation=cast(RuntimeInvocation, execution["invocation"]),
                task=verifier_task,
                raw_result=raw_result,
                metadata=_subagent_resume_metadata(
                    definition=definition,
                    runtime=runtime,
                    requested_max_turns=max_turns,
                    effective_max_turns=effective_max_turns,
                    plan_id=plan.id,
                ),
            )
            _enqueue_agent_private_memory(
                invocation=cast(RuntimeInvocation, execution["invocation"]),
                source="subagent_verifier",
                task=verifier_task,
                content=content,
            )
        else:
            content = child_agent_factory(agent_type, allowlist)(verifier_task)
            raw_result = {"messages": [{"role": "assistant", "content": content}]}
        duration_ms = max(0, int((time.perf_counter() - started_at) * 1000))
        metrics = _result_metrics(
            task=verifier_task,
            content=content,
            raw_result=raw_result,
            duration_ms=duration_ms,
        )
        return SubagentResult(
            content=content,
            agent_type=agent_type,
            tool_allowlist=allowlist,
            input_tokens=metrics["input_tokens"],
            output_tokens=metrics["output_tokens"],
            total_tokens=metrics["total_tokens"],
            total_duration_ms=metrics["total_duration_ms"],
            total_tool_use_count=metrics["total_tool_use_count"],
            plan_id=plan.id,
            plan_title=plan.title,
            verification=plan.verification,
            task_ids=tuple(plan.task_ids),
        )
    if runtime is None:
        raise RuntimeError("General subagent requires runtime context")
    started_at = time.perf_counter()
    if child_agent_factory is None:
        execution = _execute_child_subagent(
            task=task,
            runtime=runtime,
            definition=definition,
            max_turns=effective_max_turns,
            run_id=run_id,
        )
        content = str(execution["content"])
        raw_result = execution["raw_result"]
        _record_sidechain_messages(
            runtime=runtime,
            agent_type=definition.agent_type,
            child_invocation=cast(RuntimeInvocation, execution["invocation"]),
            task=task,
            raw_result=raw_result,
            metadata=_subagent_resume_metadata(
                definition=definition,
                runtime=runtime,
                requested_max_turns=max_turns,
                effective_max_turns=effective_max_turns,
            ),
        )
        _enqueue_agent_private_memory(
            invocation=cast(RuntimeInvocation, execution["invocation"]),
            source=f"subagent_{definition.agent_type}",
            task=task,
            content=content,
        )
    else:
        content = child_agent_factory(agent_type, allowlist)(task)
        raw_result = {"messages": [{"role": "assistant", "content": content}]}
    duration_ms = max(0, int((time.perf_counter() - started_at) * 1000))
    metrics = _result_metrics(
        task=task,
        content=content,
        raw_result=raw_result,
        duration_ms=duration_ms,
    )
    return SubagentResult(
        content=content,
        agent_type=agent_type,
        tool_allowlist=allowlist,
        input_tokens=metrics["input_tokens"],
        output_tokens=metrics["output_tokens"],
        total_tokens=metrics["total_tokens"],
        total_duration_ms=metrics["total_duration_ms"],
        total_tool_use_count=metrics["total_tool_use_count"],
    )


def run_fork_task(
    *,
    intent: str,
    runtime: ToolRuntime,
    max_turns: int | None = None,
    run_id: str | None = None,
) -> ForkResult:
    effective_max_turns = FORK_MAX_TURNS if max_turns is None else min(max_turns, FORK_MAX_TURNS)
    guard_message = _subagent_spawn_pressure_guard(runtime)
    if guard_message is not None:
        output_tokens = estimate_message_tokens([HumanMessage(content=guard_message)])
        tool_pool_identity = _tool_surface_snapshot(_runtime_visible_tool_projection(runtime))
        return ForkResult(
            content=guard_message,
            fork_run_id="blocked",
            parent_thread_id=_runtime_thread_id(runtime),
            child_thread_id=_runtime_thread_id(runtime),
            rendered_prompt_fingerprint=_fingerprint_text(
                _runtime_rendered_system_prompt(runtime)
            ),
            tool_pool_identity=tool_pool_identity,
            placeholder_layout=_fork_placeholder_layout(_fork_source_messages(runtime)),
            output_tokens=output_tokens,
            total_tokens=output_tokens,
        )

    active_run_id = run_id or uuid.uuid4().hex[:12]
    projection = _runtime_visible_tool_projection(runtime)
    tool_pool_identity = _tool_surface_snapshot(projection)
    rendered_system_prompt = _runtime_rendered_system_prompt(runtime)
    prompt_fingerprint = _fingerprint_text(rendered_system_prompt)
    normalized_source_messages = _normalize_fork_source_messages(
        _fork_source_messages(runtime)
    )
    placeholder_layout = _fork_placeholder_layout(normalized_source_messages)
    started_at = time.perf_counter()
    execution = _execute_fork_subagent(
        intent=intent,
        runtime=runtime,
        max_turns=effective_max_turns,
        run_id=active_run_id,
    )
    content = str(execution["content"])
    raw_result = execution["raw_result"]
    invocation = cast(RuntimeInvocation, execution["invocation"])
    _record_sidechain_messages(
        runtime=runtime,
        agent_type="fork",
        child_invocation=invocation,
        task=_fork_directive(intent),
        raw_result=raw_result,
        metadata=_fork_resume_metadata(
            runtime=runtime,
            run_id=active_run_id,
            requested_max_turns=max_turns,
            effective_max_turns=effective_max_turns,
            tool_pool_identity=tool_pool_identity,
            prompt_fingerprint=prompt_fingerprint,
            placeholder_layout=placeholder_layout,
        ),
    )
    _enqueue_agent_private_memory(
        invocation=invocation,
        source="fork",
        task=intent,
        content=content,
    )
    duration_ms = max(0, int((time.perf_counter() - started_at) * 1000))
    metrics = _result_metrics(
        task=intent,
        content=content,
        raw_result=raw_result,
        duration_ms=duration_ms,
    )
    child_thread_id = str(
        invocation.config.get("configurable", {}).get(
            "thread_id", invocation.context.session_id
        )
    )
    return ForkResult(
        content=content,
        fork_run_id=active_run_id,
        parent_thread_id=_runtime_thread_id(runtime),
        child_thread_id=child_thread_id,
        rendered_prompt_fingerprint=prompt_fingerprint,
        tool_pool_identity=tool_pool_identity,
        placeholder_layout=placeholder_layout,
        input_tokens=metrics["input_tokens"],
        output_tokens=metrics["output_tokens"],
        total_tokens=metrics["total_tokens"],
        total_duration_ms=metrics["total_duration_ms"],
        total_tool_use_count=metrics["total_tool_use_count"],
    )


def _subagent_spawn_pressure_guard(runtime: ToolRuntime | None) -> str | None:
    if runtime is None:
        return None
    context = getattr(runtime, "context", None)
    if not isinstance(context, RuntimeContext):
        return None
    context_window = context.model_context_window_tokens
    guard_ratio = context.subagent_spawn_guard_ratio
    if context_window is None or guard_ratio is None or context_window < 1:
        return None
    state = getattr(runtime, "state", None)
    if not isinstance(state, dict):
        return None
    messages = state.get("messages")
    if not isinstance(messages, list) or not all(
        isinstance(message, BaseMessage) for message in messages
    ):
        return None
    estimated_tokens = estimate_message_tokens(messages)
    ratio = estimated_tokens / context_window
    if ratio < guard_ratio:
        return None
    ratio_percent = int(ratio * 100)
    guard_percent = int(guard_ratio * 100)
    message = (
        "Subagent spawn blocked: current context pressure is "
        f"{ratio_percent}% of the configured model window, above the "
        f"{guard_percent}% guard threshold. Collapse or compact context first."
    )
    event = RuntimeEvent(
        kind="subagent_spawn_guard",
        message=message,
        session_id=context.session_id,
        metadata={
            "source": "runtime_pressure",
            "strategy": "spawn_guard",
            "estimated_token_count": estimated_tokens,
            "context_window_tokens": context_window,
            "estimated_token_ratio_percent": ratio_percent,
            "trigger": "pressure_ratio",
        },
    )
    context.event_sink.emit(event)
    append_runtime_event_evidence(context=context, event=event)
    return message


@tool(
    "run_subagent",
    args_schema=RunSubagentInput,
    description="Run a minimal synchronous stateless local subagent with a fixed child-tool allowlist.",
)
def run_subagent(
    task: str,
    runtime: ToolRuntime,
    agent_type: SubagentType = "general",
    plan_id: str | None = None,
    max_turns: int = 25,
) -> str:
    """Run one bounded synchronous subagent task."""
    result = run_subagent_task(
        task=task,
        runtime=runtime,
        agent_type=agent_type,
        plan_id=plan_id,
        max_turns=max_turns,
    )
    if agent_type == "verifier":
        record_verifier_evidence(result=result, runtime=runtime)
        return VerifierSubagentResult(
            plan_id=result.plan_id or "",
            plan_title=result.plan_title or "",
            verification=result.verification or "",
            task_ids=list(result.task_ids),
            tool_allowlist=list(result.tool_allowlist),
            content=result.content,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            total_duration_ms=result.total_duration_ms,
            total_tool_use_count=result.total_tool_use_count,
        ).model_dump_json()
    return SubagentResultEnvelope(
        agent_type=result.agent_type,
        content=result.content,
        tool_allowlist=list(result.tool_allowlist),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
        total_duration_ms=result.total_duration_ms,
        total_tool_use_count=result.total_tool_use_count,
    ).model_dump_json()


@tool(
    "run_fork",
    args_schema=RunForkInput,
    description="Fork the current same-config conversation into a sibling branch with inherited prompt and visible tools.",
)
def run_fork(
    intent: str,
    runtime: ToolRuntime,
    background: bool = False,
    max_turns: int = 25,
) -> str:
    """Run one bounded same-config sibling fork."""
    if background:
        from coding_deepgent.subagents.background import BACKGROUND_SUBAGENT_MANAGER

        return BACKGROUND_SUBAGENT_MANAGER.start_fork(
            intent=intent,
            runtime=runtime,
            max_turns=max_turns,
        ).model_dump_json()
    result = run_fork_task(
        intent=intent,
        runtime=runtime,
        max_turns=max_turns,
    )
    return ForkResultEnvelope(
        content=result.content,
        fork_run_id=result.fork_run_id,
        parent_thread_id=result.parent_thread_id,
        child_thread_id=result.child_thread_id,
        rendered_prompt_fingerprint=result.rendered_prompt_fingerprint,
        tool_pool_identity=result.tool_pool_identity,
        placeholder_layout=result.placeholder_layout,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
        total_duration_ms=result.total_duration_ms,
        total_tool_use_count=result.total_tool_use_count,
    ).model_dump_json()
