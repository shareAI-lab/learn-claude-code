from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from types import SimpleNamespace

import pytest
from langchain.messages import HumanMessage
from langgraph.store.memory import InMemoryStore
from pydantic import ValidationError

from coding_deepgent.hooks import LocalHookRegistry
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext
from coding_deepgent.sessions import JsonlSessionStore, build_recovery_brief, render_recovery_brief
from coding_deepgent.subagents import tools as subagent_tools
from coding_deepgent.subagents import (
    DEFAULT_CHILD_TOOLS,
    FORBIDDEN_CHILD_TOOLS,
    RunSubagentInput,
    VerifierSubagentResult,
    child_tool_allowlist,
    run_subagent,
    run_subagent_task,
)
from coding_deepgent.tasks import create_plan, create_task


def runtime_with_store(store: InMemoryStore) -> SimpleNamespace:
    return SimpleNamespace(store=store)


def runtime_with_context_and_store(store: InMemoryStore) -> SimpleNamespace:
    return SimpleNamespace(
        store=store,
        context=RuntimeContext(
            session_id="session-1",
            workdir=Path.cwd(),
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="coding-deepgent",
            skill_dir=Path.cwd() / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=LocalHookRegistry(),
        ),
        config={"configurable": {"thread_id": "session-1"}},
    )


def runtime_with_recorded_session(
    store: InMemoryStore,
    *,
    session_store: JsonlSessionStore,
    workdir: Path,
) -> SimpleNamespace:
    session_context = session_store.create_session(
        workdir=workdir,
        session_id="session-1",
        entrypoint="test",
    )
    session_store.append_message(session_context, role="user", content="start")
    return SimpleNamespace(
        store=store,
        context=RuntimeContext(
            session_id="session-1",
            workdir=workdir,
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="coding-deepgent",
            skill_dir=workdir / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=LocalHookRegistry(),
            session_context=session_context,
        ),
        config={"configurable": {"thread_id": "session-1"}},
    )


def test_subagent_allowlists_are_exact_and_exclude_mutating_tools() -> None:
    assert child_tool_allowlist("general") == DEFAULT_CHILD_TOOLS
    assert child_tool_allowlist("verifier") == (
        *DEFAULT_CHILD_TOOLS,
        "task_get",
        "task_list",
        "plan_get",
    )
    assert set(FORBIDDEN_CHILD_TOOLS).isdisjoint(child_tool_allowlist("verifier"))


def test_run_subagent_task_uses_fake_factory_synchronously() -> None:
    store = InMemoryStore()
    runtime = runtime_with_store(store)
    task = create_task(store, title="Implement feature")
    plan = create_plan(
        store,
        title="Verification plan",
        content="Inspect the feature output.",
        verification="Run pytest tests/test_subagents.py",
        task_ids=[task.id],
    )
    calls: list[tuple[str, tuple[str, ...], str]] = []

    def factory(agent_type, tools):
        def child(task: str) -> str:
            calls.append((agent_type, tuple(tools), task))
            return f"done:{task}"

        return child

    expected_task = "\n".join(
        [
            "Verifier task:",
            "inspect",
            "",
            f"Plan ID: {plan.id}",
            "Plan title: Verification plan",
            "Verification criteria: Run pytest tests/test_subagents.py",
            f"Referenced task IDs: {task.id}",
            "",
            "Plan content:",
            "Inspect the feature output.",
        ]
    )

    result = run_subagent_task(
        task="inspect",
        runtime=cast(Any, runtime),
        agent_type="verifier",
        plan_id=plan.id,
        child_agent_factory=factory,
    )

    assert result.content == f"done:{expected_task}"
    assert calls == [
        (
            "verifier",
            ("read_file", "glob", "grep", "task_get", "task_list", "plan_get"),
            expected_task,
        )
    ]


def test_run_subagent_tool_schema_rejects_runtime_creep_fields() -> None:
    runtime = SimpleNamespace()
    assert "Subagent general accepted" in cast(Any, run_subagent).func(
        "inspect", runtime
    )
    schema = cast(Any, run_subagent.tool_call_schema).model_json_schema()
    assert set(schema["properties"]) == {"task", "agent_type", "plan_id", "max_turns"}

    with pytest.raises(ValidationError):
        RunSubagentInput.model_validate(
            {"task": "x", "background": True, "runtime": runtime}
        )


def test_run_subagent_pressure_guard_blocks_high_pressure() -> None:
    runtime = SimpleNamespace(
        store=InMemoryStore(),
        state={"messages": [HumanMessage(content="x" * 5000)]},
        context=RuntimeContext(
            session_id="session-1",
            workdir=Path.cwd(),
            trusted_workdirs=(),
            entrypoint="test",
            agent_name="coding-deepgent",
            skill_dir=Path.cwd() / "skills",
            event_sink=InMemoryEventSink(),
            hook_registry=LocalHookRegistry(),
            model_context_window_tokens=1000,
            subagent_spawn_guard_ratio=0.5,
        ),
    )

    result = run_subagent_task(
        task="inspect",
        runtime=cast(Any, runtime),
    )

    assert result.content.startswith("Subagent spawn blocked")
    assert runtime.context.event_sink.snapshot()[0].kind == "subagent_spawn_guard"


def test_run_subagent_pressure_guard_records_evidence(tmp_path: Path) -> None:
    session_store = JsonlSessionStore(tmp_path / "sessions-store")
    runtime = runtime_with_recorded_session(
        InMemoryStore(),
        session_store=session_store,
        workdir=tmp_path,
    )
    runtime.state = {"messages": [HumanMessage(content="x" * 5000)]}
    runtime.context = RuntimeContext(
        session_id=runtime.context.session_id,
        workdir=runtime.context.workdir,
        trusted_workdirs=runtime.context.trusted_workdirs,
        entrypoint=runtime.context.entrypoint,
        agent_name=runtime.context.agent_name,
        skill_dir=runtime.context.skill_dir,
        event_sink=runtime.context.event_sink,
        hook_registry=runtime.context.hook_registry,
        session_context=runtime.context.session_context,
        model_context_window_tokens=1000,
        subagent_spawn_guard_ratio=0.5,
    )

    output = cast(Any, run_subagent).func("inspect", runtime)
    loaded = session_store.load_session(session_id="session-1", workdir=tmp_path)

    assert output.startswith("Subagent spawn blocked")
    assert loaded.evidence[0].kind == "runtime_event"
    assert loaded.evidence[0].metadata["event_kind"] == "subagent_spawn_guard"


def test_verifier_subagent_requires_plan_id() -> None:
    runtime = runtime_with_store(InMemoryStore())

    with pytest.raises(ValueError, match="plan_id"):
        cast(Any, run_subagent).func(
            "inspect",
            runtime,
            agent_type="verifier",
        )


def test_verifier_subagent_requires_task_store() -> None:
    runtime = SimpleNamespace(store=None)

    with pytest.raises(RuntimeError, match="task store"):
        cast(Any, run_subagent).func(
            "inspect",
            runtime,
            agent_type="verifier",
            plan_id="plan-123",
        )


def test_verifier_subagent_rejects_unknown_plan() -> None:
    runtime = runtime_with_store(InMemoryStore())

    with pytest.raises(KeyError, match="Unknown plan"):
        cast(Any, run_subagent).func(
            "inspect",
            runtime,
            agent_type="verifier",
            plan_id="plan-missing",
        )


def test_run_subagent_task_verifier_executes_real_child_agent(monkeypatch) -> None:
    store = InMemoryStore()
    runtime = runtime_with_context_and_store(store)
    task = create_task(store, title="Implement feature")
    plan = create_plan(
        store,
        title="Verification plan",
        content="Run the targeted tests and inspect durable task state.",
        verification="Run pytest tests/test_subagents.py",
        task_ids=[task.id],
    )
    captured: dict[str, Any] = {}

    class FakeChildAgent:
        def invoke(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            captured["payload"] = payload
            captured["invoke_kwargs"] = kwargs
            return {"messages": [{"role": "assistant", "content": "VERDICT: PASS"}]}

    def fake_create_agent(**kwargs: Any) -> FakeChildAgent:
        captured["agent_kwargs"] = kwargs
        return FakeChildAgent()

    monkeypatch.setattr(subagent_tools, "create_agent", fake_create_agent)
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda: object())

    result = run_subagent_task(
        task="Verify the implementation",
        runtime=cast(Any, runtime),
        agent_type="verifier",
        plan_id=plan.id,
    )

    assert result.content == "VERDICT: PASS"
    assert [tool.name for tool in captured["agent_kwargs"]["tools"]] == [
        "read_file",
        "glob",
        "grep",
        "task_get",
        "task_list",
        "plan_get",
    ]
    assert "strictly read-only" in captured["agent_kwargs"]["system_prompt"]
    assert captured["agent_kwargs"]["store"] is store
    assert captured["agent_kwargs"]["name"] == "coding-deepgent-verifier"
    assert len(captured["agent_kwargs"]["middleware"]) == 1
    assert captured["payload"] == {
        "messages": [
            {
                "role": "user",
                "content": "\n".join(
                    [
                        "Verifier task:",
                        "Verify the implementation",
                        "",
                        f"Plan ID: {plan.id}",
                        "Plan title: Verification plan",
                        "Verification criteria: Run pytest tests/test_subagents.py",
                        f"Referenced task IDs: {task.id}",
                        "",
                        "Plan content:",
                        "Run the targeted tests and inspect durable task state.",
                    ]
                ),
            }
        ]
    }
    assert captured["invoke_kwargs"]["context"].entrypoint == "run_subagent:verifier"
    assert (
        captured["invoke_kwargs"]["config"]["configurable"]["thread_id"]
        == f"session-1:verifier:{plan.id}"
    )


def test_run_subagent_task_verifier_uses_durable_plan_payload() -> None:
    store = InMemoryStore()
    runtime = runtime_with_store(store)
    task = create_task(store, title="Implement feature")
    plan = create_plan(
        store,
        title="Verification plan",
        content="Run the targeted tests and inspect durable task state.",
        verification="Run pytest tests/test_subagents.py",
        task_ids=[task.id],
    )
    calls: list[tuple[str, tuple[str, ...], str]] = []

    def factory(agent_type, tools):
        def child(rendered_task: str) -> str:
            calls.append((agent_type, tuple(tools), rendered_task))
            return "VERDICT: PASS"

        return child

    result = run_subagent_task(
        task="Verify the implementation",
        runtime=cast(Any, runtime),
        agent_type="verifier",
        plan_id=plan.id,
        child_agent_factory=factory,
    )

    assert result.content == "VERDICT: PASS"
    assert result.plan_id == plan.id
    assert result.plan_title == "Verification plan"
    assert result.verification == "Run pytest tests/test_subagents.py"
    assert result.task_ids == (task.id,)
    assert calls == [
        (
            "verifier",
            ("read_file", "glob", "grep", "task_get", "task_list", "plan_get"),
            "\n".join(
                [
                    "Verifier task:",
                    "Verify the implementation",
                    "",
                    f"Plan ID: {plan.id}",
                    "Plan title: Verification plan",
                    "Verification criteria: Run pytest tests/test_subagents.py",
                    f"Referenced task IDs: {task.id}",
                    "",
                    "Plan content:",
                    "Run the targeted tests and inspect durable task state.",
                ]
            ),
        )
    ]


def test_run_subagent_tool_returns_structured_verifier_result(monkeypatch) -> None:
    store = InMemoryStore()
    runtime = runtime_with_context_and_store(store)
    task = create_task(store, title="Implement feature")
    plan = create_plan(
        store,
        title="Verification plan",
        content="Run the targeted tests and inspect durable task state.",
        verification="Run pytest tests/test_subagents.py",
        task_ids=[task.id],
    )

    monkeypatch.setattr(
        subagent_tools,
        "create_agent",
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [{"role": "assistant", "content": "VERDICT: PASS"}]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda: object())

    output = cast(Any, run_subagent).func(
        "Verify the implementation",
        runtime,
        agent_type="verifier",
        plan_id=plan.id,
    )
    result = VerifierSubagentResult.model_validate_json(output)

    assert result.agent_type == "verifier"
    assert result.plan_id == plan.id
    assert result.plan_title == "Verification plan"
    assert result.verification == "Run pytest tests/test_subagents.py"
    assert result.task_ids == [task.id]
    assert result.tool_allowlist == [
        "read_file",
        "glob",
        "grep",
        "task_get",
        "task_list",
        "plan_get",
    ]
    assert result.content == "VERDICT: PASS"


def test_verifier_verdict_helpers_map_status_and_summary() -> None:
    assert subagent_tools.verifier_verdict("Checked output\nVERDICT: PASS") == "PASS"
    assert subagent_tools.verifier_verdict("VERDICT: fail") == "FAIL"
    assert subagent_tools.verifier_verdict("VERDICT: PARTIAL") == "PARTIAL"
    assert subagent_tools.verifier_verdict("looks ok") is None
    assert (
        subagent_tools.verifier_evidence_summary(
            "Checked targeted tests.\nVERDICT: PASS", verdict="PASS"
        )
        == "Checked targeted tests."
    )
    assert (
        subagent_tools.verifier_evidence_summary("VERDICT: PASS", verdict="PASS")
        == "Verifier verdict: PASS"
    )


def test_run_subagent_tool_persists_verifier_evidence_roundtrip(
    monkeypatch, tmp_path: Path
) -> None:
    task_store = InMemoryStore()
    workdir = tmp_path / "repo"
    workdir.mkdir()
    session_store = JsonlSessionStore(tmp_path / "sessions")
    runtime = runtime_with_recorded_session(
        task_store,
        session_store=session_store,
        workdir=workdir,
    )
    task = create_task(task_store, title="Implement feature")
    plan = create_plan(
        task_store,
        title="Verification plan",
        content="Run the targeted tests and inspect durable task state.",
        verification="Run pytest coding-deepgent/tests/test_subagents.py",
        task_ids=[task.id],
    )

    monkeypatch.setattr(
        subagent_tools,
        "create_agent",
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "Checked targeted tests.\nVERDICT: FAIL",
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda: object())

    output = cast(Any, run_subagent).func(
        "Verify the implementation",
        runtime,
        agent_type="verifier",
        plan_id=plan.id,
    )
    result = VerifierSubagentResult.model_validate_json(output)
    loaded = session_store.load_session(session_id="session-1", workdir=workdir)
    rendered = render_recovery_brief(build_recovery_brief(loaded))

    assert result.content == "Checked targeted tests.\nVERDICT: FAIL"
    assert loaded.summary.evidence_count == 1
    assert loaded.evidence[0].kind == "verification"
    assert loaded.evidence[0].status == "failed"
    assert loaded.evidence[0].summary == "Checked targeted tests."
    assert loaded.evidence[0].subject == plan.id
    assert loaded.evidence[0].metadata == {
        "plan_id": plan.id,
        "plan_title": "Verification plan",
        "verdict": "FAIL",
        "parent_session_id": "session-1",
        "parent_thread_id": "session-1",
        "child_thread_id": f"session-1:verifier:{plan.id}",
        "verifier_agent_name": "coding-deepgent-verifier",
        "task_ids": [task.id],
        "tool_allowlist": [
            "read_file",
            "glob",
            "grep",
            "task_get",
            "task_list",
            "plan_get",
        ],
    }
    assert "[failed] verification: Checked targeted tests." in rendered


def test_run_subagent_tool_skips_verifier_evidence_without_recording_context(
    monkeypatch,
) -> None:
    store = InMemoryStore()
    runtime = runtime_with_context_and_store(store)
    task = create_task(store, title="Implement feature")
    plan = create_plan(
        store,
        title="Verification plan",
        content="Run the targeted tests and inspect durable task state.",
        verification="Run pytest coding-deepgent/tests/test_subagents.py",
        task_ids=[task.id],
    )

    monkeypatch.setattr(
        subagent_tools,
        "create_agent",
        lambda **_kwargs: SimpleNamespace(
            invoke=lambda payload, **kwargs: {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "Checked targeted tests.\nVERDICT: PASS",
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(subagent_tools, "build_openai_model", lambda: object())

    output = cast(Any, run_subagent).func(
        "Verify the implementation",
        runtime,
        agent_type="verifier",
        plan_id=plan.id,
    )
    result = VerifierSubagentResult.model_validate_json(output)

    assert result.content == "Checked targeted tests.\nVERDICT: PASS"
