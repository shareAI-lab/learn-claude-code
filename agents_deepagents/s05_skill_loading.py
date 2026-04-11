#!/usr/bin/env python3
# Deep Agents track: on-demand knowledge -- discover light, load deep.
"""
s05_skill_loading.py - Skills with Deep Agents

The original chapter teaches progressive disclosure: keep a cheap skill catalog
visible, then read the full skill instructions only when they are relevant.
This version keeps that behavior but uses Deep Agents' native skills middleware
instead of a custom ``load_skill`` tool.
"""

from __future__ import annotations

from typing import Any

from langchain.tools import tool

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel

try:
    from .common import (
        WORKDIR,
        bash,
        build_openai_model,
        edit_file,
        extract_text,
        invoke_and_append,
        read_file_content,
        write_file,
    )
except ImportError:
    from common import (
        WORKDIR,
        bash,
        build_openai_model,
        edit_file,
        extract_text,
        invoke_and_append,
        read_file_content,
        write_file,
    )

SKILL_SOURCE = "/skills"
SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use the skills catalog when a task needs specialized instructions.
When a skill looks relevant, read its SKILL.md path before following it."""


def normalize_skill_path(path: str) -> str:
    """Map Deep Agents' virtual skill paths onto the local workspace."""

    if path.startswith("/skills/"):
        return path[1:]
    return path


@tool("read_file")
def read_file(path: str, limit: int | None = None) -> str:
    """Read normal workspace files and SkillsMiddleware virtual skill paths."""

    return read_file_content(normalize_skill_path(path), limit)


TOOLS = [bash, read_file, write_file, edit_file]


def build_agent(
    *,
    model: BaseChatModel | None = None,
    backend: FilesystemBackend | None = None,
    skill_sources: list[str] | None = None,
):
    """Build the agent with Deep Agents' skills middleware."""

    return create_agent(
        model=model or build_openai_model(),
        tools=TOOLS,
        system_prompt=SYSTEM,
        middleware=[
            SkillsMiddleware(
                backend=backend
                or FilesystemBackend(root_dir=WORKDIR, virtual_mode=True),
                sources=skill_sources or [SKILL_SOURCE],
            )
        ],
    )


def agent_loop(messages: list[dict[str, Any]]) -> str:
    return invoke_and_append(build_agent(), messages)


if __name__ == "__main__":
    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input("\033[36ms05-lc >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})
        try:
            final = agent_loop(history)
        except RuntimeError as exc:
            print(f"Error: {exc}")
            continue
        print(extract_text(final) or "(no response)")
        print()
