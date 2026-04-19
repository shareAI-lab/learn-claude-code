from __future__ import annotations

from langgraph.store.memory import InMemoryStore

from coding_deepgent.frontend.event_mapping import (
    context_snapshot_from_loaded,
    runtime_events_to_frontend,
    subagent_snapshot_from_loaded,
    task_snapshot_from_store,
    todo_snapshot_from_state,
)
from coding_deepgent.runtime import RuntimeEvent
from coding_deepgent.sessions import JsonlSessionStore
from coding_deepgent.sessions.records import message_id_for_index
from coding_deepgent.sessions.session_memory import write_session_memory_artifact
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


def test_context_snapshot_from_loaded_exposes_projection_counts(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions")
    workdir = tmp_path / "repo"
    workdir.mkdir()
    context = store.create_session(workdir=workdir, session_id="session-1")
    store.append_message(context, role="user", content="first")
    store.append_message(context, role="assistant", content="second")
    store.append_collapse(
        context,
        trigger="threshold_tokens",
        summary="Earlier work collapsed.",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
    )
    state = {"todos": [], "rounds_since_update": 0}
    write_session_memory_artifact(
        state,
        content="Current focus.",
        message_count=2,
        token_count=2,
        tool_call_count=0,
    )
    store.append_state_snapshot(context, state=state)
    loaded = store.load_session(session_id="session-1", workdir=workdir)

    snapshot = context_snapshot_from_loaded(loaded)

    assert snapshot.projection_mode == "collapse"
    assert snapshot.history_messages == 2
    assert snapshot.model_messages == 3
    assert snapshot.visible_messages == 1
    assert snapshot.hidden_messages == 1
    assert snapshot.collapse_count == 1
    assert snapshot.session_memory_status == "current"
    assert snapshot.latest_event == "collapse"


def test_subagent_snapshot_from_loaded_limits_recent_sidechain_messages(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions")
    workdir = tmp_path / "repo"
    workdir.mkdir()
    context = store.create_session(workdir=workdir, session_id="session-1")
    store.append_message(context, role="user", content="first")
    for index in range(3):
        store.append_sidechain_message(
            context,
            agent_type="general",
            role="assistant",
            content=f"sidechain {index}",
            subagent_thread_id=f"child-{index}",
        )
    loaded = store.load_session(session_id="session-1", workdir=workdir)

    snapshot = subagent_snapshot_from_loaded(loaded, limit=2)

    assert snapshot.total == 3
    assert [item.content for item in snapshot.items] == ["sidechain 1", "sidechain 2"]
