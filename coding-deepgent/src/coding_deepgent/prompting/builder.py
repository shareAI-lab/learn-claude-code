from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from coding_deepgent.memory import MemoryRecord, render_memories
from coding_deepgent.rules import render_project_rules_for_prompt


@dataclass(frozen=True, slots=True)
class PromptContext:
    default_system_prompt: tuple[str, ...]
    user_context: Mapping[str, str] = field(default_factory=dict)
    system_context: Mapping[str, str] = field(default_factory=dict)
    append_system_prompt: str | None = None
    rules_context: str | None = None
    memory_context: str | None = None

    @property
    def system_prompt_parts(self) -> tuple[str, ...]:
        parts = [*self.default_system_prompt]
        if self.rules_context:
            parts.append(self.rules_context)
        if self.memory_context:
            parts.append(self.memory_context)
        if self.append_system_prompt:
            parts.append(self.append_system_prompt)
        return tuple(parts)

    @property
    def system_prompt(self) -> str:
        return "\n\n".join(self.system_prompt_parts)


def build_default_system_prompt(*, workdir: Path, agent_name: str) -> tuple[str, ...]:
    return (
        f"You are {agent_name}, an independent cumulative LangChain cc product agent.",
        f"Current workspace: {workdir}.",
        (
            "Use TodoWrite when explicit progress tracking helps on multi-step work; "
            "preserve exactly one in-progress todo and include activeForm for every todo."
        ),
        "Prefer LangChain-native tools and state updates over prose when an action is needed.",
    )


def build_prompt_context(
    *,
    workdir: Path,
    agent_name: str,
    session_id: str,
    entrypoint: str,
    custom_system_prompt: str | None = None,
    append_system_prompt: str | None = None,
    memories: Sequence[MemoryRecord] = (),
) -> PromptContext:
    default_prompt = (
        (custom_system_prompt,)
        if custom_system_prompt
        else build_default_system_prompt(workdir=workdir, agent_name=agent_name)
    )
    return PromptContext(
        default_system_prompt=default_prompt,
        user_context={"session_id": session_id},
        system_context={
            "workdir": str(workdir),
            "entrypoint": entrypoint,
            "agent_name": agent_name,
        },
        append_system_prompt=append_system_prompt,
        rules_context=render_project_rules_for_prompt(workdir),
        memory_context=render_memories(memories),
    )
