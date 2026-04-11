from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain.messages import ToolMessage
from pydantic import ValidationError
import pytest
from langgraph.types import Command

from coding_deepgent.middleware.planning import PlanContextMiddleware
from coding_deepgent.tools.planning import _write_plan_command, reminder_text, write_plan


def test_write_plan_updates_custom_state_via_command() -> None:
    command = _write_plan_command(
        [
            {"content": "Inspect repo", "status": "completed"},
            {"content": "Implement change", "status": "in_progress", "activeForm": "Implementing"},
        ],
        tool_call_id="call-1",
    )

    assert isinstance(command, Command)
    assert command.update["items"] == [
        {"content": "Inspect repo", "status": "completed"},
        {"content": "Implement change", "status": "in_progress", "activeForm": "Implementing"},
    ]
    assert command.update["rounds_since_update"] == 0
    assert isinstance(command.update["messages"][0], ToolMessage)


def test_write_plan_tool_call_schema_hides_injected_tool_call_id() -> None:
    schema = write_plan.tool_call_schema.model_json_schema()
    item_schema = schema["$defs"]["PlanItemInput"]

    assert schema["required"] == ["items"]
    assert "tool_call_id" not in schema["properties"]
    assert item_schema["required"] == ["content", "status"]
    assert item_schema["additionalProperties"] is False


def test_write_plan_rejects_mismatched_json_without_fallback() -> None:
    with pytest.raises(ValidationError):
        _write_plan_command([{}], tool_call_id="call-1")

    with pytest.raises(ValidationError):
        _write_plan_command([{"task": "Inspect repo", "status": "done"}], tool_call_id="call-1")

    with pytest.raises(ValueError, match="tool_call_id is required"):
        _write_plan_command([{"content": "Inspect repo", "status": "pending"}])


def test_plan_context_middleware_rejects_parallel_write_plan_calls() -> None:
    middleware = PlanContextMiddleware()

    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "write_plan",
                        "args": {"items": [{"content": "Inspect repo", "status": "in_progress"}]},
                        "id": "call_1",
                        "type": "tool_call",
                    },
                    {
                        "name": "write_plan",
                        "args": {"items": [{"content": "Summarize findings", "status": "pending"}]},
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
    assert all(getattr(message, "status", None) == "error" for message in update["messages"])
    assert "should never be called multiple times in parallel" in update["messages"][0].content


def test_plan_context_middleware_tracks_stale_rounds() -> None:
    middleware = PlanContextMiddleware()

    assert middleware.after_agent(
        {
            "messages": [],
            "items": [{"content": "Keep going", "status": "pending"}],
            "rounds_since_update": 2,
        },
        runtime=None,
    ) == {"rounds_since_update": 3}

    middleware._updated_this_turn = True
    assert middleware.after_agent(
        {
            "messages": [],
            "items": [{"content": "Keep going", "status": "pending"}],
            "rounds_since_update": 0,
        },
        runtime=None,
    ) is None


def test_plan_context_middleware_seeds_missing_defaults() -> None:
    middleware = PlanContextMiddleware()

    assert middleware.before_agent({"messages": []}, runtime=None) == {
        "items": [],
        "rounds_since_update": 0,
    }


def test_reminder_text_triggers_only_for_stale_plans() -> None:
    items = [{"content": "Keep going", "status": "pending"}]
    assert reminder_text(items, 2) is None
    assert reminder_text(items, 3) == "<reminder>Refresh your current plan before continuing.</reminder>"
