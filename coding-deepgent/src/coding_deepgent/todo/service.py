from __future__ import annotations

from collections.abc import Mapping, Sequence

from langchain.messages import ToolMessage
from langgraph.types import Command

from coding_deepgent.todo.renderers import render_plan_items
from coding_deepgent.todo.schemas import TodoItemInput, TodoWriteInput
from coding_deepgent.todo.state import TodoItemState


def normalize_todos(
    todos: Sequence[TodoItemInput | Mapping[str, object]],
) -> list[TodoItemState]:
    if len(todos) > 12:
        raise ValueError("Keep the todo list short (max 12 todos)")

    validated = TodoWriteInput.model_validate({"todos": list(todos)})

    normalized: list[TodoItemState] = []
    in_progress_count = 0
    for todo_input in validated.todos:
        if todo_input.status == "in_progress":
            in_progress_count += 1

        normalized.append(
            {
                "content": todo_input.content,
                "status": todo_input.status,
                "activeForm": todo_input.activeForm,
            }
        )

    if in_progress_count > 1:
        raise ValueError("Only one todo item can be in_progress")

    return normalized


def build_todo_update(
    todos: Sequence[TodoItemInput | Mapping[str, object]],
    *,
    tool_call_id: str | None = None,
) -> Command:
    if tool_call_id is None:
        raise ValueError("tool_call_id is required for TodoWrite tool execution")

    normalized = normalize_todos(todos)
    rendered = render_plan_items(normalized)
    return Command(
        update={
            "todos": normalized,
            "rounds_since_update": 0,
            "messages": [ToolMessage(content=rendered, tool_call_id=tool_call_id)],
        }
    )
