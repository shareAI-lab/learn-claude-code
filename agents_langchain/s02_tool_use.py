#!/usr/bin/env python3
# LangChain track: tool dispatch -- adding tools grows the dispatch surface, not the user's CLI contract.
"""
s02_tool_use.py - Tool dispatch with LangChain

LangChain's create_agent owns the repeated model/tool loop here.  The harness
still owns the concrete tool implementations, path safety, and output limits.
"""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool

try:
    from agents_langchain._common import (
        WORKDIR,
        build_openai_chat_model,
        edit_file as edit_file_impl,
        latest_text,
        read_file as read_file_impl,
        run_bash,
        write_file as write_file_impl,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script fallback
    from _common import (
        WORKDIR,
        build_openai_chat_model,
        edit_file as edit_file_impl,
        latest_text,
        read_file as read_file_impl,
        run_bash,
        write_file as write_file_impl,
    )

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks. Act, don't explain."


@tool
def bash(command: str) -> str:
    """Run a shell command in the current workspace."""

    return run_bash(command)


@tool
def read_file(path: str, limit: int | None = None) -> str:
    """Read file contents from the workspace, optionally limiting lines."""

    return read_file_impl(path, limit)


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a workspace file, creating parents when needed."""

    return write_file_impl(path, content)


@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace one exact text occurrence in a workspace file."""

    return edit_file_impl(path, old_text, new_text)


TOOLS = [bash, read_file, write_file, edit_file]

# Read-only tools can safely run in parallel; mutating tools should serialize.
CONCURRENCY_SAFE = {"read_file"}
CONCURRENCY_UNSAFE = {"write_file", "edit_file"}


def build_agent():
    return create_agent(build_openai_chat_model(), tools=TOOLS, system_prompt=SYSTEM)


def invoke_agent(agent: Any, messages: list[Any], query: str) -> list[Any]:
    result = agent.invoke({"messages": [*messages, {"role": "user", "content": query}]})
    return list(result["messages"])


if __name__ == "__main__":
    agent = build_agent()
    history: list[Any] = []
    while True:
        try:
            query = input("\033[36mlc-s02 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history = invoke_agent(agent, history, query)
        print(latest_text(history))
        print()
