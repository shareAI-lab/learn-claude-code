from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from langchain.tools import ToolRuntime, tool

from coding_deepgent.subagents.schemas import RunSubagentInput, SubagentType

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


ChildAgentFactory = Callable[[SubagentType, Sequence[str]], Callable[[str], str]]


def child_tool_allowlist(agent_type: SubagentType) -> tuple[str, ...]:
    if agent_type == "verifier":
        return (*DEFAULT_CHILD_TOOLS, *VERIFIER_EXTRA_TOOLS)
    return DEFAULT_CHILD_TOOLS


def run_subagent_task(
    *,
    task: str,
    agent_type: SubagentType = "general",
    child_agent_factory: ChildAgentFactory | None = None,
) -> SubagentResult:
    allowlist = child_tool_allowlist(agent_type)
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
    max_turns: int = 1,
) -> str:
    """Run one bounded synchronous subagent task."""
    del runtime, max_turns
    result = run_subagent_task(task=task, agent_type=agent_type)
    return result.content
