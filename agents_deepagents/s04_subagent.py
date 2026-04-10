#!/usr/bin/env python3
# Deep Agents track: context isolation -- a child agent gets fresh messages.
"""
s04_subagent.py - Subagents with Deep Agents

A Deep Agents agent can be created inside a tool call.  The parent and child share
the filesystem tools, but the child receives fresh ``messages=[]`` and returns
only a summary.  That preserves the original context-isolation lesson.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from .common import (
        WORKDIR,
        bash,
        create_agent_runtime,
        edit_file,
        extract_text,
        invoke_and_append,
        latest_assistant_text,
        read_file,
        write_file,
    )
except ImportError:
    from common import (
        WORKDIR,
        bash,
        create_agent_runtime,
        edit_file,
        extract_text,
        invoke_and_append,
        latest_assistant_text,
        read_file,
        write_file,
    )

SYSTEM = f"You are a coding agent at {WORKDIR}. Use the task tool to delegate exploration or subtasks."
SUBAGENT_SYSTEM = f"You are a coding subagent at {WORKDIR}. Complete the given task, then summarize your findings."


class AgentTemplate:
    """Parse an agent definition from markdown frontmatter."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.name = self.path.stem
        self.config: dict[str, str] = {}
        self.system_prompt = ""
        self._parse()

    def _parse(self) -> None:
        text = self.path.read_text(encoding="utf-8")
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


CHILD_TOOLS = [bash, read_file, write_file, edit_file]


def run_subagent(prompt: str) -> str:
    """Run a child Deep Agents agent with fresh context and return a summary only."""

    child_messages = [{"role": "user", "content": prompt}]
    child_agent = create_agent_runtime(SUBAGENT_SYSTEM, CHILD_TOOLS)
    result = child_agent.invoke({"messages": child_messages})
    return latest_assistant_text(result) or "(no summary)"


def task(prompt: str, description: str = "subtask") -> str:
    """Spawn a subagent with fresh context and return its short summary."""

    return run_subagent(f"Task: {description}\n\n{prompt}")


PARENT_TOOLS = CHILD_TOOLS + [task]


def build_agent():
    return create_agent_runtime(SYSTEM, PARENT_TOOLS)


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
