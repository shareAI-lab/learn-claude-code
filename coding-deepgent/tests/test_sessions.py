from __future__ import annotations

import json
from typing import Any

import pytest

from coding_deepgent.sessions import (
    COLLAPSE_EVENT_KIND,
    COMPACT_EVENT_KIND,
    EVIDENCE_RECORD_TYPE,
    JsonlSessionStore,
    SessionMessage,
    SessionLoadError,
    TRANSCRIPT_EVENT_RECORD_TYPE,
    build_compression_view,
    build_recovery_brief,
    render_recovery_brief,
    resume_session,
    thread_config_for_session,
)
from coding_deepgent.sessions.records import message_id_for_index
from coding_deepgent.sessions.session_memory import SESSION_MEMORY_STATE_KEY
from coding_deepgent.memory import LONG_TERM_MEMORY_STATE_KEY
from coding_deepgent.compact import COLLAPSE_BOUNDARY_PREFIX, COLLAPSE_SUMMARY_PREFIX


def _history_summary(history: list[SessionMessage]) -> list[tuple[str, str, str]]:
    return [(item.message_id, item.role, item.content) for item in history]


def _projected_history(history: list[SessionMessage]) -> list[dict[str, Any]]:
    return [item.as_conversation_dict() for item in history]


def test_jsonl_session_roundtrip_preserves_history_state_and_summary(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir, entrypoint="cli")
    store.append_message(context, role="user", content="plan this")
    store.append_state_snapshot(context, state={"todos": [], "rounds_since_update": 0})
    store.append_message(context, role="assistant", content="planned")
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
    assert raw_records[0]["message_id"] == message_id_for_index(0)
    assert raw_records[2]["message_id"] == message_id_for_index(1)
    assert _history_summary(loaded.history) == [
        (message_id_for_index(0), "user", "plan this"),
        (message_id_for_index(1), "assistant", "planned"),
    ]
    assert loaded.compacted_history == _projected_history(loaded.history)
    assert loaded.compacted_history_source.mode == "raw"
    assert loaded.compacted_history_source.reason == "no_compacts"
    assert loaded.compacted_history_source.compact_index is None
    assert loaded.state == {
        "todos": [
            {"content": "Ship it", "status": "in_progress", "activeForm": "Shipping"}
        ],
        "rounds_since_update": 0,
    }
    assert loaded.summary.session_id == context.session_id
    assert loaded.summary.first_prompt == "plan this"
    assert loaded.summary.message_count == 2
    assert loaded.summary.evidence_count == 0
    assert loaded.summary.created_at is not None
    assert loaded.summary.updated_at is not None


def test_jsonl_session_roundtrip_preserves_session_memory_artifact(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir, entrypoint="cli")
    store.append_message(context, role="user", content="plan this")
    store.append_state_snapshot(
        context,
        state={
            "todos": [],
            "rounds_since_update": 0,
            SESSION_MEMORY_STATE_KEY: {
                "content": "Current repo focus is deterministic assist.",
                "source": "manual",
                "message_count": 1,
                "updated_at": "2026-04-15T00:00:00Z",
            },
        },
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)

    assert loaded.state[SESSION_MEMORY_STATE_KEY] == {
        "content": "Current repo focus is deterministic assist.",
        "source": "manual",
        "message_count": 1,
        "updated_at": "2026-04-15T00:00:00Z",
    }


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

    assert _history_summary(loaded.history) == [
        (message_id_for_index(0), "user", "resume me")
    ]
    assert loaded.state == {
        "todos": [
            {"content": "Inspect", "status": "in_progress", "activeForm": "Inspecting"}
        ],
        "rounds_since_update": 3,
    }


def test_load_session_ignores_invalid_session_memory_artifact(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="resume me")
    store.append_state_snapshot(
        context,
        state={
            "todos": [],
            "rounds_since_update": 0,
            SESSION_MEMORY_STATE_KEY: {
                "content": "   ",
                "source": "manual",
                "message_count": 1,
                "updated_at": "2026-04-15T00:00:00Z",
            },
        },
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)

    assert loaded.state == {
        "todos": [],
        "rounds_since_update": 0,
    }


def test_session_evidence_roundtrip_and_recovery_brief(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="ship")
    store.append_state_snapshot(
        context,
        state={
            "todos": [
                {
                    "content": "Implement recovery",
                    "status": "in_progress",
                    "activeForm": "Implementing recovery",
                },
                {
                    "content": "Already done",
                    "status": "completed",
                    "activeForm": "Completing",
                },
            ],
            "rounds_since_update": 0,
        },
    )
    store.append_evidence(
        context,
        kind="verification",
        summary="targeted tests passed",
        status="passed",
        subject="pytest",
        metadata={"command": "pytest tests/test_sessions.py"},
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)
    raw_records = [
        json.loads(line)
        for line in context.transcript_path.read_text(encoding="utf-8").splitlines()
    ]
    brief = build_recovery_brief(loaded)
    rendered = render_recovery_brief(brief)

    assert raw_records[-1]["record_type"] == EVIDENCE_RECORD_TYPE
    assert loaded.summary.evidence_count == 1
    assert loaded.evidence[0].kind == "verification"
    assert loaded.evidence[0].status == "passed"
    assert loaded.evidence[0].summary == "targeted tests passed"
    assert loaded.evidence[0].metadata == {"command": "pytest tests/test_sessions.py"}
    assert brief.active_todos == ("Implement recovery",)
    assert "Already done" not in rendered
    assert "[passed] verification: targeted tests passed" in rendered


def test_recovery_brief_renders_verification_provenance_only(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="resume")
    store.append_evidence(
        context,
        kind="runtime",
        summary="Prompt completed.",
        status="completed",
        metadata={"internal": "hidden"},
    )
    store.append_evidence(
        context,
        kind="verification",
        summary="Checked targeted tests.",
        status="failed",
        subject="plan-1",
        metadata={"plan_id": "plan-1", "verdict": "FAIL", "ignored": "value"},
    )

    rendered = render_recovery_brief(
        build_recovery_brief(store.load_session(session_id=context.session_id, workdir=workdir))
    )

    assert "- [completed] runtime: Prompt completed." in rendered
    assert "internal=hidden" not in rendered
    assert (
        "- [failed] verification: Checked targeted tests. (plan=plan-1; verdict=FAIL)"
        in rendered
    )
    assert "ignored=value" not in rendered


def test_recovery_brief_renders_session_memory_status(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="resume")
    store.append_state_snapshot(
        context,
        state={
            "todos": [],
            "rounds_since_update": 0,
            SESSION_MEMORY_STATE_KEY: {
                "content": "Current repo focus is deterministic assist.",
                "source": "manual",
                "message_count": 1,
                "updated_at": "2026-04-15T00:00:00Z",
            },
        },
    )

    rendered = render_recovery_brief(
        build_recovery_brief(
            store.load_session(session_id=context.session_id, workdir=workdir)
        )
    )

    assert "Current-session memory:" in rendered
    assert "[current] Current repo focus is deterministic assist." in rendered


def test_recovery_brief_marks_stale_session_memory_status(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="resume")
    store.append_message(context, role="assistant", content="continued")
    store.append_state_snapshot(
        context,
        state={
            "todos": [],
            "rounds_since_update": 0,
            SESSION_MEMORY_STATE_KEY: {
                "content": "Current repo focus is deterministic assist.",
                "source": "manual",
                "message_count": 1,
                "updated_at": "2026-04-15T00:00:00Z",
            },
        },
    )

    rendered = render_recovery_brief(
        build_recovery_brief(
            store.load_session(session_id=context.session_id, workdir=workdir)
        )
    )

    assert "[stale] Current repo focus is deterministic assist." in rendered


def test_recovery_brief_renders_long_term_memory_snapshot(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir, entrypoint="cli")
    store.append_message(context, role="user", content="resume")
    store.append_state_snapshot(
        context,
        state={
            "todos": [],
            "rounds_since_update": 0,
            LONG_TERM_MEMORY_STATE_KEY: {
                "entries": [
                    {
                        "key": "fb-1",
                        "type": "feedback",
                        "summary": "Run lint before commit",
                    },
                    {
                        "key": "proj-1",
                        "type": "project",
                        "summary": "Use JWT for auth",
                    },
                ],
                "updated_at": "2026-04-18T00:00:00Z",
            },
        },
    )

    rendered = render_recovery_brief(
        build_recovery_brief(
            store.load_session(session_id=context.session_id, workdir=workdir)
        )
    )

    assert "Long-term memory:" in rendered
    assert "[feedback] Run lint before commit (key=fb-1)" in rendered
    assert "[project] Use JWT for auth (key=proj-1)" in rendered


def test_compact_record_roundtrip_does_not_enter_history(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir, entrypoint="cli")
    store.append_message(context, role="user", content="start")
    store.append_compact(
        context,
        trigger="manual",
        summary="Older work was summarized.",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
        metadata={"source": "test"},
    )
    store.append_message(context, role="assistant", content="continued")

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)
    raw_records = [
        json.loads(line)
        for line in context.transcript_path.read_text(encoding="utf-8").splitlines()
    ]

    assert raw_records[1]["record_type"] == TRANSCRIPT_EVENT_RECORD_TYPE
    assert raw_records[1]["event_kind"] == COMPACT_EVENT_KIND
    assert _history_summary(loaded.history) == [
        (message_id_for_index(0), "user", "start"),
        (message_id_for_index(1), "assistant", "continued"),
    ]
    assert loaded.compacted_history[0]["role"] == "system"
    assert loaded.compacted_history[1]["role"] == "user"
    assert loaded.compacted_history[2] == {"role": "assistant", "content": "continued"}
    assert loaded.compacted_history_source.mode == "compact"
    assert loaded.compacted_history_source.reason == "latest_valid_compact"
    assert loaded.compacted_history_source.compact_index == 0
    assert loaded.summary.message_count == 2
    assert loaded.summary.compact_count == 1
    assert loaded.compacts[0].trigger == "manual"
    assert loaded.compacts[0].summary == "Older work was summarized."
    assert loaded.compacts[0].start_message_id == message_id_for_index(0)
    assert loaded.compacts[0].end_message_id == message_id_for_index(0)
    assert loaded.compacts[0].covered_message_ids == (message_id_for_index(0),)
    assert loaded.compacts[0].metadata == {"source": "test"}
    brief = build_recovery_brief(loaded)
    rendered = render_recovery_brief(brief)
    assert brief.recent_compacts[0].summary == "Older work was summarized."
    assert "[manual] Older work was summarized." in rendered


def test_collapse_record_roundtrip_does_not_enter_history(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir, entrypoint="cli")
    store.append_message(context, role="user", content="start")
    store.append_message(context, role="assistant", content="continued")
    store.append_collapse(
        context,
        trigger="threshold_tokens",
        summary="Older work was collapsed.",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
        metadata={"source": "runtime_pressure"},
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)
    raw_records = [
        json.loads(line)
        for line in context.transcript_path.read_text(encoding="utf-8").splitlines()
    ]

    assert raw_records[-1]["record_type"] == TRANSCRIPT_EVENT_RECORD_TYPE
    assert raw_records[-1]["event_kind"] == COLLAPSE_EVENT_KIND
    assert _history_summary(loaded.history) == [
        (message_id_for_index(0), "user", "start"),
        (message_id_for_index(1), "assistant", "continued"),
    ]
    assert loaded.summary.collapse_count == 1
    assert loaded.collapses[0].trigger == "threshold_tokens"
    assert loaded.collapses[0].summary == "Older work was collapsed."
    assert loaded.collapses[0].start_message_id == message_id_for_index(0)
    assert loaded.collapses[0].end_message_id == message_id_for_index(0)
    assert loaded.collapses[0].covered_message_ids == (message_id_for_index(0),)
    assert loaded.collapses[0].metadata == {"source": "runtime_pressure"}


def test_sidechain_message_roundtrip_stays_out_of_parent_history(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir, entrypoint="cli")
    store.append_message(context, role="user", content="parent prompt")
    store.append_sidechain_message(
        context,
        agent_type="general",
        role="user",
        content="Inspect the repository",
        subagent_thread_id="session-1:general",
        parent_message_id=message_id_for_index(0),
        parent_thread_id="session-1",
    )
    store.append_sidechain_message(
        context,
        agent_type="general",
        role="assistant",
        content="Found the relevant files.",
        subagent_thread_id="session-1:general",
        parent_message_id=message_id_for_index(0),
        parent_thread_id="session-1",
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)

    assert _history_summary(loaded.history) == [
        (message_id_for_index(0), "user", "parent prompt")
    ]
    assert loaded.compacted_history == _projected_history(loaded.history)
    assert loaded.collapsed_history == _projected_history(loaded.history)
    assert len(loaded.sidechain_messages) == 2
    assert loaded.sidechain_messages[0].agent_type == "general"
    assert loaded.sidechain_messages[0].role == "user"
    assert loaded.sidechain_messages[0].content == "Inspect the repository"
    assert loaded.sidechain_messages[0].parent_message_id == message_id_for_index(0)
    assert loaded.sidechain_messages[0].parent_thread_id == "session-1"
    assert loaded.sidechain_messages[0].subagent_thread_id == "session-1:general"
    assert loaded.sidechain_messages[1].role == "assistant"
    assert loaded.sidechain_messages[1].content == "Found the relevant files."


def test_load_session_collapsed_history_uses_newest_non_overlapping_collapses(
    tmp_path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="first")
    store.append_message(context, role="assistant", content="second")
    store.append_message(context, role="user", content="third")
    store.append_collapse(
        context,
        trigger="threshold_tokens",
        summary="older collapse",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
    )
    store.append_collapse(
        context,
        trigger="threshold_tokens",
        summary="newer collapse",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(1),
        covered_message_ids=[message_id_for_index(0), message_id_for_index(1)],
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)

    assert loaded.collapsed_history_source.mode == "collapse"
    assert loaded.collapsed_history_source.collapse_index == 1
    assert loaded.collapsed_history[0]["role"] == "system"
    assert COLLAPSE_BOUNDARY_PREFIX in str(loaded.collapsed_history[0]["content"])
    assert COLLAPSE_SUMMARY_PREFIX in str(loaded.collapsed_history[1]["content"])
    assert "newer collapse" in str(loaded.collapsed_history[1]["content"])
    assert "older collapse" not in str(loaded.collapsed_history[1]["content"])
    assert loaded.collapsed_history[2] == {"role": "user", "content": "third"}


def test_load_session_collapsed_history_falls_back_to_raw_on_invalid_refs(
    tmp_path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="first")
    store.append_collapse(
        context,
        trigger="threshold_tokens",
        summary="invalid collapse",
        start_message_id="msg-unknown",
        end_message_id="msg-unknown",
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)

    assert loaded.collapsed_history == _projected_history(loaded.history)
    assert loaded.collapsed_history_source.mode == "raw"
    assert loaded.collapsed_history_source.reason == "no_valid_collapse"


def test_compression_view_exposes_raw_projection_and_timeline(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="first")
    store.append_message(context, role="assistant", content="second")
    store.append_message(context, role="user", content="third")
    store.append_compact(
        context,
        trigger="manual",
        summary="First message compacted.",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
        metadata={"source": "manual"},
    )
    store.append_collapse(
        context,
        trigger="threshold_tokens",
        summary="First two messages collapsed.",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(1),
        covered_message_ids=[message_id_for_index(0), message_id_for_index(1)],
        metadata={"source": "runtime_pressure"},
    )
    store.append_evidence(
        context,
        kind="runtime_event",
        summary="Live microcompact cleared older tool results.",
        status="completed",
        metadata={
            "event_kind": "microcompact",
            "source": "runtime_pressure",
            "trigger": "time_gap",
            "affected_tool_call_ids": ["call-1"],
        },
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)
    view = build_compression_view(loaded)

    assert view.projection_mode == "collapse"
    assert [(message.message_id, message.model_visible) for message in view.raw_messages] == [
        (message_id_for_index(0), False),
        (message_id_for_index(1), False),
        (message_id_for_index(2), True),
    ]
    assert view.raw_messages[0].hidden_by_event_ids == ("collapse-0",)
    assert [message.source for message in view.model_projection] == [
        "collapse_boundary",
        "collapse_summary",
        "raw",
    ]
    assert view.model_projection[0].covered_message_ids == (
        message_id_for_index(0),
        message_id_for_index(1),
    )
    timeline_by_type = {event.event_type: event for event in view.timeline}
    assert timeline_by_type["compact"].affected_message_ids == (message_id_for_index(0),)
    assert timeline_by_type["collapse"].affected_message_ids == (
        message_id_for_index(0),
        message_id_for_index(1),
    )
    assert timeline_by_type["microcompact"].affected_tool_call_ids == ("call-1",)
    assert timeline_by_type["microcompact"].trigger == "time_gap"


def test_compression_view_can_force_raw_projection(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="first")
    store.append_collapse(
        context,
        trigger="threshold_tokens",
        summary="First collapsed.",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)
    view = build_compression_view(loaded, projection_mode="raw")

    assert view.projection_mode == "raw"
    assert view.raw_messages[0].model_visible
    assert view.model_projection[0].source == "raw"
    assert view.model_projection[0].message_id == message_id_for_index(0)


def test_load_session_ignores_invalid_compact_records(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="resume me")
    with context.transcript_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "record_type": TRANSCRIPT_EVENT_RECORD_TYPE,
                    "version": 1,
                    "session_id": context.session_id,
                    "timestamp": "2026-04-13T00:00:00Z",
                    "event_kind": COMPACT_EVENT_KIND,
                    "payload": {
                        "trigger": "",
                        "summary": "bad",
                        "start_message_id": message_id_for_index(0),
                        "end_message_id": message_id_for_index(0),
                    },
                }
            )
            + "\n"
        )
        handle.write(
            json.dumps(
                {
                    "record_type": TRANSCRIPT_EVENT_RECORD_TYPE,
                    "version": 1,
                    "session_id": "other",
                    "timestamp": "2026-04-13T00:00:01Z",
                    "event_kind": COMPACT_EVENT_KIND,
                    "payload": {
                        "trigger": "manual",
                        "summary": "foreign",
                        "start_message_id": message_id_for_index(0),
                        "end_message_id": message_id_for_index(0),
                    },
                }
            )
            + "\n"
        )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)

    assert loaded.compacts == []
    assert loaded.summary.compact_count == 0


def test_recovery_brief_limits_recent_compacts_in_original_order(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="resume")
    for index in range(5):
        store.append_compact(
            context,
            trigger="manual",
            summary=f"compact-{index}",
            start_message_id=message_id_for_index(0),
            end_message_id=message_id_for_index(0),
            covered_message_ids=[message_id_for_index(0)],
        )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)
    brief = build_recovery_brief(loaded, compact_limit=2)
    rendered = render_recovery_brief(brief)

    assert [item.summary for item in brief.recent_compacts] == [
        "compact-3",
        "compact-4",
    ]
    assert "[manual] compact-3" in rendered
    assert "[manual] compact-4" in rendered


def test_load_session_compacted_history_falls_back_to_raw_history_on_invalid_tail_range(
    tmp_path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="first")
    store.append_message(context, role="assistant", content="second")
    store.append_compact(
        context,
        trigger="manual",
        summary="summary",
        start_message_id="msg-unknown",
        end_message_id="msg-unknown",
        covered_message_ids=["msg-unknown"],
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)

    assert _history_summary(loaded.history) == [
        (message_id_for_index(0), "user", "first"),
        (message_id_for_index(1), "assistant", "second"),
    ]
    assert loaded.compacted_history == _projected_history(loaded.history)
    assert loaded.compacted_history_source.mode == "raw"
    assert loaded.compacted_history_source.reason == "no_valid_compact"
    assert loaded.compacted_history_source.compact_index is None


def test_load_session_compacted_history_uses_latest_valid_compact_record(
    tmp_path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="first")
    store.append_message(context, role="assistant", content="second")
    store.append_compact(
        context,
        trigger="manual",
        summary="valid compact",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
    )
    store.append_compact(
        context,
        trigger="manual",
        summary="invalid compact",
        start_message_id="msg-unknown",
        end_message_id="msg-unknown",
        covered_message_ids=["msg-unknown"],
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)

    assert loaded.compacted_history[0]["role"] == "system"
    assert "valid compact" in str(loaded.compacted_history[1]["content"])
    assert "invalid compact" not in str(loaded.compacted_history[1]["content"])
    assert loaded.compacted_history_source.mode == "compact"
    assert loaded.compacted_history_source.reason == "latest_valid_compact"
    assert loaded.compacted_history_source.compact_index == 0


def test_load_session_compacted_history_uses_newest_valid_compact_record(
    tmp_path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="first")
    store.append_message(context, role="assistant", content="second")
    store.append_message(context, role="user", content="third")
    store.append_compact(
        context,
        trigger="manual",
        summary="older compact",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(0),
        covered_message_ids=[message_id_for_index(0)],
    )
    store.append_compact(
        context,
        trigger="manual",
        summary="newer compact",
        start_message_id=message_id_for_index(0),
        end_message_id=message_id_for_index(1),
        covered_message_ids=[message_id_for_index(0), message_id_for_index(1)],
    )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)

    assert _history_summary(loaded.history) == [
        (message_id_for_index(0), "user", "first"),
        (message_id_for_index(1), "assistant", "second"),
        (message_id_for_index(2), "user", "third"),
    ]
    assert "newer compact" in str(loaded.compacted_history[1]["content"])
    assert "older compact" not in str(loaded.compacted_history[1]["content"])
    assert loaded.compacted_history[-1] == {"role": "user", "content": "third"}
    assert loaded.compacted_history_source.mode == "compact"
    assert loaded.compacted_history_source.compact_index == 1


def test_recovery_brief_limits_recent_evidence_in_original_order(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="resume")
    store.append_state_snapshot(
        context,
        state={
            "todos": [
                {
                    "content": "Keep context brief",
                    "status": "pending",
                    "activeForm": "Keeping context brief",
                }
            ],
            "rounds_since_update": 0,
        },
    )
    for index in range(7):
        store.append_evidence(
            context,
            kind="verification",
            summary=f"evidence-{index}",
            status="passed",
        )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)
    brief = build_recovery_brief(loaded, evidence_limit=3)

    assert [item.summary for item in brief.recent_evidence] == [
        "evidence-4",
        "evidence-5",
        "evidence-6",
    ]
    assert brief.active_todos == ("Keep context brief",)


def test_load_session_ignores_invalid_evidence_records(tmp_path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    workdir = tmp_path / "repo"
    workdir.mkdir()

    context = store.create_session(workdir=workdir)
    store.append_message(context, role="user", content="resume me")
    with context.transcript_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "record_type": "evidence",
                    "version": 1,
                    "session_id": context.session_id,
                    "timestamp": "2026-04-13T00:00:00Z",
                    "cwd": str(workdir.resolve()),
                    "kind": "",
                    "summary": "bad",
                    "status": "passed",
                }
            )
            + "\n"
        )
        handle.write(
            json.dumps(
                {
                    "record_type": "evidence",
                    "version": 1,
                    "session_id": "other",
                    "timestamp": "2026-04-13T00:00:01Z",
                    "cwd": str(workdir.resolve()),
                    "kind": "verification",
                    "summary": "foreign",
                    "status": "passed",
                }
            )
            + "\n"
        )

    loaded = store.load_session(session_id=context.session_id, workdir=workdir)

    assert loaded.evidence == []
    assert loaded.summary.evidence_count == 0


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

    assert _history_summary(loaded.history) == [
        (message_id_for_index(0), "user", "hello")
    ]
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

    assert _history_summary(loaded.history) == [
        (message_id_for_index(0), "user", "continue")
    ]
    assert runtime_state == {
        "todos": [
            {"content": "Ship it", "status": "pending", "activeForm": "Shipping"}
        ],
        "rounds_since_update": 2,
    }
    runtime_state["todos"][0]["content"] = "Mutated"
    assert loaded.state == {
        "todos": [
            {"content": "Ship it", "status": "pending", "activeForm": "Shipping"}
        ],
        "rounds_since_update": 2,
    }


def test_thread_config_uses_session_id_as_langgraph_thread_id() -> None:
    assert thread_config_for_session("session-123") == {
        "configurable": {"thread_id": "session-123"}
    }
