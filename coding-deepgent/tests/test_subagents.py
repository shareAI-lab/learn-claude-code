from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from types import SimpleNamespace

import pytest
from langgraph.store.memory import InMemoryStore
from pydantic import ValidationError

from coding_deepgent.hooks import LocalHookRegistry
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext
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
