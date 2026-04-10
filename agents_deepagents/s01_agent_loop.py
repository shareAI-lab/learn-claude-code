#!/usr/bin/env python3
# Deep Agents track: the framework-owned loop -- model, tool, result, repeat.
"""
s01_agent_loop.py - The Agent Loop with Deep Agents

The original ``agents/s01_agent_loop.py`` hand-writes every provider turn.  This
parallel version uses Deep Agents's ``create_agent``.  The important comparison:
Deep Agents now owns the repeated model -> tool -> tool-result loop, while this
harness still owns the user history, workspace tool, and CLI boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from .common import WORKDIR, bash, create_agent_runtime, extract_text, invoke_and_append
except ImportError:  # direct script execution: python agents_deepagents/s01_agent_loop.py
    from common import WORKDIR, bash, create_agent_runtime, extract_text, invoke_and_append

SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Use bash to inspect and change the workspace. Act first, then report clearly."
)
TOOLS = [bash]


@dataclass
class LoopState:
    # The visible harness state is still small: history and why the harness continues.
    messages: list[dict[str, Any]] = field(default_factory=list)
    turn_count: int = 1
    transition_reason: str | None = None


def build_agent():
    """Create the Deep Agents agent that owns the inner model/tool loop."""

    return create_agent_runtime(SYSTEM, TOOLS)


def agent_loop(state: LoopState) -> str:
    final_text = invoke_and_append(build_agent(), state.messages)
    state.turn_count += 1
    state.transition_reason = "langchain_agent_completed"
    return final_text


if __name__ == "__main__":
    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input("\033[36ms01-lc >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})
        state = LoopState(messages=history)
        try:
            final = agent_loop(state)
        except RuntimeError as exc:
            print(f"Error: {exc}")
            continue
        print(extract_text(final) or "(no response)")
        print()
