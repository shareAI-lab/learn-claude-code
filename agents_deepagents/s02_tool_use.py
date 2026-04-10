#!/usr/bin/env python3
# LangChain track: tool dispatch -- expanding what the agent can reach.
"""
s02_tool_use.py - Tool dispatch with LangChain

The original chapter adds read/write/edit tools without changing the agent loop.
Here the same lesson is even sharper: ``create_agent`` still owns the loop, and
this file only grows the callable tool surface passed into LangChain.
"""

from __future__ import annotations

from typing import Any

try:
    from .common import (
        WORKDIR,
        bash,
        create_agent_runtime,
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
        create_agent_runtime,
        edit_file,
        extract_text,
        invoke_and_append,
        read_file,
        write_file,
    )

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks. Act, don't explain."

# Read-only tools can safely run in parallel; mutating tools must be serialized.
CONCURRENCY_SAFE = {"read_file"}
CONCURRENCY_UNSAFE = {"write_file", "edit_file"}
TOOLS = [bash, read_file, write_file, edit_file]


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
    return create_agent_runtime(SYSTEM, TOOLS)


def agent_loop(messages: list[dict[str, Any]]) -> str:
    normalized = normalize_messages(messages)
    final_text = invoke_and_append(build_agent(), normalized)
    if normalized is not messages:
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
