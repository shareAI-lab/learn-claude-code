from __future__ import annotations

from typing import Any, cast
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from coding_deepgent.subagents import (
    DEFAULT_CHILD_TOOLS,
    FORBIDDEN_CHILD_TOOLS,
    RunSubagentInput,
    child_tool_allowlist,
    run_subagent,
    run_subagent_task,
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
    calls: list[tuple[str, tuple[str, ...], str]] = []

    def factory(agent_type, tools):
        def child(task: str) -> str:
            calls.append((agent_type, tuple(tools), task))
            return f"done:{task}"

        return child

    result = run_subagent_task(
        task="inspect", agent_type="verifier", child_agent_factory=factory
    )

    assert result.content == "done:inspect"
    assert calls == [
        (
            "verifier",
            ("read_file", "glob", "grep", "task_get", "task_list", "plan_get"),
            "inspect",
        )
    ]


def test_run_subagent_tool_schema_rejects_runtime_creep_fields() -> None:
    runtime = SimpleNamespace()
    assert "Subagent general accepted" in cast(Any, run_subagent).func(
        "inspect", runtime
    )
    schema = cast(Any, run_subagent.tool_call_schema).model_json_schema()
    assert set(schema["properties"]) == {"task", "agent_type", "max_turns"}

    with pytest.raises(ValidationError):
        RunSubagentInput.model_validate(
            {"task": "x", "background": True, "runtime": runtime}
        )
