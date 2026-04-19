from __future__ import annotations

from langgraph.store.memory import InMemoryStore

from coding_deepgent.frontend.event_mapping import (
    runtime_events_to_frontend,
    task_snapshot_from_store,
    todo_snapshot_from_state,
)
from coding_deepgent.runtime import RuntimeEvent
from coding_deepgent.tasks import create_task


def test_todo_snapshot_from_state_filters_invalid_items() -> None:
    snapshot = todo_snapshot_from_state(
        {
            "todos": [
                {
                    "content": "Ship CLI",
                    "status": "in_progress",
                    "activeForm": "Shipping CLI",
                },
                {"content": "Bad status", "status": "unknown"},
                "not an item",
            ]
        }
    )

    assert [item.model_dump() for item in snapshot.items] == [
        {
            "content": "Ship CLI",
            "status": "in_progress",
            "activeForm": "Shipping CLI",
        }
    ]


def test_runtime_tool_guard_events_map_to_tool_events() -> None:
    mapped = runtime_events_to_frontend(
        [
            RuntimeEvent(
                kind="allowed",
                message="Tool guard allowed for read_file",
                session_id="session-1",
                metadata={
                    "source": "tool_guard",
                    "phase": "allowed",
                    "tool": "read_file",
                    "tool_call_id": "call-1",
                },
            ),
            RuntimeEvent(
                kind="completed",
                message="Tool guard completed for read_file",
                session_id="session-1",
                metadata={
                    "source": "tool_guard",
                    "phase": "completed",
                    "tool": "read_file",
                    "tool_call_id": "call-1",
                },
            ),
        ]
    )

    assert [event.type for event in mapped] == ["tool_started", "tool_finished"]


def test_task_snapshot_from_store_filters_to_active_task_records() -> None:
    store = InMemoryStore()
    create_task(store, title="Ship CLI")
    create_task(store, title="Review tests", owner="kun")

    snapshot = task_snapshot_from_store(store)

    assert sorted(
        (item.content, item.status, item.owner) for item in snapshot.items
    ) == [
        ("Review tests", "pending", "kun"),
        ("Ship CLI", "pending", None),
    ]
