import builtins
import importlib.util
import sys
import types
from pathlib import Path

import pytest

from homework.agent_app.features.todos import run_todo_write
from homework.agent_app.runtime import SessionState


BASE_AGENT = (
    Path(__file__).resolve().parents[1]
    / "homework"
    / "BaseAgent.py"
)


class BaseAgentModule:
    def __init__(self, module):
        self.module = module

    def __getitem__(self, name):
        return getattr(self.module, name)

    def __setitem__(self, name, value):
        setattr(self.module, name, value)

    def __contains__(self, name):
        return hasattr(self.module, name)


def load_baseagent_module():
    spec = importlib.util.spec_from_file_location("_baseagent_todos", BASE_AGENT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return BaseAgentModule(module)


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

    return load_baseagent_module()


@pytest.fixture
def baseagent(monkeypatch):
    return load_baseagent(monkeypatch)


def test_todo_update_is_session_owned():
    session = SessionState()

    result = run_todo_write(
        session,
        [{"content": "inspect", "status": "in_progress"}],
    )

    assert result == "Updated 1 tasks"
    assert session.todos == [{"content": "inspect", "status": "in_progress"}]


def test_legacy_todo_alias_shares_session_state(baseagent):
    assert baseagent["CURRENT_TODOS"] is baseagent["SESSION_STATE"].todos

    baseagent["run_todo_write"]([
        {"content": "inspect", "status": "in_progress"},
    ])

    assert baseagent["CURRENT_TODOS"] is baseagent["SESSION_STATE"].todos


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

    baseagent["run_agent_turn"] = record_turn
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
