#!/usr/bin/env python3
# LangChain track: context isolation -- parent and child are separate LangChain agents with separate message state.
"""
s04_subagent.py - Subagents with LangChain

The parent gets a `task` tool.  When called, the tool creates a child LangChain
agent with fresh messages, lets it work with a smaller tool set, then returns
only a summary.  The filesystem is shared; message context is not.
"""

from __future__ import annotations

import re
from pathlib import Path
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

SYSTEM = f"You are a coding agent at {WORKDIR}. Use the task tool to delegate exploration or subtasks."
SUBAGENT_SYSTEM = f"You are a coding subagent at {WORKDIR}. Complete the given task, then summarize your findings."


class AgentTemplate:
    """Parse a markdown agent definition with simple YAML-like frontmatter."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.name = self.path.stem
        self.config: dict[str, str] = {}
        self.system_prompt = ""
        self._parse()

    def _parse(self) -> None:
        text = self.path.read_text()
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
        if not match:
            self.system_prompt = text
            return
        for line in match.group(1).splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                self.config[key.strip()] = value.strip()
        self.system_prompt = match.group(2).strip()
        self.name = self.config.get("name", self.name)


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
    """Write content to a workspace file."""

    return write_file_impl(path, content)


@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace one exact text occurrence in a workspace file."""

    return edit_file_impl(path, old_text, new_text)


CHILD_TOOLS = [bash, read_file, write_file, edit_file]


def run_subagent(prompt: str) -> str:
    """Run a child agent with fresh context and return only its final text."""

    child = create_agent(build_openai_chat_model(), tools=CHILD_TOOLS, system_prompt=SUBAGENT_SYSTEM)
    result = child.invoke({"messages": [{"role": "user", "content": prompt}]})
    return latest_text(result["messages"]) or "(no summary)"


@tool
def task(prompt: str, description: str = "subtask") -> str:
    """Spawn a subagent with fresh context; return only its short summary."""

    print(f"> task ({description}): {prompt[:80]}")
    return run_subagent(prompt)


PARENT_TOOLS = [*CHILD_TOOLS, task]


def build_parent_agent():
    return create_agent(build_openai_chat_model(), tools=PARENT_TOOLS, system_prompt=SYSTEM)


def invoke_agent(agent: Any, messages: list[Any], query: str) -> list[Any]:
    result = agent.invoke({"messages": [*messages, {"role": "user", "content": query}]})
    return list(result["messages"])


if __name__ == "__main__":
    parent = build_parent_agent()
    history: list[Any] = []
    while True:
        try:
            query = input("\033[36mlc-s04 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history = invoke_agent(parent, history, query)
        print(latest_text(history))
        print()
