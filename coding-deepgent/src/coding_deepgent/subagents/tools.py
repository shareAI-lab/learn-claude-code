from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from langchain.tools import ToolRuntime, tool

from coding_deepgent.subagents.schemas import (
    RunSubagentInput,
    SubagentType,
    VerifierSubagentResult,
)
from coding_deepgent.tasks.store import get_plan

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


def _verifier_task_prompt(*, task: str, plan_id: str, plan_title: str, content: str, verification: str, task_ids: Sequence[str]) -> str:
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
            content = f"Verifier subagent accepted task synchronously: {plan.title}"
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
