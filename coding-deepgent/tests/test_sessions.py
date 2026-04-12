from __future__ import annotations

import json

import pytest

from coding_deepgent.sessions import (
    JsonlSessionStore,
    SessionLoadError,
    resume_session,
    thread_config_for_session,
)


def test_jsonl_session_roundtrip_preserves_history_state_and_summary(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir, entrypoint="cli")
    store.append_message(context, role="user", content="plan this", message_index=0)
    store.append_state_snapshot(context, state={"todos": [], "rounds_since_update": 0})
    store.append_message(context, role="assistant", content="planned", message_index=1)
    store.append_state_snapshot(
        context,
        state={
            "todos": [
                {
                    "content": "Ship it",
                    "status": "in_progress",
                    "activeForm": "Shipping",
                }
            ],
            "rounds_since_update": 0,
        },
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)
    raw_records = [
        json.loads(line)
        for line in context.transcript_path.read_text(encoding="utf-8").splitlines()
    ]

    assert context.transcript_path == store.transcript_path_for(
        session_id=context.session_id,
        workdir=workdir,
    )
    assert len(raw_records) == 4
    assert raw_records[0]["record_type"] == "message"
    assert raw_records[1]["record_type"] == "state_snapshot"
    assert raw_records[0]["session_id"] == context.session_id
    assert raw_records[0]["cwd"] == str(workdir.resolve())
    assert loaded.history == [
        {"role": "user", "content": "plan this"},
        {"role": "assistant", "content": "planned"},
    ]
    assert loaded.state == {
        "todos": [
            {"content": "Ship it", "status": "in_progress", "activeForm": "Shipping"}
        ],
        "rounds_since_update": 0,
    }
    assert loaded.summary.session_id == context.session_id
    assert loaded.summary.first_prompt == "plan this"
    assert loaded.summary.message_count == 2
    assert loaded.summary.created_at is not None
    assert loaded.summary.updated_at is not None


def test_list_sessions_filters_by_workdir(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "shared-sessions-store")
    workdir_a = tmp_path / "repo-a"
    workdir_b = tmp_path / "repo-b"
    workdir_a.mkdir()
    workdir_b.mkdir()

    session_a = store.create_session(workdir=workdir_a)
    store.append_message(session_a, role="user", content="alpha")
    store.append_state_snapshot(
        session_a, state={"todos": [], "rounds_since_update": 0}
    )

    session_b = store.create_session(workdir=workdir_b)
    store.append_message(session_b, role="user", content="beta")
    store.append_state_snapshot(
        session_b, state={"todos": [], "rounds_since_update": 0}
    )

    listed = store.list_sessions(workdir=workdir_a)

    assert [summary.session_id for summary in listed] == [session_a.session_id]
    assert listed[0].first_prompt == "alpha"


def test_load_session_ignores_corrupt_unknown_and_invalid_later_snapshots(
    tmp_path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="resume me")
    store.append_state_snapshot(
        context,
        state={
            "todos": [
                {
                    "content": "Inspect",
                    "status": "in_progress",
                    "activeForm": "Inspecting",
                }
            ],
            "rounds_since_update": 3,
        },
    )

    with context.transcript_path.open("a", encoding="utf-8") as handle:
        handle.write("{not-json}\n")
        handle.write(
            json.dumps(
                {
                    "record_type": "future_record",
                    "version": 1,
                    "session_id": context.session_id,
                    "timestamp": "2026-04-13T00:00:00Z",
                    "cwd": str(workdir.resolve()),
                }
            )
            + "\n"
        )
        handle.write(
            json.dumps(
                {
                    "record_type": "state_snapshot",
                    "version": 1,
                    "session_id": "other-session",
                    "timestamp": "2026-04-13T00:00:01Z",
                    "cwd": str(workdir.resolve()),
                    "state": {"todos": [], "rounds_since_update": 99},
                }
            )
            + "\n"
        )
        handle.write(
            json.dumps(
                {
                    "record_type": "state_snapshot",
                    "version": 1,
                    "session_id": context.session_id,
                    "timestamp": "2026-04-13T00:00:02Z",
                    "cwd": str(workdir.resolve()),
                    "state": {"todos": "bad", "rounds_since_update": "bad"},
                }
            )
            + "\n"
        )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)

    assert loaded.history == [{"role": "user", "content": "resume me"}]
    assert loaded.state == {
        "todos": [
            {"content": "Inspect", "status": "in_progress", "activeForm": "Inspecting"}
        ],
        "rounds_since_update": 3,
    }


def test_load_session_requires_at_least_one_valid_message(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_state_snapshot(context, state={"todos": [], "rounds_since_update": 0})

    with pytest.raises(SessionLoadError, match="No valid session messages found"):
        store.load_session(session_id=context.session_id, workdir=workdir)


def test_load_session_without_snapshot_falls_back_to_default_state(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="hello")

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)

    assert loaded.history == [{"role": "user", "content": "hello"}]
    assert loaded.state == {"todos": [], "rounds_since_update": 0}


def test_resume_session_restores_runtime_state(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="continue")
    store.append_state_snapshot(
        context,
        state={
            "todos": [
                {"content": "Ship it", "status": "pending", "activeForm": "Shipping"}
            ],
            "rounds_since_update": 2,
        },
    )

    runtime_state = {
        "todos": [{"content": "Wrong", "status": "completed", "activeForm": "Wrong"}]
    }
    loaded = resume_session(
        store,
        session_id=context.session_id,
        workdir=workdir,
        runtime_state=runtime_state,
    )

    assert loaded.history == [{"role": "user", "content": "continue"}]
    assert runtime_state == {
        "todos": [
            {"content": "Ship it", "status": "pending", "activeForm": "Shipping"}
        ],
        "rounds_since_update": 2,
    }


def test_thread_config_uses_session_id_as_langgraph_thread_id() -> None:
    assert thread_config_for_session("session-123") == {
        "configurable": {"thread_id": "session-123"}
    }
