from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from dependency_injector import providers

from coding_deepgent.agent_loop_service import run_agent_loop
from coding_deepgent.agent_runtime_service import session_payload, update_session_state
from coding_deepgent.compact import ORPHAN_TOOL_RESULT_TOMBSTONE
from coding_deepgent.containers import AppContainer
from coding_deepgent.hooks import LocalHookRegistry
from coding_deepgent.memory import MemoryRecord, save_memory_record
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext, RuntimeInvocation
from coding_deepgent.sessions import JsonlSessionStore
from coding_deepgent.settings import Settings


class CapturingAgent:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    def invoke(
        self,
        payload: dict[str, Any],
        *,
        context: RuntimeContext,
        config: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        del context, config
        self.payloads.append(payload)
        return {
            "messages": [
                *payload["messages"],
                {"role": "assistant", "content": "ok"},
            ],
            "todos": [],
            "rounds_since_update": 0,
        }


class FailingAgent:
    def invoke(
        self,
        payload: dict[str, Any],
        *,
        context: RuntimeContext,
        config: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        del payload, context, config
        raise RuntimeError("model transport failed")


def _invocation(tmp_path: Path, *, sink: InMemoryEventSink) -> RuntimeInvocation:
    return RuntimeInvocation(
        context=RuntimeContext(
            session_id="session-1",
            workdir=tmp_path,
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="test-agent",
            skill_dir=tmp_path / "skills",
            event_sink=sink,
            hook_registry=LocalHookRegistry(),
        ),
        config={"configurable": {"thread_id": "session-1"}},
    )


def _recorded_invocation(
    tmp_path: Path,
    *,
    sink: InMemoryEventSink,
    store: JsonlSessionStore,
) -> RuntimeInvocation:
    context = store.create_session(workdir=tmp_path, session_id="session-1")
    store.append_message(context, role="user", content="start")
    invocation = _invocation(tmp_path, sink=sink)
    return RuntimeInvocation(
        context=RuntimeContext(
            session_id=invocation.context.session_id,
            workdir=invocation.context.workdir,
            trusted_workdirs=invocation.context.trusted_workdirs,
            entrypoint=invocation.context.entrypoint,
            agent_name=invocation.context.agent_name,
            skill_dir=invocation.context.skill_dir,
            event_sink=invocation.context.event_sink,
            hook_registry=invocation.context.hook_registry,
            session_context=context,
        ),
        config=invocation.config,
    )


def _unused_container() -> AppContainer:
    raise AssertionError("test provides an active container")


def test_session_payload_preserves_session_memory_artifact() -> None:
    payload = session_payload(
        {
            "todos": [],
            "rounds_since_update": 0,
            "session_memory": {
                "content": "Keep repo focus.",
                "source": "manual",
                "message_count": 1,
                "updated_at": "2026-04-15T00:00:00Z",
            },
        }
    )

    assert payload["session_memory"] == {
        "content": "Keep repo focus.",
        "source": "manual",
        "message_count": 1,
        "updated_at": "2026-04-15T00:00:00Z",
    }


def test_session_payload_preserves_long_term_memory_snapshot() -> None:
    payload = session_payload(
        {
            "todos": [],
            "rounds_since_update": 0,
            "long_term_memory": {
                "entries": [
                    {
                        "key": "abc123",
                        "type": "feedback",
                        "summary": "Run lint before commit",
                    }
                ],
                "updated_at": "2026-04-18T00:00:00Z",
            },
        }
    )

    assert payload["long_term_memory"] == {
        "entries": [
            {
                "key": "abc123",
                "type": "feedback",
                "summary": "Run lint before commit",
            }
        ],
        "updated_at": "2026-04-18T00:00:00Z",
    }


def test_update_session_state_preserves_session_memory_artifact() -> None:
    state = {"todos": [], "rounds_since_update": 0}

    update_session_state(
        state,
        {
            "todos": [],
            "rounds_since_update": 1,
            "session_memory": {
                "content": "Keep repo focus.",
                "source": "live_compact",
                "message_count": 2,
                "updated_at": "2026-04-15T00:00:00Z",
            },
        },
    )

    assert state["session_memory"] == {
        "content": "Keep repo focus.",
        "source": "live_compact",
        "message_count": 2,
        "updated_at": "2026-04-15T00:00:00Z",
    }


def test_update_session_state_preserves_long_term_memory_snapshot() -> None:
    state = {"todos": [], "rounds_since_update": 0}

    update_session_state(
        state,
        {
            "todos": [],
            "rounds_since_update": 1,
            "long_term_memory": {
                "entries": [
                    {
                        "key": "abc123",
                        "type": "feedback",
                        "summary": "Run lint before commit",
                    }
                ],
                "updated_at": "2026-04-18T00:00:00Z",
            },
        },
    )

    assert state["long_term_memory"] == {
        "entries": [
            {
                "key": "abc123",
                "type": "feedback",
                "summary": "Run lint before commit",
            }
        ],
        "updated_at": "2026-04-18T00:00:00Z",
    }


def test_agent_loop_emits_orphan_tombstoned_event_and_uses_repaired_projection(
    tmp_path: Path,
) -> None:
    sink = InMemoryEventSink()
    store = JsonlSessionStore(tmp_path / "sessions")
    invocation = _recorded_invocation(tmp_path, sink=sink, store=store)
    agent = CapturingAgent()
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "missing-call",
                    "content": "raw output",
                }
            ],
        }
    ]

    result = run_agent_loop(
        messages=messages,
        session_state={},
        session_id="session-1",
        container=cast(AppContainer, object()),
        build_container=_unused_container,
        build_agent=lambda: agent,
        build_runtime_invocation=lambda **_: invocation,
    )

    assert result == "ok"
    assert agent.payloads[0]["messages"] == [
        {
            "role": "user",
            "content": [{"type": "text", "text": ORPHAN_TOOL_RESULT_TOMBSTONE}],
        }
    ]
    events = sink.snapshot()
    assert events[0].kind == "orphan_tombstoned"
    assert events[0].metadata["tombstoned_count"] == 1
    loaded = store.load_session(session_id="session-1", workdir=tmp_path)
    assert loaded.evidence[0].metadata == {
        "event_kind": "orphan_tombstoned",
        "source": "message_projection",
        "reason": "missing_tool_use",
        "tombstoned_count": 1,
        "message_count": 1,
    }


def test_agent_loop_emits_structured_query_error_event_and_evidence(
    tmp_path: Path,
) -> None:
    sink = InMemoryEventSink()
    store = JsonlSessionStore(tmp_path / "sessions")
    invocation = _recorded_invocation(tmp_path, sink=sink, store=store)

    with pytest.raises(RuntimeError, match="model transport failed"):
        run_agent_loop(
            messages=[{"role": "user", "content": "hello"}],
            session_state={},
            session_id="session-1",
            container=cast(AppContainer, object()),
            build_container=_unused_container,
            build_agent=lambda: FailingAgent(),
            build_runtime_invocation=lambda **_: invocation,
        )

    event = sink.snapshot()[0]
    assert event.kind == "query_error"
    assert event.metadata == {
        "source": "agent_loop",
        "phase": "agent_invoke",
        "error_class": "RuntimeError",
        "retry_count": 0,
    }
    loaded = store.load_session(session_id="session-1", workdir=tmp_path)
    assert loaded.evidence[0].status == "failed"
    assert loaded.evidence[0].metadata == {
        "event_kind": "query_error",
        "source": "agent_loop",
        "phase": "agent_invoke",
        "error_class": "RuntimeError",
        "retry_count": 0,
    }


def test_run_agent_loop_refreshes_long_term_memory_snapshot_from_store(
    tmp_path: Path,
) -> None:
    sink = InMemoryEventSink()
    container = AppContainer(
        settings=providers.Object(Settings(workdir=tmp_path, store_backend="memory")),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(lambda **kwargs: object()),
    )
    save_memory_record(
        container.runtime.store(),
        MemoryRecord(
            type="feedback",
            rule="Run lint before commit",
            why="The repo requires clean validation before code submission",
            how_to_apply="Before any commit-like completion step, run lint first",
        ),
    )
    invocation = _invocation(tmp_path, sink=sink)
    session_state: dict[str, Any] = {}

    result = run_agent_loop(
        messages=[{"role": "user", "content": "hello"}],
        session_state=session_state,
        session_id="session-1",
        container=container,
        build_container=_unused_container,
        build_agent=lambda: CapturingAgent(),
        build_runtime_invocation=lambda **_: invocation,
    )

    assert result == "ok"
    assert session_state["long_term_memory"]["entries"][0]["type"] == "feedback"
    assert (
        session_state["long_term_memory"]["entries"][0]["summary"]
        == "Run lint before commit"
    )
