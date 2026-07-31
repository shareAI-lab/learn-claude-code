import builtins
import runpy
import sys
import types
from pathlib import Path

import pytest


BASE_AGENT = (
    Path(__file__).resolve().parents[1]
    / "homework"
    / "BaseAgent.py"
)


def load_baseagent(monkeypatch):
    """Load BaseAgent without creating a real Anthropic client."""
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(
                create=None,
                stream=None,
            )

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)
    monkeypatch.setenv("MODEL_ID", "dummy")
    monkeypatch.delenv("FALLBACK_MODEL_ID", raising=False)

    namespace = runpy.run_path(
        str(BASE_AGENT),
        run_name="not_main",
    )
    return namespace["agent_loop"].__globals__


@pytest.fixture
def baseagent(monkeypatch):
    return load_baseagent(monkeypatch)


def test_todo_persistence_and_resume_apis_are_removed(baseagent):
    for name in (
        "TODO_FILE",
        "save_todos",
        "read_saved_todos",
        "all_todos_completed",
        "ask_resume_todos",
    ):
        assert name not in baseagent


def test_todo_write_does_not_touch_legacy_todo_file(
    baseagent,
    monkeypatch,
    tmp_path,
):
    legacy_file = tmp_path / ".todo.json"
    legacy_file.write_text("legacy-state", encoding="utf-8")

    if "TODO_FILE" in baseagent:
        monkeypatch.setitem(
            baseagent,
            "TODO_FILE",
            legacy_file,
        )

    result = baseagent["run_todo_write"]([{
        "content": "current session step",
        "status": "in_progress",
    }])

    assert result == "Updated 1 tasks"
    assert legacy_file.read_text(encoding="utf-8") == "legacy-state"


def test_todos_remain_available_across_turns_in_one_process(
    baseagent,
):
    first_plan = [{
        "content": "inspect files",
        "status": "completed",
    }]
    latest_plan = [
        {
            "content": "modify agent loop",
            "status": "in_progress",
        },
        {
            "content": "run tests",
            "status": "pending",
        },
    ]

    assert baseagent["run_todo_write"](first_plan) == (
        "Updated 1 tasks"
    )
    assert baseagent["run_todo_write"](latest_plan) == (
        "Updated 2 tasks"
    )

    assert baseagent["CURRENT_TODOS"] == latest_plan
    formatted = baseagent["format_current_todos"]()
    assert "modify agent loop" in formatted
    assert "run tests" in formatted
    assert "inspect files" not in formatted

    context = baseagent["update_context"]({}, [])
    assert context["todos"] == formatted


def test_loading_baseagent_again_starts_with_empty_todos(
    monkeypatch,
):
    first_process = load_baseagent(monkeypatch)
    plan = [{
        "content": "only in first process",
        "status": "pending",
    }]
    first_process["run_todo_write"](plan)

    second_process = load_baseagent(monkeypatch)

    assert first_process["CURRENT_TODOS"] == plan
    assert second_process["CURRENT_TODOS"] == []
    assert second_process["format_current_todos"]() == ""


def test_invalid_todo_update_preserves_current_plan(baseagent):
    current_plan = [{
        "content": "keep this",
        "status": "in_progress",
    }]
    baseagent["run_todo_write"](current_plan)

    result = baseagent["run_todo_write"]([{
        "content": "invalid update",
        "status": "unknown",
    }])

    assert result.startswith("Error:")
    assert baseagent["CURRENT_TODOS"] == current_plan


def test_main_does_not_run_an_automatic_resume_turn(
    baseagent,
    monkeypatch,
):
    turns = []

    if "ask_resume_todos" in baseagent:
        monkeypatch.setitem(
            baseagent,
            "ask_resume_todos",
            lambda: "automatic resume",
        )

    def record_turn(history, content, context):
        turns.append(content)
        return context

    monkeypatch.setitem(baseagent, "run_agent_turn", record_turn)
    monkeypatch.setattr(builtins, "input", lambda _prompt: "q")

    baseagent["main"]()

    assert turns == []


def test_todo_tool_contract_remains_registered(baseagent):
    schemas = {
        tool["name"]: tool
        for tool in baseagent["BUILTIN_TOOLS"]
    }

    assert "todo_write" in schemas
    assert schemas["todo_write"]["input_schema"]["required"] == [
        "todos"
    ]
    assert baseagent["BUILTIN_HANDLERS"]["todo_write"] is (
        baseagent["run_todo_write"]
    )
