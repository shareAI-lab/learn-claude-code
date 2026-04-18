from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, cast

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool

from coding_deepgent.compact.runtime_pressure import estimate_message_tokens
from coding_deepgent.filesystem import glob_search, grep_search, read_file
from coding_deepgent.rendering import latest_assistant_text
from coding_deepgent.runtime import RuntimeContext, RuntimeEvent, RuntimeInvocation
from coding_deepgent.sessions.evidence_events import append_runtime_event_evidence
from coding_deepgent.sessions.records import SessionContext
from coding_deepgent.sessions.store_jsonl import JsonlSessionStore
from coding_deepgent.settings import build_openai_model
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

DEFAULT_CHILD_TOOLS = ("read_file", "glob", "grep", "task_get", "task_list", "plan_get")
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

BUILTIN_AGENT_DEFINITIONS: dict[SubagentType, AgentDefinition] = {
    "general": AgentDefinition(
        agent_type="general",
        description="Read-only general-purpose research subagent.",
        when_to_use=(
            "Use for bounded codebase research, file inspection, and durable "
            "task/plan reads that do not modify workspace or state."
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
        tool_allowlist=DEFAULT_CHILD_TOOLS,
        disallowed_tools=FORBIDDEN_CHILD_TOOLS,
        max_turns=5,
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
    agent_type: SubagentType
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


ChildAgentFactory = Callable[[SubagentType, Sequence[str]], Callable[[str], str]]


def agent_definition(agent_type: SubagentType) -> AgentDefinition:
    return BUILTIN_AGENT_DEFINITIONS[agent_type]


def child_tool_allowlist(agent_type: SubagentType) -> tuple[str, ...]:
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


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


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


def _general_system_prompt(*, definition: AgentDefinition, context: RuntimeContext) -> str:
    allowed_tools = ", ".join(definition.tool_allowlist)
    return "\n\n".join(
        [
            (
                "You are a read-only general-purpose research subagent. Inspect "
                "the workspace and durable task/plan state, then return a concise "
                "answer to the parent agent."
            ),
            (
                "Do not modify files, tasks, plans, memory, or invoke nested "
                "subagents. If a task requires mutation, explain what the parent "
                "agent should do instead."
            ),
            f"Workspace: {context.workdir}",
            f"Allowed tools: {allowed_tools}",
        ]
    )


def _verifier_system_prompt(
    *, definition: AgentDefinition, context: RuntimeContext
) -> str:
    tool_allowlist = definition.tool_allowlist
    allowed_tools = ", ".join(tool_allowlist)
    return "\n\n".join(
        [
            (
                "You are a verification specialist. Your role is to verify the "
                "implementation against the plan and try to find breakage, not to "
                "confirm success quickly."
            ),
            (
                "You are strictly read-only. Do not modify files, tasks, plans, "
                "memory, or invoke nested subagents."
            ),
            (
                "Use only the available tools when they materially improve the "
                "verification result. Cite concrete evidence from commands or tool "
                "reads in your final answer."
            ),
            f"Workspace: {context.workdir}",
            f"Allowed tools: {allowed_tools}",
            (
                "End with a final line exactly `VERDICT: PASS`, `VERDICT: FAIL`, "
                "or `VERDICT: PARTIAL`."
            ),
        ]
    )


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
        config={
            "configurable": {
                "thread_id": f"{parent_thread_id}:{definition.agent_type}{suffix}"
            }
        },
    )


def _fork_runtime_invocation(
    *,
    runtime: ToolRuntime,
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
        config={"configurable": {"thread_id": f"{parent_thread_id}:fork:{run_id}"}},
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
    return [*source_messages, HumanMessage(content=_fork_directive(intent))]


def _execute_child_subagent(
    *,
    task: str,
    runtime: ToolRuntime,
    definition: AgentDefinition,
    run_id: str | None = None,
) -> dict[str, Any]:
    from coding_deepgent.agent_runtime_service import invoke_agent

    invocation = _child_runtime_invocation(
        runtime=runtime,
        definition=definition,
        run_id=run_id,
    )
    system_prompt = (
        _verifier_system_prompt(definition=definition, context=invocation.context)
        if definition.agent_type == "verifier"
        else _general_system_prompt(definition=definition, context=invocation.context)
    )
    agent = cast(
        Any,
        create_agent,
    )(
        model=build_openai_model(),
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
    for role, content in _sidechain_message_entries(raw_result):
        store.append_sidechain_message(
            session_context,
            agent_type=agent_type,
            role=role,
            content=content,
            subagent_thread_id=subagent_thread_id,
            parent_message_id=parent_message_id,
            parent_thread_id=parent_thread_id,
            metadata=metadata,
        )
    return True


def _sidechain_message_entries(raw_result: Any) -> list[tuple[str, str]]:
    messages = raw_result.get("messages", []) if isinstance(raw_result, dict) else []
    entries: list[tuple[str, str]] = []
    for message in messages:
        role = _sidechain_message_role(message)
        content = _sidechain_message_text(message)
        if role is None or not content:
            continue
        entries.append((role, content))
    return entries


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


def _execute_fork_subagent(
    *,
    intent: str,
    runtime: ToolRuntime,
    run_id: str,
) -> dict[str, Any]:
    from coding_deepgent.agent_runtime_service import invoke_agent

    projection = _runtime_visible_tool_projection(runtime)
    invocation = _fork_runtime_invocation(runtime=runtime, run_id=run_id)
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


def run_subagent_task(
    *,
    task: str,
    agent_type: SubagentType = "general",
    runtime: ToolRuntime | None = None,
    plan_id: str | None = None,
    max_turns: int | None = None,
    child_agent_factory: ChildAgentFactory | None = None,
) -> SubagentResult:
    definition = agent_definition(agent_type)
    allowlist = definition.tool_allowlist
    effective_max_turns = (
        definition.max_turns if max_turns is None else min(max_turns, definition.max_turns)
    )
    del effective_max_turns
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
                run_id=plan.id,
            )
            content = str(execution["content"])
            raw_result = execution["raw_result"]
            _record_sidechain_messages(
                runtime=runtime,
                agent_type=definition.agent_type,
                child_invocation=cast(RuntimeInvocation, execution["invocation"]),
                task=verifier_task,
                raw_result=raw_result,
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
        )
        content = str(execution["content"])
        raw_result = execution["raw_result"]
        _record_sidechain_messages(
            runtime=runtime,
            agent_type=definition.agent_type,
            child_invocation=cast(RuntimeInvocation, execution["invocation"]),
            task=task,
            raw_result=raw_result,
        )
        _enqueue_agent_private_memory(
            invocation=cast(RuntimeInvocation, execution["invocation"]),
            source="subagent_general",
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
) -> ForkResult:
    del max_turns
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

    run_id = uuid.uuid4().hex[:12]
    projection = _runtime_visible_tool_projection(runtime)
    tool_pool_identity = _tool_surface_snapshot(projection)
    rendered_system_prompt = _runtime_rendered_system_prompt(runtime)
    prompt_fingerprint = _fingerprint_text(rendered_system_prompt)
    placeholder_layout = _fork_placeholder_layout(_fork_source_messages(runtime))
    started_at = time.perf_counter()
    execution = _execute_fork_subagent(intent=intent, runtime=runtime, run_id=run_id)
    content = str(execution["content"])
    raw_result = execution["raw_result"]
    invocation = cast(RuntimeInvocation, execution["invocation"])
    _record_sidechain_messages(
        runtime=runtime,
        agent_type="fork",
        child_invocation=invocation,
        task=_fork_directive(intent),
        raw_result=raw_result,
        metadata={
            "fork_run_id": run_id,
            "tool_pool_fingerprint": tool_pool_identity.fingerprint,
            "placeholder_layout_version": placeholder_layout.version,
        },
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
        fork_run_id=run_id,
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
    max_turns: int = 25,
) -> str:
    """Run one bounded same-config sibling fork."""
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
