from __future__ import annotations

from types import SimpleNamespace

from langchain.messages import ToolMessage
from langgraph.types import Command

from coding_deepgent.middleware.planning import PlanningMiddleware
from coding_deepgent.tools.planning import reminder_text, todo


def test_todo_updates_custom_state_via_command() -> None:
    command = todo(
        [
            {"content": "Inspect repo", "status": "completed"},
            {"content": "Implement change", "status": "in_progress", "activeForm": "Implementing"},
        ],
        runtime=SimpleNamespace(tool_call_id="call-1"),
    )

    assert isinstance(command, Command)
    assert command.update["plan_items"] == [
        {"content": "Inspect repo", "status": "completed", "active_form": ""},
        {"content": "Implement change", "status": "in_progress", "active_form": "Implementing"},
    ]
    assert command.update["rounds_since_update"] == 0
    assert command.update["updated_this_turn"] is True
    assert isinstance(command.update["messages"][0], ToolMessage)


def test_planning_middleware_tracks_stale_rounds() -> None:
    middleware = PlanningMiddleware()

    assert middleware.after_agent(
        {
            "messages": [],
            "plan_items": [{"content": "Keep going", "status": "pending", "active_form": ""}],
            "rounds_since_update": 2,
            "updated_this_turn": False,
        },
        runtime=None,
    ) == {"rounds_since_update": 3}

    assert middleware.after_agent(
        {
            "messages": [],
            "plan_items": [{"content": "Keep going", "status": "pending", "active_form": ""}],
            "rounds_since_update": 0,
            "updated_this_turn": True,
        },
        runtime=None,
    ) == {"updated_this_turn": False}


def test_planning_middleware_seeds_missing_defaults() -> None:
    middleware = PlanningMiddleware()

    assert middleware.before_agent({"messages": []}, runtime=None) == {
        "plan_items": [],
        "rounds_since_update": 0,
        "updated_this_turn": False,
    }


def test_reminder_text_triggers_only_for_stale_plans() -> None:
    items = [{"content": "Keep going", "status": "pending", "active_form": ""}]
    assert reminder_text(items, 2) is None
    assert reminder_text(items, 3) == "<reminder>Refresh your current plan before continuing.</reminder>"
