from __future__ import annotations

import pytest
from pydantic import ValidationError

from coding_deepgent.hooks import (
    HookDispatchOutcome,
    HookPayload,
    HookResult,
    LocalHookRegistry,
)
from coding_deepgent.hooks.dispatcher import dispatch_context_hook, dispatch_runtime_hook
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext, RuntimeInvocation
from coding_deepgent.sessions import JsonlSessionStore, build_recovery_brief, render_recovery_brief
from pathlib import Path


def test_local_hook_registry_runs_matching_hooks_in_order() -> None:
    registry = LocalHookRegistry()
    seen: list[str] = []

    def first(payload: HookPayload) -> HookResult:
        seen.append(f"first:{payload.event}")
        return HookResult(reason="first")

    def second(payload: HookPayload) -> HookResult:
        seen.append(f"second:{payload.event}")
        return HookResult.model_validate(
            {"continue": False, "decision": "block", "reason": "second"}
        )

    registry.register("PreToolUse", first)
    registry.register("PreToolUse", second)

    results = registry.run(HookPayload(event="PreToolUse", data={"tool": "bash"}))

    assert seen == ["first:PreToolUse", "second:PreToolUse"]
    assert [result.reason for result in results] == ["first", "second"]
    assert results[1].continue_ is False


def test_local_hook_registry_dispatch_aggregates_block_and_context() -> None:
    registry = LocalHookRegistry()

    registry.register(
        "UserPromptSubmit",
        lambda _payload: HookResult(additional_context="ctx-1"),
    )
    registry.register(
        "UserPromptSubmit",
        lambda _payload: HookResult.model_validate(
            {
                "continue": False,
                "decision": "block",
                "reason": "blocked",
                "additional_context": "ctx-2",
            }
        ),
    )

    outcome = registry.dispatch(
        HookPayload(event="UserPromptSubmit", data={"message": "hello"})
    )

    assert isinstance(outcome, HookDispatchOutcome)
    assert outcome.blocked is True
    assert outcome.reason == "blocked"
    assert outcome.additional_context == ("ctx-1", "ctx-2")


def test_hook_result_schema_rejects_unknown_fields_and_decisions() -> None:
    with pytest.raises(ValidationError):
        HookResult.model_validate({"decision": "maybe"})
    with pytest.raises(ValidationError):
        HookResult.model_validate({"continue": True, "extra": "nope"})


def test_hook_payload_rejects_unknown_events() -> None:
    with pytest.raises(ValidationError):
        HookPayload.model_validate({"event": "UnknownEvent", "data": {}})


def test_runtime_hook_dispatch_emits_start_and_terminal_event_metadata() -> None:
    registry = LocalHookRegistry()
    registry.register(
        "UserPromptSubmit",
        lambda _payload: HookResult.model_validate(
            {"continue": False, "decision": "block", "reason": "blocked"}
        ),
    )
    sink = InMemoryEventSink()
    invocation = RuntimeInvocation(
        context=RuntimeContext(
            session_id="session-1",
            workdir=Path.cwd(),
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="test-agent",
            skill_dir=Path.cwd() / "skills",
            event_sink=sink,
            hook_registry=registry,
        ),
        config={"configurable": {"thread_id": "session-1"}},
    )

    outcome = dispatch_runtime_hook(
        invocation,
        event="UserPromptSubmit",
        data={"message": "hello"},
    )
    events = sink.snapshot()

    assert outcome.blocked is True
    assert [event.kind for event in events] == ["hook_start", "hook_blocked"]
    assert events[0].metadata == {
        "source": "hooks",
        "hook_event": "UserPromptSubmit",
        "blocked": False,
        "reason": None,
    }
    assert events[1].metadata == {
        "source": "hooks",
        "hook_event": "UserPromptSubmit",
        "blocked": True,
        "reason": "blocked",
    }


def test_blocked_runtime_hook_appends_session_evidence(tmp_path: Path) -> None:
    store = JsonlSessionStore(tmp_path / "sessions")
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_context = store.create_session(workdir=workdir, session_id="session-1")
    store.append_message(session_context, role="user", content="start")
    registry = LocalHookRegistry()
    registry.register(
        "UserPromptSubmit",
        lambda _payload: HookResult.model_validate(
            {"continue": False, "decision": "block", "reason": "blocked"}
        ),
    )
    invocation = RuntimeInvocation(
        context=RuntimeContext(
            session_id="session-1",
            workdir=workdir,
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="test-agent",
            skill_dir=workdir / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=registry,
            session_context=session_context,
        ),
        config={"configurable": {"thread_id": "session-1"}},
    )

    dispatch_runtime_hook(
        invocation,
        event="UserPromptSubmit",
        data={"message": "hello"},
    )
    loaded = store.load_session(session_id="session-1", workdir=workdir)
    rendered = render_recovery_brief(build_recovery_brief(loaded))

    assert loaded.summary.evidence_count == 1
    assert loaded.evidence[0].kind == "runtime_event"
    assert loaded.evidence[0].status == "blocked"
    assert loaded.evidence[0].metadata == {
        "event_kind": "hook_blocked",
        "source": "hooks",
        "hook_event": "UserPromptSubmit",
        "blocked": True,
    }
    assert "[blocked] runtime_event: Hook UserPromptSubmit blocked execution." in rendered


def test_context_hook_dispatch_emits_start_and_complete_event_metadata() -> None:
    registry = LocalHookRegistry()
    registry.register("PreToolUse", lambda _payload: HookResult(reason="ok"))
    sink = InMemoryEventSink()
    context = RuntimeContext(
        session_id="session-1",
        workdir=Path.cwd(),
        trusted_workdirs=(),
        entrypoint="test",
        agent_name="test-agent",
        skill_dir=Path.cwd() / "skills",
        event_sink=sink,
        hook_registry=registry,
    )

    outcome = dispatch_context_hook(
        context=context,
        session_id="session-1",
        event="PreToolUse",
        data={"tool": "read_file"},
    )
    events = sink.snapshot()

    assert outcome is not None
    assert outcome.blocked is False
    assert [event.kind for event in events] == ["hook_start", "hook_complete"]
    assert events[0].metadata == {
        "source": "hooks",
        "hook_event": "PreToolUse",
        "blocked": False,
    }
    assert events[1].metadata == {
        "source": "hooks",
        "hook_event": "PreToolUse",
        "blocked": False,
        "reason": None,
    }
