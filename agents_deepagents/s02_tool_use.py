#!/usr/bin/env python3
# Deep Agents track: tool dispatch -- expanding what the agent can reach.
"""
s02_tool_use.py - Tool dispatch with Deep Agents

The original chapter adds read/write/edit tools without changing the visible
harness. This stage keeps the same lesson: the runtime owns the inner
model -> tool -> result loop, while the chapter wrapper stays thin and the tool
surface is unchanged.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage

try:
    from .common import (
        WORKDIR,
        bash,
        build_openai_model,
        edit_file,
        extract_text,
        latest_assistant_text,
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
        latest_assistant_text,
        read_file,
        write_file,
    )

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks. Act, don't explain."

# Read-only tools can safely run in parallel; mutating tools must be serialized.
CONCURRENCY_SAFE = {"read_file"}
CONCURRENCY_UNSAFE = {"write_file", "edit_file"}
TOOLS = [bash, read_file, write_file, edit_file]


class ToolUseMiddleware(AgentMiddleware):
    """Keep the s02 lesson explicit without adding chapter-specific state."""

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        new_content = list(request.system_message.content_blocks) + [
            {
                "type": "text",
                "text": (
                    "Stage s02: the runtime owns the repeated model-tool loop. "
                    "This chapter only expands the available tool surface. "
                    f"Visible merged history count: {len(request.messages)}."
                ),
            }
        ]
        return handler(
            request.override(system_message=SystemMessage(content=new_content))
        )


def normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only provider-facing message fields and merge consecutive roles."""

    cleaned: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        cleaned.append({"role": role, "content": content})

    if not cleaned:
        return cleaned

    merged = [cleaned[0]]
    for message in cleaned[1:]:
        if message["role"] == merged[-1]["role"]:
            merged[-1]["content"] = f"{merged[-1]['content']}\n\n{message['content']}"
        else:
            merged.append(message)
    return merged


def build_agent():
    return create_agent(
        model=build_openai_model(),
        tools=TOOLS,
        system_prompt=SYSTEM,
        middleware=[ToolUseMiddleware()],
    )


def agent_loop(messages: list[dict[str, Any]]) -> str:
    normalized = normalize_messages(messages)
    result = build_agent().invoke({"messages": normalized})
    final_text = latest_assistant_text(result)
    if final_text:
        messages.append({"role": "assistant", "content": final_text})
    return final_text


if __name__ == "__main__":
    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input("\033[36ms02-lc >> \033[0m")
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
