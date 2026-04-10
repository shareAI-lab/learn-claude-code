#!/usr/bin/env python3
"""Deep Agents staging spike for the s01-s06 teaching track.

`deepagents.create_deep_agent()` eagerly installs planning, filesystem,
subagent, and summarization middleware. That default stack is convenient for a
fully-loaded coding harness, but it is too permissive for this repository's
chapter-by-chapter tutorial: `s01` must not expose planning yet, and `s03`
must still block subagents.

This module proves the gating requirement is technically viable by composing the
Deep Agents middleware stack directly with `langchain.agents.create_agent()`.
Each stage only receives the middleware that should be visible at that chapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Sequence

from deepagents.backends import StateBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.skills import SkillsMiddleware
from deepagents.middleware.subagents import CompiledSubAgent, SubAgent, SubAgentMiddleware
from deepagents.middleware.summarization import (
    create_summarization_middleware,
    create_summarization_tool_middleware,
)
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.middleware.types import AgentMiddleware
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

StageName = Literal["s01", "s02", "s03", "s04", "s05", "s06"]


@dataclass(frozen=True)
class StageCapabilities:
    planning: bool = False
    subagents: bool = False
    skills: bool = False
    compaction: bool = False


STAGE_CAPABILITIES: dict[StageName, StageCapabilities] = {
    "s01": StageCapabilities(),
    "s02": StageCapabilities(),
    "s03": StageCapabilities(planning=True),
    "s04": StageCapabilities(planning=True, subagents=True),
    "s05": StageCapabilities(planning=True, subagents=True, skills=True),
    "s06": StageCapabilities(planning=True, subagents=True, skills=True, compaction=True),
}

SubagentSpec = SubAgent | CompiledSubAgent


def capabilities_for_stage(stage: StageName) -> StageCapabilities:
    try:
        return STAGE_CAPABILITIES[stage]
    except KeyError as exc:  # pragma: no cover - defensive guard
        expected = ", ".join(STAGE_CAPABILITIES)
        raise ValueError(f"Unsupported stage '{stage}'. Expected one of: {expected}") from exc


def _resolve_model(model: str | BaseChatModel) -> BaseChatModel:
    return init_chat_model(model) if isinstance(model, str) else model


def _validate_stage_inputs(
    stage: StageName,
    capabilities: StageCapabilities,
    *,
    subagents: Sequence[SubagentSpec] | None,
    skill_sources: Sequence[str] | None,
) -> None:
    if capabilities.subagents and not subagents:
        raise ValueError(f"{stage} requires at least one configured subagent")
    if capabilities.skills and not skill_sources:
        raise ValueError(f"{stage} requires at least one configured skill source")


def build_stage_middleware(
    stage: StageName,
    *,
    model: str | BaseChatModel,
    backend: Any = StateBackend,
    subagents: Sequence[SubagentSpec] | None = None,
    skill_sources: Sequence[str] | None = None,
    extra_middleware: Sequence[AgentMiddleware[Any, Any]] = (),
) -> list[AgentMiddleware[Any, Any]]:
    """Build the middleware stack for a staged Deep Agents chapter."""

    capabilities = capabilities_for_stage(stage)
    _validate_stage_inputs(stage, capabilities, subagents=subagents, skill_sources=skill_sources)

    resolved_model = _resolve_model(model) if capabilities.compaction else model

    middleware: list[AgentMiddleware[Any, Any]] = []
    if capabilities.planning:
        middleware.append(TodoListMiddleware())
    if capabilities.skills and skill_sources:
        middleware.append(SkillsMiddleware(backend=backend, sources=list(skill_sources)))

    middleware.append(FilesystemMiddleware(backend=backend))

    if capabilities.subagents and subagents:
        middleware.append(SubAgentMiddleware(backend=backend, subagents=list(subagents)))
    if capabilities.compaction:
        middleware.append(create_summarization_tool_middleware(resolved_model, backend))
        middleware.append(create_summarization_middleware(resolved_model, backend))

    middleware.append(PatchToolCallsMiddleware())
    middleware.extend(extra_middleware)
    return middleware


def build_stage_agent(
    stage: StageName,
    *,
    model: str | BaseChatModel,
    tools: Sequence[Any] | None = None,
    backend: Any = StateBackend,
    system_prompt: str | None = None,
    subagents: Sequence[SubagentSpec] | None = None,
    skill_sources: Sequence[str] | None = None,
    extra_middleware: Sequence[AgentMiddleware[Any, Any]] = (),
):
    """Create a stage-gated agent using Deep Agents middleware primitives."""

    capabilities = capabilities_for_stage(stage)
    resolved_model = _resolve_model(model) if capabilities.compaction else model

    return create_agent(
        resolved_model,
        tools=list(tools or []),
        system_prompt=system_prompt,
        middleware=build_stage_middleware(
            stage,
            model=resolved_model,
            backend=backend,
            subagents=subagents,
            skill_sources=skill_sources,
            extra_middleware=extra_middleware,
        ),
    )
