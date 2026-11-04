import importlib.util
import os
import sys
import tempfile
import time
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LESSONS = tuple(
    ROOT / chapter / "code.py"
    for chapter in (
        "s01_agent_loop",
        "s02_tool_use",
        "s03_permission",
        "s04_hooks",
        "s05_todo_write",
        "s06_subagent",
        "s07_skill_loading",
        "s08_context_compact",
        "s09_memory",
        "s10_task_system",
        "s11_background_tasks",
        "s12_cron_scheduler",
        "s13_agent_teams",
        "s14_mcp_plugin",
    )
)
INTEGRATED_LESSON = ROOT / "s15_integrated_harness" / "code.py"
GOAL_LESSON = ROOT / "s17_goal_loop" / "code.py"
GLOB_LESSONS = (*LESSONS[1:], INTEGRATED_LESSON, GOAL_LESSON)


class FakeMessagesApi:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        if not self.responses:
            raise AssertionError("agent loop requested another model turn")
        return self.responses.pop(0)


def load_lesson(workdir: Path, lesson_path: Path):
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = FakeMessagesApi([])

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None

    previous_modules = {
        "anthropic": sys.modules.get("anthropic"),
        "dotenv": sys.modules.get("dotenv"),
    }
    previous_cwd = Path.cwd()
    previous_model = os.environ.get("MODEL_ID")
    module_name = f"agent_loop_boundary_{lesson_path.parent.name}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, lesson_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    sys.modules[module_name] = module
    try:
        os.chdir(workdir)
        os.environ["MODEL_ID"] = "test-model"
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous_cwd)
        if previous_model is None:
            os.environ.pop("MODEL_ID", None)
        else:
            os.environ["MODEL_ID"] = previous_model
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
        sys.modules.pop(module_name, None)


def empty_tool_use_response(content=None):
    return types.SimpleNamespace(
        stop_reason="tool_use",
        content=(
            [types.SimpleNamespace(type="text", text="")]
            if content is None else content
        ),
    )


def disable_lesson_side_effects(lesson):
    if hasattr(lesson, "trigger_hooks"):
        lesson.trigger_hooks = lambda *_args, **_kwargs: None
    if hasattr(lesson, "inject_background_results"):
        lesson.inject_background_results = lambda _messages: None
    if hasattr(lesson, "consume_cron_queue"):
        lesson.consume_cron_queue = lambda: []
    if hasattr(lesson, "extract_memories"):
        lesson.extract_memories = lambda _messages: False
    if hasattr(lesson, "release_completed_assignment"):
        lesson.release_completed_assignment = lambda _owner: None
    if hasattr(lesson, "assemble_tool_pool"):
        lesson.assemble_tool_pool = lambda: ([], {})
    if hasattr(lesson, "assemble_system_prompt"):
        lesson.assemble_system_prompt = lambda: "test system"
    if hasattr(lesson, "COMPACTOR"):
        lesson.COMPACTOR.prepare = lambda messages, _request: messages


def use_successful_bash_handler(lesson):
    if hasattr(lesson, "run_bash"):
        lesson.run_bash = lambda *_args, **_kwargs: "tool output"
    if hasattr(lesson, "check_permission"):
        lesson.check_permission = lambda _block: True
    if hasattr(lesson, "execute_tool"):
        lesson.execute_tool = lambda *_args, **_kwargs: "tool output"
    if hasattr(lesson, "TOOL_HANDLERS"):
        lesson.TOOL_HANDLERS["bash"] = lambda **_kwargs: "tool output"


def bash_tool_call():
    return types.SimpleNamespace(
        type="tool_use",
        id="tool_1",
        name="bash",
        input={"command": "true"},
    )


def run_glob_tool(lesson, workdir: Path, pattern: str) -> str:
    if hasattr(lesson, "run_glob"):
        return lesson.run_glob(pattern)
    session = object.__new__(lesson.AgentSession)
    session.workdir = workdir.resolve()
    return session._run_tool("glob", {"pattern": pattern})


def run_text_tool(lesson, workdir: Path, name: str, arguments: dict) -> str:
    handlers = {
        "read_file": "run_read",
        "write_file": "run_write",
        "edit_file": "run_edit",
    }
    handler = getattr(lesson, handlers[name], None)
    if handler is not None:
        return handler(**arguments)
    session = object.__new__(lesson.AgentSession)
    session.workdir = workdir.resolve()
    return session._run_tool(name, arguments)


@pytest.mark.parametrize("lesson_path", GLOB_LESSONS,
                         ids=lambda path: path.parent.name)
def test_text_tools_use_utf8_for_non_ascii_content(
        tmp_path: Path, lesson_path: Path):
    lesson = load_lesson(tmp_path, lesson_path)
    path = tmp_path / "note.txt"
    original = "你好，UTF-8\n"

    written = run_text_tool(
        lesson, tmp_path, "write_file", {"path": path.name, "content": original}
    )
    read = run_text_tool(
        lesson, tmp_path, "read_file", {"path": path.name}
    )
    edited = run_text_tool(
        lesson,
        tmp_path,
        "edit_file",
        {"path": path.name, "old_text": "UTF-8", "new_text": "跨平台"},
    )

    assert not written.startswith("Error:")
    assert read == original.rstrip()
    assert not edited.startswith("Error:")
    assert path.read_bytes() == "你好，跨平台\n".encode("utf-8")


@pytest.mark.parametrize("lesson_path", GLOB_LESSONS,
                         ids=lambda path: path.parent.name)
def test_glob_double_star_matches_files_at_any_depth(
        tmp_path: Path, lesson_path: Path):
    (tmp_path / "root.py").write_text("")
    (tmp_path / "one" / "two").mkdir(parents=True)
    (tmp_path / "one" / "one.py").write_text("")
    (tmp_path / "one" / "two" / "deep.py").write_text("")
    lesson = load_lesson(tmp_path, lesson_path)

    matches = set(run_glob_tool(lesson, tmp_path, "**/*.py").splitlines())

    assert matches == {"root.py", "one/one.py", "one/two/deep.py"}


@pytest.mark.parametrize("lesson_path", GLOB_LESSONS,
                         ids=lambda path: path.parent.name)
def test_glob_caps_large_result_sets(tmp_path: Path, lesson_path: Path):
    for index in range(205):
        (tmp_path / f"file-{index:03}.txt").write_text("")
    lesson = load_lesson(tmp_path, lesson_path)

    lines = run_glob_tool(lesson, tmp_path, "*.txt").splitlines()

    assert len(lines) == 201
    assert lines[-1] == "... (more matches omitted; narrow the pattern)"


@pytest.mark.parametrize("lesson_path", LESSONS, ids=lambda path: path.parent.name)
@pytest.mark.parametrize("content", ([], None), ids=("empty-content", "empty-text"))
def test_parent_loop_does_not_append_an_empty_tool_result_turn(
        lesson_path: Path, content):
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp), lesson_path)
        disable_lesson_side_effects(lesson)
        api = FakeMessagesApi([empty_tool_use_response(content)])
        lesson.client = types.SimpleNamespace(messages=api)
        messages = [{"role": "user", "content": "hello"}]

        if lesson_path.parent.name == "s08_context_compact":
            lesson.agent_loop(messages, "hello")
        else:
            lesson.agent_loop(messages)

        assert api.calls == 1
        assert messages[-1]["role"] == "assistant"
        assert not any(
            message.get("role") == "user" and message.get("content") == []
            for message in messages
        )


@pytest.mark.parametrize("lesson_path", LESSONS, ids=lambda path: path.parent.name)
def test_parent_loop_executes_a_real_tool_call_even_if_stop_reason_disagrees(
        lesson_path: Path):
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp), lesson_path)
        disable_lesson_side_effects(lesson)
        use_successful_bash_handler(lesson)
        api = FakeMessagesApi([
            types.SimpleNamespace(
                stop_reason="end_turn",
                content=[bash_tool_call()],
            ),
            types.SimpleNamespace(
                stop_reason="end_turn",
                content=[types.SimpleNamespace(type="text", text="done")],
            ),
        ])
        lesson.client = types.SimpleNamespace(messages=api)
        messages = [{"role": "user", "content": "hello"}]

        if lesson_path.parent.name == "s08_context_compact":
            lesson.agent_loop(messages, "hello")
        else:
            lesson.agent_loop(messages)

        assert api.calls == 2
        tool_result_turns = [
            message for message in messages
            if message.get("role") == "user"
            and isinstance(message.get("content"), list)
        ]
        assert len(tool_result_turns) == 1
        assert tool_result_turns[0]["content"][0]["tool_use_id"] == "tool_1"


def test_subagent_stops_without_an_empty_tool_result_turn():
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp), ROOT / "s06_subagent" / "code.py")
        disable_lesson_side_effects(lesson)
        api = FakeMessagesApi([empty_tool_use_response()])
        lesson.client = types.SimpleNamespace(messages=api)

        assert lesson.run_subagent("inspect the repository") == "(no summary)"
        assert api.calls == 1


def test_subagent_still_executes_a_real_tool_call_with_text_present():
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp), ROOT / "s06_subagent" / "code.py")
        disable_lesson_side_effects(lesson)
        tool_call = types.SimpleNamespace(
            type="tool_use",
            id="tool_1",
            name="read_file",
            input={"path": "README.md"},
        )
        api = FakeMessagesApi([
            types.SimpleNamespace(
                stop_reason="end_turn",
                content=[types.SimpleNamespace(type="text", text=""), tool_call],
            ),
            types.SimpleNamespace(
                stop_reason="end_turn",
                content=[types.SimpleNamespace(type="text", text="done")],
            ),
        ])
        lesson.client = types.SimpleNamespace(messages=api)
        lesson.execute_tool = lambda _block, _handlers: "tool output"

        assert lesson.run_subagent("inspect the repository") == "done"
        assert api.calls == 2


def test_s13_teammate_does_not_continue_with_an_empty_tool_result_turn():
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp), ROOT / "s13_agent_teams" / "code.py")
        api = FakeMessagesApi([empty_tool_use_response()])
        lesson.client = types.SimpleNamespace(messages=api)
        runtime = lesson.TeammateRuntime(
            "alice", "reviewer", "inspect the repository", None, False
        )

        assert runtime.work() == "idle"
        assert api.calls == 1
        assert not any(
            message.get("role") == "user" and message.get("content") == []
            for message in runtime.messages
        )


def test_s13_teammate_executes_a_real_tool_call_when_stop_reason_disagrees():
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp), ROOT / "s13_agent_teams" / "code.py")
        api = FakeMessagesApi([
            types.SimpleNamespace(
                stop_reason="end_turn",
                content=[bash_tool_call()],
            )
        ])
        lesson.client = types.SimpleNamespace(messages=api)
        lesson._run_teammate_tool = lambda *_args: "tool output"
        runtime = lesson.TeammateRuntime(
            "alice", "reviewer", "inspect the repository", None, False
        )

        assert runtime.work() == "continue"
        assert api.calls == 1
        assert runtime.messages[-1]["content"][0]["tool_use_id"] == "tool_1"


def stop_s15_teammate_when_idle(lesson, name: str):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        with lesson.team_lock:
            state = lesson.active_teammates.get(name)
        if state == "idle":
            lesson.run_request_shutdown(name)
            break
        if state is None:
            break
        time.sleep(0.01)

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        with lesson.team_lock:
            if name not in lesson.active_teammates:
                return
        time.sleep(0.01)


def test_s15_teammate_does_not_request_another_turn_for_empty_tool_use():
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp), INTEGRATED_LESSON)
        api = FakeMessagesApi([empty_tool_use_response()])
        lesson.client = types.SimpleNamespace(messages=api)

        lesson.spawn_teammate_thread("alice", "reviewer", "inspect the repository")
        stop_s15_teammate_when_idle(lesson, "alice")

        assert api.calls == 1
        with lesson.team_lock:
            assert "alice" not in lesson.active_teammates


def test_s15_teammate_executes_a_real_tool_call_when_stop_reason_disagrees():
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp), INTEGRATED_LESSON)
        api = FakeMessagesApi([
            types.SimpleNamespace(
                stop_reason="end_turn",
                content=[bash_tool_call()],
            ),
            types.SimpleNamespace(
                stop_reason="end_turn",
                content=[types.SimpleNamespace(type="text", text="done")],
            ),
        ])
        lesson.client = types.SimpleNamespace(messages=api)
        calls = []
        lesson._run_teammate_tool = lambda *_args: calls.append("bash") or "ok"

        lesson.spawn_teammate_thread("alice", "reviewer", "inspect the repository")
        stop_s15_teammate_when_idle(lesson, "alice")

        assert api.calls == 2
        assert calls == ["bash"]
        with lesson.team_lock:
            assert "alice" not in lesson.active_teammates
