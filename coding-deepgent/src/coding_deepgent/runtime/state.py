from __future__ import annotations

from typing import Any, Literal

from langchain.agents import AgentState
from typing_extensions import NotRequired, TypedDict


class RuntimeTodoState(TypedDict):
    content: str
    status: Literal["pending", "in_progress", "completed"]
    activeForm: str


class RuntimeState(AgentState):
    todos: NotRequired[list[RuntimeTodoState]]
    rounds_since_update: NotRequired[int]
    session_memory: NotRequired[dict[str, Any]]


PlanningState = RuntimeState


def default_runtime_state() -> dict[str, Any]:
    return {
        "todos": [],
        "rounds_since_update": 0,
    }
