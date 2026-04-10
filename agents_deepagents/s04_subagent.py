#!/usr/bin/env python3
# Deep Agents track: context isolation -- a child agent gets fresh messages.
"""
s04_subagent.py - Subagents with Deep Agents

This chapter keeps the original lesson -- delegate a context-heavy side task and
return only a short summary -- but now uses Deep Agents' native task/subagent
middleware instead of a handwritten nested agent loop.
"""

from __future__ import annotations

from typing import Any

from deepagents.backends import StateBackend
from deepagents.middleware.subagents import SubAgent, SubAgentMiddleware
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
        read_file,
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
        read_file,
        write_file,
    )

SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Use the task tool when a subtask needs fresh context or would otherwise "
    "bloat the main thread."
)
SUBAGENT_SYSTEM = (
    f"You are a coding subagent at {WORKDIR}. "
    "Complete the delegated task autonomously, then return a concise summary "
    "of what you found or changed."
)
SUBAGENT_TYPE = "general-purpose"
SUBAGENT_DESCRIPTION = (
    "Fresh-context coding subagent for isolated exploration, editing, and "
    "verification tasks. Return only a short summary to the parent agent."
)

TOOLS = [bash, read_file, write_file, edit_file]


def build_subagents(
    model: BaseChatModel,
) -> list[SubAgent]:
    """Return the stage's available subagent specs."""

    return [
        {
            "name": SUBAGENT_TYPE,
            "description": SUBAGENT_DESCRIPTION,
            "system_prompt": SUBAGENT_SYSTEM,
            "model": model,
            "tools": TOOLS,
        }
    ]


def build_agent(
    *,
    model: BaseChatModel | None = None,
    subagent_model: BaseChatModel | None = None,
):
    """Build the parent agent with Deep Agents' native task tool."""

    main_model = model or build_openai_model()
    child_model = subagent_model or main_model
    return create_agent(
        model=main_model,
        tools=TOOLS,
        system_prompt=SYSTEM,
        middleware=[
            SubAgentMiddleware(
                backend=StateBackend,
                subagents=build_subagents(child_model),
            )
        ],
    )


def agent_loop(messages: list[dict[str, Any]]) -> str:
    return invoke_and_append(build_agent(), messages)


if __name__ == "__main__":
    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input("\033[36ms04-lc >> \033[0m")
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
