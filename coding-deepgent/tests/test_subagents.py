from __future__ import annotations

from typing import Any, cast
from types import SimpleNamespace

import pytest
from langgraph.store.memory import InMemoryStore
from pydantic import ValidationError

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


def test_run_subagent_tool_returns_structured_verifier_result() -> None:
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
    assert "Verifier subagent accepted task synchronously" in result.content
