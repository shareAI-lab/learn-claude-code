from homework.agent_app import bootstrap
from homework.agent_app.config import AppConfig
from homework.agent_app.core.context import build_context
from homework.agent_app.features import todos
from homework.agent_app.runtime import SessionState
from homework.agent_app.tools.registry import ToolRegistry


class FakeSDKClient:
    class Messages:
        def create(self, **_kwargs):
            raise AssertionError("no live request expected")

        def stream(self, **_kwargs):
            raise AssertionError("no live request expected")

    def __init__(self):
        self.messages = self.Messages()


def build_test_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "dummy")
    monkeypatch.delenv("FALLBACK_MODEL_ID", raising=False)
    return bootstrap.build_runtime(
        AppConfig.from_env(tmp_path),
        FakeSDKClient(),
    )


def test_todo_update_is_session_owned():
    session = SessionState()

    result = todos.run_todo_write(
        session,
        [{"content": "inspect", "status": "in_progress"}],
    )

    assert result == "Updated 1 tasks"
    assert session.todos == [{"content": "inspect", "status": "in_progress"}]


def test_todo_sessions_do_not_share_state():
    first = SessionState()
    second = SessionState()

    todos.run_todo_write(
        first,
        [{"content": "inspect", "status": "in_progress"}],
    )

    assert first.todos == [{"content": "inspect", "status": "in_progress"}]
    assert second.todos == []


def test_todo_persistence_and_resume_apis_are_not_part_of_owner_module():
    for name in (
        "TODO_FILE",
        "save_todos",
        "read_saved_todos",
        "all_todos_completed",
        "ask_resume_todos",
    ):
        assert not hasattr(todos, name)


def test_todo_write_does_not_touch_legacy_todo_file(tmp_path):
    legacy_file = tmp_path / ".todo.json"
    legacy_file.write_text("legacy-state", encoding="utf-8")
    session = SessionState()

    result = todos.run_todo_write(
        session,
        [{"content": "current session step", "status": "in_progress"}],
    )

    assert result == "Updated 1 tasks"
    assert legacy_file.read_text(encoding="utf-8") == "legacy-state"


def test_todos_remain_available_across_turns_in_one_runtime(
    tmp_path,
    monkeypatch,
):
    runtime = build_test_runtime(tmp_path, monkeypatch)
    first_plan = [{"content": "inspect files", "status": "completed"}]
    latest_plan = [
        {"content": "modify agent loop", "status": "in_progress"},
        {"content": "run tests", "status": "pending"},
    ]

    assert todos.run_todo_write(runtime.session, first_plan) == "Updated 1 tasks"
    assert todos.run_todo_write(runtime.session, latest_plan) == "Updated 2 tasks"

    assert runtime.session.todos == latest_plan
    formatted = todos.format_current_todos(runtime.session)
    assert "modify agent loop" in formatted
    assert "run tests" in formatted
    assert "inspect files" not in formatted

    tools, _ = runtime.tools.snapshot()
    context = build_context(runtime, tools)
    assert context["todos"] == formatted


def test_new_runtime_starts_with_empty_todos(tmp_path, monkeypatch):
    first = build_test_runtime(tmp_path / "first", monkeypatch)
    second = build_test_runtime(tmp_path / "second", monkeypatch)
    plan = [{"content": "only in first runtime", "status": "pending"}]
    todos.run_todo_write(first.session, plan)

    assert first.session.todos == plan
    assert second.session.todos == []
    assert todos.format_current_todos(second.session) == ""


def test_invalid_todo_update_preserves_current_plan():
    session = SessionState()
    current_plan = [{"content": "keep this", "status": "in_progress"}]
    todos.run_todo_write(session, current_plan)

    result = todos.run_todo_write(
        session,
        [{"content": "invalid update", "status": "unknown"}],
    )

    assert result.startswith("Error:")
    assert session.todos == current_plan


def test_runtime_todo_handler_is_bound_to_its_session(tmp_path, monkeypatch):
    first = build_test_runtime(tmp_path / "first", monkeypatch)
    second = build_test_runtime(tmp_path / "second", monkeypatch)
    _, first_handlers = first.tools.snapshot()
    _, second_handlers = second.tools.snapshot()

    assert first_handlers["todo_write"](
        [{"content": "runtime-local", "status": "pending"}]
    ) == "Updated 1 tasks"

    assert first.session.todos == [
        {"content": "runtime-local", "status": "pending"}
    ]
    assert second.session.todos == []
    assert first_handlers["todo_write"] is not second_handlers["todo_write"]


def test_todo_tool_contract_remains_registered():
    session = SessionState()
    registry = ToolRegistry()
    todos.register_todo_tools(registry, session)
    registered, handlers = registry.snapshot()
    schema = next(tool for tool in registered if tool["name"] == "todo_write")

    assert schema["input_schema"]["required"] == ["todos"]
    assert handlers["todo_write"](
        [{"content": "registered", "status": "pending"}]
    ) == "Updated 1 tasks"
    assert session.todos == [{"content": "registered", "status": "pending"}]
