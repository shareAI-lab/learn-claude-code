from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, cast

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import BaseMessage
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
    RunSubagentInput,
    SubagentType,
    VerifierSubagentResult,
)
from coding_deepgent.tasks import plan_get, task_get, task_list
from coding_deepgent.tasks.store import get_plan
from coding_deepgent.tool_system import ToolCapability, ToolGuardMiddleware, build_capability_registry

DEFAULT_CHILD_TOOLS = ("read_file", "glob", "grep")
VERIFIER_EXTRA_TOOLS = ("task_get", "task_list", "plan_get")
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
        exposure="child_only",
        tags=("read", "workspace"),
    )


@dataclass(frozen=True, slots=True)
class SubagentResult:
    content: str
    agent_type: SubagentType
    tool_allowlist: tuple[str, ...]
    plan_id: str | None = None
    plan_title: str | None = None
    verification: str | None = None
    task_ids: tuple[str, ...] = ()


ChildAgentFactory = Callable[[SubagentType, Sequence[str]], Callable[[str], str]]


def child_tool_allowlist(agent_type: SubagentType) -> tuple[str, ...]:
    if agent_type == "verifier":
        return (*DEFAULT_CHILD_TOOLS, *VERIFIER_EXTRA_TOOLS)
    return DEFAULT_CHILD_TOOLS


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


def _verifier_system_prompt(*, tool_allowlist: Sequence[str], context: RuntimeContext) -> str:
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


def _verifier_runtime_invocation(
    *,
    runtime: ToolRuntime,
    plan_id: str,
) -> RuntimeInvocation:
    context = getattr(runtime, "context", None)
    if not isinstance(context, RuntimeContext):
        raise RuntimeError("Verifier subagent requires runtime context")
    parent_config = getattr(runtime, "config", None)
    parent_thread_id = context.session_id
    if isinstance(parent_config, dict):
        configurable = parent_config.get("configurable", {})
        if isinstance(configurable, dict):
            parent_thread_id = str(configurable.get("thread_id", parent_thread_id))
    return RuntimeInvocation(
        context=replace(
            context,
            agent_name=f"{context.agent_name}-verifier",
            entrypoint="run_subagent:verifier",
        ),
        config={"configurable": {"thread_id": f"{parent_thread_id}:verifier:{plan_id}"}},
    )


def _verifier_tools(tool_allowlist: Sequence[str]) -> list[BaseTool]:
    return [CHILD_TOOL_OBJECTS[name] for name in tool_allowlist]


def _verifier_middleware(tool_allowlist: Sequence[str]) -> list[ToolGuardMiddleware]:
    registry = build_capability_registry(
        builtin_capabilities=tuple(
            _child_tool_capability(name) for name in tool_allowlist
        ),
        extension_capabilities=(),
    )
    return [ToolGuardMiddleware(registry=registry)]


def _execute_verifier_subagent(
    *,
    task: str,
    runtime: ToolRuntime,
    plan_id: str,
    tool_allowlist: Sequence[str],
) -> str:
    from coding_deepgent.agent_runtime_service import invoke_agent

    invocation = _verifier_runtime_invocation(runtime=runtime, plan_id=plan_id)
    agent = cast(
        Any,
        create_agent,
    )(
        model=build_openai_model(),
        tools=_verifier_tools(tool_allowlist),
        system_prompt=_verifier_system_prompt(
            tool_allowlist=tool_allowlist,
            context=invocation.context,
        ),
        middleware=_verifier_middleware(tool_allowlist),
        context_schema=RuntimeContext,
        store=runtime.store,
        name=invocation.context.agent_name,
    )
    result = invoke_agent(
        agent,
        {"messages": [{"role": "user", "content": task}]},
        invocation,
    )
    content = latest_assistant_text(result).strip()
    if not content:
        raise RuntimeError("Verifier subagent returned no assistant content")
    return content


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


def run_subagent_task(
    *,
    task: str,
    agent_type: SubagentType = "general",
    runtime: ToolRuntime | None = None,
    plan_id: str | None = None,
    child_agent_factory: ChildAgentFactory | None = None,
) -> SubagentResult:
    allowlist = child_tool_allowlist(agent_type)
    guard_message = _subagent_spawn_pressure_guard(runtime)
    if guard_message is not None:
        return SubagentResult(
            content=guard_message,
            agent_type=agent_type,
            tool_allowlist=allowlist,
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
        if child_agent_factory is None:
            content = _execute_verifier_subagent(
                task=verifier_task,
                runtime=runtime,
                plan_id=plan.id,
                tool_allowlist=allowlist,
            )
        else:
            content = child_agent_factory(agent_type, allowlist)(verifier_task)
        return SubagentResult(
            content=content,
            agent_type=agent_type,
            tool_allowlist=allowlist,
            plan_id=plan.id,
            plan_title=plan.title,
            verification=plan.verification,
            task_ids=tuple(plan.task_ids),
        )
    if child_agent_factory is None:
        content = f"Subagent {agent_type} accepted task synchronously: {task}"
    else:
        content = child_agent_factory(agent_type, allowlist)(task)
    return SubagentResult(
        content=content, agent_type=agent_type, tool_allowlist=allowlist
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
    max_turns: int = 1,
) -> str:
    """Run one bounded synchronous subagent task."""
    del max_turns
    result = run_subagent_task(
        task=task,
        runtime=runtime,
        agent_type=agent_type,
        plan_id=plan_id,
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
        ).model_dump_json()
    return result.content
