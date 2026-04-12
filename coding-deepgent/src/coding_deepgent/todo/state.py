from __future__ import annotations

from typing import Any, Literal

from langchain.agents import AgentState
from typing_extensions import NotRequired, TypedDict


class TodoItemState(TypedDict):
    content: str
    status: Literal["pending", "in_progress", "completed"]
    activeForm: str


class PlanningState(AgentState):
    todos: NotRequired[list[TodoItemState]]
    rounds_since_update: NotRequired[int]


def default_session_state() -> dict[str, Any]:
    return {
        "todos": [],
        "rounds_since_update": 0,
    }
