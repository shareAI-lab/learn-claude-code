from __future__ import annotations

from typing import cast

from langchain_core.messages import AIMessage
from langchain.messages import ToolMessage
from pydantic import BaseModel, ValidationError
import pytest
from langgraph.types import Command

from coding_deepgent.middleware.planning import PlanContextMiddleware
from coding_deepgent.todo.state import PlanningState, TodoItemState
from coding_deepgent.tools.planning import (
    _todo_write_command,
    reminder_text,
    todo_write,
)


def test_todowrite_updates_custom_state_via_command() -> None:
    command = _todo_write_command(
        [
            {
                "content": "Inspect repo",
                "status": "completed",
                "activeForm": "Inspecting",
            },
            {
                "content": "Implement change",
                "status": "in_progress",
                "activeForm": "Implementing",
            },
        ],
        tool_call_id="call-1",
    )

    assert isinstance(command, Command)
    command_update = command.update
    assert command_update is not None
    assert command_update["todos"] == [
        {"content": "Inspect repo", "status": "completed", "activeForm": "Inspecting"},
        {
            "content": "Implement change",
            "status": "in_progress",
            "activeForm": "Implementing",
        },
    ]
    assert command_update["rounds_since_update"] == 0
    assert isinstance(command_update["messages"][0], ToolMessage)


def test_todowrite_tool_call_schema_hides_injected_tool_call_id() -> None:
    tool_call_schema = cast(type[BaseModel], todo_write.tool_call_schema)
    schema = tool_call_schema.model_json_schema()
    item_schema = schema["$defs"]["TodoItemInput"]

    assert getattr(todo_write, "name", None) == "TodoWrite"
    assert schema["required"] == ["todos"]
    assert "items" not in schema["properties"]
    assert "tool_call_id" not in schema["properties"]
    assert item_schema["required"] == ["content", "status", "activeForm"]
    assert item_schema["additionalProperties"] is False


def test_todowrite_rejects_mismatched_json_without_fallback() -> None:
    with pytest.raises(ValidationError):
        _todo_write_command([{}], tool_call_id="call-1")

    with pytest.raises(ValidationError):
        _todo_write_command(
            [{"task": "Inspect repo", "status": "done", "activeForm": "Inspecting"}],
            tool_call_id="call-1",
        )

    with pytest.raises(ValueError, match="tool_call_id is required"):
        _todo_write_command(
            [
                {
                    "content": "Inspect repo",
                    "status": "pending",
                    "activeForm": "Inspecting",
                }
            ]
        )


def test_todowrite_requires_active_form_for_every_item() -> None:
    with pytest.raises(ValidationError):
        _todo_write_command(
            [{"content": "Inspect repo", "status": "pending"}], tool_call_id="call-1"
        )

    with pytest.raises(ValidationError):
        _todo_write_command(
            [{"content": "Inspect repo", "status": "pending", "activeForm": "   "}],
            tool_call_id="call-1",
        )


def test_plan_context_middleware_rejects_parallel_todowrite_calls() -> None:
    middleware = PlanContextMiddleware()

    state: PlanningState = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "TodoWrite",
                        "args": {
                            "todos": [
                                {
                                    "content": "Inspect repo",
                                    "status": "in_progress",
                                    "activeForm": "Inspecting",
                                }
                            ]
                        },
                        "id": "call_1",
                        "type": "tool_call",
                    },
                    {
                        "name": "TodoWrite",
                        "args": {
                            "todos": [
                                {
                                    "content": "Summarize findings",
                                    "status": "pending",
                                    "activeForm": "Summarizing",
                                }
                            ]
                        },
                        "id": "call_2",
                        "type": "tool_call",
                    },
                ],
            )
        ]
    }

    update = middleware.after_model(state, runtime=None)

    assert update is not None
    assert len(update["messages"]) == 2
    assert all(isinstance(message, ToolMessage) for message in update["messages"])
    assert all(
        getattr(message, "status", None) == "error" for message in update["messages"]
    )
    assert (
        "should never be called multiple times in parallel"
        in update["messages"][0].content
    )


def test_plan_context_middleware_tracks_stale_rounds() -> None:
    middleware = PlanContextMiddleware()

    assert middleware.after_agent(
        {
            "messages": [],
            "todos": [
                {"content": "Keep going", "status": "pending", "activeForm": "Keeping"}
            ],
            "rounds_since_update": 2,
        },
        runtime=None,
    ) == {"rounds_since_update": 3}

    middleware._updated_this_turn = True
    assert (
        middleware.after_agent(
            {
                "messages": [],
                "todos": [
                    {
                        "content": "Keep going",
                        "status": "pending",
                        "activeForm": "Keeping",
                    }
                ],
                "rounds_since_update": 0,
            },
            runtime=None,
        )
        is None
    )


def test_plan_context_middleware_seeds_missing_defaults() -> None:
    middleware = PlanContextMiddleware()

    assert middleware.before_agent({"messages": []}, runtime=None) == {
        "todos": [],
        "rounds_since_update": 0,
    }


def test_reminder_text_triggers_only_for_stale_plans() -> None:
    todos: list[TodoItemState] = [
        {"content": "Keep going", "status": "pending", "activeForm": "Keeping"}
    ]
    assert reminder_text(todos, 2) is None
    assert (
        reminder_text(todos, 3)
        == "<reminder>Refresh your current plan before continuing.</reminder>"
    )
