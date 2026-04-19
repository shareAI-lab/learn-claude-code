from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from coding_deepgent.subagents.schemas import ForkPlaceholderLayout, ToolPoolIdentitySnapshot


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
