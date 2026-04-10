#!/usr/bin/env python3
# Deep Agents track: planning -- keep session plan state outside the model's head.
"""
s03_todo_write.py - Session Planning with Deep Agents tools

This is the first chapter where custom state becomes natural. The session plan
belongs in explicit runtime state, not in the model's hidden chain-of-thought.
Middleware renders that state back into the prompt, and the todo tool updates it
through LangChain state updates.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage, ToolMessage
from langchain.tools import ToolRuntime
from langgraph.types import Command
from typing_extensions import NotRequired

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

PLAN_REMINDER_INTERVAL = 3
SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use the todo tool for multi-step work.
Keep exactly one step in_progress when a task has multiple steps.
Refresh the plan as work advances. Prefer tools over prose."""


@dataclass
class PlanItem:
    content: str
    status: str = "pending"
    active_form: str = ""


class PlanningState(AgentState):
    plan_items: NotRequired[list[dict[str, str]]]
    rounds_since_update: NotRequired[int]
    updated_this_turn: NotRequired[bool]


def normalize_plan_items(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    if len(items) > 12:
        raise ValueError("Keep the session plan short (max 12 items)")

    normalized: list[dict[str, str]] = []
    in_progress_count = 0
    for index, raw_item in enumerate(items):
        content = str(raw_item.get("content", "")).strip()
        status = str(raw_item.get("status", "pending")).lower()
        active_form = str(raw_item.get("activeForm", raw_item.get("active_form", ""))).strip()

        if not content:
            raise ValueError(f"Item {index}: content required")
        if status not in {"pending", "in_progress", "completed"}:
            raise ValueError(f"Item {index}: invalid status '{status}'")
        if status == "in_progress":
            in_progress_count += 1

        normalized.append({
            "content": content,
            "status": status,
            "active_form": active_form,
        })

    if in_progress_count > 1:
        raise ValueError("Only one plan item can be in_progress")

    return normalized


def render_plan_items(items: list[dict[str, str]]) -> str:
    if not items:
        return "No session plan yet."

    lines: list[str] = []
    for raw_item in items:
        item = PlanItem(**raw_item)
        marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[item.status]
        line = f"{marker} {item.content}"
        if item.status == "in_progress" and item.active_form:
            line += f" ({item.active_form})"
        lines.append(line)

    completed = sum(1 for item in items if item["status"] == "completed")
    lines.append(f"\n({completed}/{len(items)} completed)")
    return "\n".join(lines)


def reminder_text(items: list[dict[str, str]], rounds_since_update: int) -> str | None:
    if not items:
        return None
    if rounds_since_update < PLAN_REMINDER_INTERVAL:
        return None
    return "<reminder>Refresh your current plan before continuing.</reminder>"


def todo(items: list[dict[str, Any]], runtime: ToolRuntime[None, PlanningState]) -> Command:
    """Rewrite the current session plan for multi-step work."""

    normalized = normalize_plan_items(items)
    rendered = render_plan_items(normalized)
    return Command(
        update={
            "plan_items": normalized,
            "rounds_since_update": 0,
            "updated_this_turn": True,
            "messages": [
                ToolMessage(content=rendered, tool_call_id=runtime.tool_call_id)
            ],
        }
    )


TOOLS = [bash, read_file, write_file, edit_file, todo]


class PlanningMiddleware(AgentMiddleware[PlanningState]):
    """Render planning state into the prompt and track stale-plan rounds."""

    state_schema = PlanningState

    def before_agent(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        updates: dict[str, Any] = {}
        if "plan_items" not in state:
            updates["plan_items"] = []
        if "rounds_since_update" not in state:
            updates["rounds_since_update"] = 0
        if "updated_this_turn" not in state:
            updates["updated_this_turn"] = False
        return updates or None

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        plan_items = request.state.get("plan_items", [])
        rounds_since_update = request.state.get("rounds_since_update", 0)
        extra_blocks: list[dict[str, str]] = []

        if plan_items:
            extra_blocks.append(
                {
                    "type": "text",
                    "text": "Current session plan:\n" + render_plan_items(plan_items),
                }
            )
            reminder = reminder_text(plan_items, rounds_since_update)
            if reminder:
                extra_blocks.append({"type": "text", "text": reminder})

        if not extra_blocks:
            return handler(request)

        return handler(
            request.override(
                system_message=SystemMessage(
                    content=[*request.system_message.content_blocks, *extra_blocks]
                )
            )
        )

    def after_agent(self, state: PlanningState, runtime) -> dict[str, Any] | None:
        if state.get("updated_this_turn"):
            return {"updated_this_turn": False}
        if state.get("plan_items"):
            return {"rounds_since_update": state.get("rounds_since_update", 0) + 1}
        return None


SESSION_STATE: dict[str, Any] = {
    "plan_items": [],
    "rounds_since_update": 0,
    "updated_this_turn": False,
}


def build_agent():
    return create_agent(
        model=build_openai_model(),
        tools=TOOLS,
        system_prompt=SYSTEM,
        middleware=[PlanningMiddleware()],
    )


def agent_loop(messages: list[dict[str, Any]]) -> str:
    result = build_agent().invoke({"messages": list(messages), **SESSION_STATE})
    SESSION_STATE.update(
        {
            "plan_items": result.get("plan_items", []),
            "rounds_since_update": result.get("rounds_since_update", 0),
            "updated_this_turn": result.get("updated_this_turn", False),
        }
    )
    final_text = latest_assistant_text(result)
    if final_text:
        messages.append({"role": "assistant", "content": final_text})
    return final_text


if __name__ == "__main__":
    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input("\033[36ms03-lc >> \033[0m")
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
