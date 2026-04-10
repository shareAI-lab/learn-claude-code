#!/usr/bin/env python3
# LangChain track: the loop -- LangChain supplies message/tool objects, the harness still drives the turn boundary.
"""
s01_agent_loop.py - The Agent Loop with LangChain

This mirrors agents/s01_agent_loop.py without replacing it.  The teaching point
is the same minimal cycle:

    user message -> model -> tool call -> ToolMessage -> next model turn

LangChain now owns the provider adapter and tool-call message schema.  This file
keeps the loop itself visible with ChatOpenAI.bind_tools rather than jumping
straight to create_agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

try:  # Support both `python -m agents_langchain.s01_agent_loop` and direct script execution.
    from agents_langchain._common import WORKDIR, build_openai_chat_model, latest_text, run_bash
except ModuleNotFoundError:  # pragma: no cover - direct script fallback
    from _common import WORKDIR, build_openai_chat_model, latest_text, run_bash

SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Use bash to inspect and change the workspace. Act first, then report clearly."
)


@tool
def bash(command: str) -> str:
    """Run a shell command in the current workspace."""

    return run_bash(command)


TOOLS = [bash]


@dataclass
class LoopState:
    """The explicit loop state: messages, turn count, and why we continue."""

    messages: list[Any]
    turn_count: int = 1
    transition_reason: str | None = None


def execute_tool_calls(response: Any) -> list[ToolMessage]:
    """Convert LangChain AIMessage.tool_calls into ToolMessage observations."""

    results: list[ToolMessage] = []
    for call in getattr(response, "tool_calls", []) or []:
        if call.get("name") != "bash":
            output = f"Unknown tool: {call.get('name')}"
        else:
            command = str((call.get("args") or {}).get("command", ""))
            print(f"\033[33m$ {command}\033[0m")
            output = run_bash(command)
            print(output[:200])
        results.append(ToolMessage(content=output, tool_call_id=call["id"]))
    return results


def run_one_turn(state: LoopState, model_with_tools: Any) -> bool:
    response = model_with_tools.invoke([SystemMessage(content=SYSTEM), *state.messages])
    state.messages.append(response)

    tool_results = execute_tool_calls(response)
    if not tool_results:
        state.transition_reason = None
        return False

    state.messages.extend(tool_results)
    state.turn_count += 1
    state.transition_reason = "tool_result"
    return True


def agent_loop(state: LoopState) -> None:
    model_with_tools = build_openai_chat_model().bind_tools(TOOLS)
    while run_one_turn(state, model_with_tools):
        pass


if __name__ == "__main__":
    history: list[Any] = []
    while True:
        try:
            query = input("\033[36mlc-s01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append(HumanMessage(content=query))
        state = LoopState(messages=history)
        agent_loop(state)
        print(latest_text(history))
        print()
