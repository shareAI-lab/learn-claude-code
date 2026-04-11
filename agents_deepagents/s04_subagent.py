#!/usr/bin/env python3
# Deep Agents track: context isolation -- a child agent gets fresh messages.
"""
s04_subagent.py - Subagents with Deep Agents

This chapter keeps the original lesson -- delegate a context-heavy side task and
return only a short summary -- but now uses Deep Agents' native task/subagent
middleware instead of a handwritten nested agent loop.

Mapping bridge from the original tutorial:
- original `run_subagent(prompt)` -> Deep Agents `task(description, subagent_type)`
- original local `sub_messages = [...]` -> middleware-managed fresh message context
- original summary string -> child final message returned as the parent `ToolMessage`

This file intentionally does not define `task`, `run_subagent`, `PARENT_TOOLS`,
or `CHILD_TOOLS`; `SubAgentMiddleware` injects `task`, and the `SubAgent` spec
controls the child's non-recursive tool surface.
"""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict

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

# Base tools shared by the parent and explicitly granted to the child.
# `task` is injected only into the parent by SubAgentMiddleware; leaving it out
# here preserves the original s04 no-recursive-spawn child tool boundary.
TOOLS = [bash, read_file, write_file, edit_file]


class TaskActivity(TypedDict):
    description: str
    subagent_type: str
    summary: str


def _task_calls_from_message(message: Any) -> list[tuple[str, str, str]]:
    """Return task-call metadata from one AI message.

    This keeps the extractor focused on task semantics instead of repeatedly
    branching over generic message attributes.
    """

    message_type = (
        str(message.get("type") or message.get("role") or "")
        if isinstance(message, dict)
        else str(getattr(message, "type", ""))
    )
    if message_type != "ai":
        return []

    tool_calls = (
        list(message.get("tool_calls") or [])
        if isinstance(message, dict)
        else list(getattr(message, "tool_calls", []) or [])
    )
    events: list[tuple[str, str, str]] = []
    for tool_call in tool_calls:
        if tool_call.get("name") != "task":
            continue
        args = tool_call.get("args") or {}
        events.append(
            (
                str(tool_call.get("id") or ""),
                str(args.get("description") or "").strip(),
                str(args.get("subagent_type") or "").strip(),
            )
        )
    return events


def _task_result_from_message(message: Any) -> tuple[str, str] | None:
    """Return the task tool-call id plus rendered summary from one tool message."""

    message_type = (
        str(message.get("type") or message.get("role") or "")
        if isinstance(message, dict)
        else str(getattr(message, "type", ""))
    )
    if message_type != "tool":
        return None

    tool_name = (
        str(message.get("name") or "")
        if isinstance(message, dict)
        else str(getattr(message, "name", ""))
    )
    if tool_name != "task":
        return None

    tool_call_id = (
        str(message.get("tool_call_id") or message.get("id") or "")
        if isinstance(message, dict)
        else str(getattr(message, "tool_call_id", "") or getattr(message, "id", ""))
    )
    content = message.get("content", "") if isinstance(message, dict) else getattr(message, "content", "")
    return tool_call_id, extract_text(content)


def extract_task_activity(result: dict[str, Any]) -> list[TaskActivity]:
    """Extract task/subagent events as structured data.

    This keeps UI concerns out of agent execution. The CLI can render these
    events for terminal visibility now, and future frontends can present the
    same structured activity differently without changing agent logic.
    """

    messages = result.get("messages") or []
    pending_calls: dict[str, dict[str, str]] = {}
    events: list[TaskActivity] = []

    for message in messages:
        task_calls = _task_calls_from_message(message)
        if task_calls:
            for tool_call_id, description, subagent_type in task_calls:
                pending_calls[tool_call_id] = {
                    "description": description,
                    "subagent_type": subagent_type,
                }
            continue

        task_result = _task_result_from_message(message)
        if task_result is None:
            continue

        tool_call_id, summary = task_result
        event_data = pending_calls.get(tool_call_id, {})
        events.append(
            {
                "description": event_data.get("description", ""),
                "subagent_type": event_data.get("subagent_type", ""),
                "summary": summary,
            }
        )

    return events


def render_task_activity(events: list[TaskActivity]) -> list[str]:
    """Render structured task activity for the terminal UI.

    The terminal is only one presentation layer over task activity. Future UIs
    can reuse ``extract_task_activity`` and replace this renderer.
    """

    lines: list[str] = []
    for event in events:
        subtype = f" ({event['subagent_type']})" if event["subagent_type"] else ""
        description = event["description"] or "delegated subtask"
        summary = event["summary"] or "(no summary)"
        lines.append(f"> task{subtype}: {description}")
        lines.append(f"  {summary}")
    return lines


def build_subagents(
    model: BaseChatModel,
) -> list[SubAgent]:
    """Return the stage's available subagent specs.

    The spec is the Deep Agents replacement for the original CHILD_TOOLS and
    SUBAGENT_SYSTEM bundle. The child receives these tools and a fresh message
    context internally; this is message-context isolation, not total process or
    arbitrary runtime-state isolation.
    """

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
    """Build the parent agent with Deep Agents' native task tool.

    SubAgentMiddleware maps the original parent `task(prompt)` idea to the
    framework-managed `task(description, subagent_type)` tool and returns the
    child final message as a parent-visible ToolMessage.
    """

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


def run_turn(messages: list[dict[str, Any]]) -> tuple[str, list[TaskActivity]]:
    result = build_agent().invoke({"messages": messages})
    final_text = latest_assistant_text(result)
    if final_text:
        messages.append({"role": "assistant", "content": final_text})
    return final_text, extract_task_activity(result)


def agent_loop(messages: list[dict[str, Any]]) -> str:
    final_text, _ = run_turn(messages)
    return final_text


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
            final, events = run_turn(history)
        except RuntimeError as exc:
            print(f"Error: {exc}")
            continue
        for line in render_task_activity(events):
            print(line)
        print(extract_text(final) or "(no response)")
        print()
