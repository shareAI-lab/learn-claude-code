from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, cast

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool

from coding_deepgent.filesystem import glob_search, grep_search, read_file
from coding_deepgent.rendering import latest_assistant_text
from coding_deepgent.runtime import RuntimeContext, RuntimeInvocation
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
            "End with a concise verdict and the strongest evidence you found.",
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


def run_subagent_task(
    *,
    task: str,
    agent_type: SubagentType = "general",
    runtime: ToolRuntime | None = None,
    plan_id: str | None = None,
    child_agent_factory: ChildAgentFactory | None = None,
) -> SubagentResult:
    allowlist = child_tool_allowlist(agent_type)
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
        return VerifierSubagentResult(
            plan_id=result.plan_id or "",
            plan_title=result.plan_title or "",
            verification=result.verification or "",
            task_ids=list(result.task_ids),
            tool_allowlist=list(result.tool_allowlist),
            content=result.content,
        ).model_dump_json()
    return result.content
