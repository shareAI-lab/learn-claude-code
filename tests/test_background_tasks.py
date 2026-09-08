import copy
import importlib.util
import os
import subprocess
import sys
import tempfile
import threading
import time
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "s11_background_tasks" / "code.py"


def load_lesson(workdir: Path):
    fake_anthropic = types.ModuleType("anthropic")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_dotenv = types.ModuleType("dotenv")
    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None

    previous_modules = {
        "anthropic": sys.modules.get("anthropic"),
        "dotenv": sys.modules.get("dotenv"),
    }
    previous_cwd = Path.cwd()
    previous_model = os.environ.get("MODEL_ID")
    module_name = f"background_tasks_test_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, LESSON)
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


def wait_until(predicate, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_windows_process_cleanup_avoids_posix_only_signals():
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))
        calls = []

        class RunningProcess:
            def poll(self):
                return None

            def terminate(self):
                calls.append("terminate")

            def wait(self, timeout):
                calls.append(("wait", timeout))
                return 0

            def kill(self):
                calls.append("kill")

        original_os_name = lesson.os.name
        try:
            lesson.os.name = "nt"
            lesson._stop_process_group(RunningProcess())
        finally:
            lesson.os.name = original_os_name

        assert calls == ["terminate", ("wait", 0.2)]

        calls.clear()

        class StubbornProcess(RunningProcess):
            def wait(self, timeout):
                calls.append(("wait", timeout))
                raise subprocess.TimeoutExpired("test", timeout)

        try:
            lesson.os.name = "nt"
            lesson._stop_process_group(StubbornProcess())
        finally:
            lesson.os.name = original_os_name

        assert calls == ["terminate", ("wait", 0.2), "kill"]


def test_s11_keeps_the_s04_kernel_and_adds_one_bash_option():
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))

        assert {tool["name"] for tool in lesson.TOOLS} == {
            "bash", "read_file", "write_file", "edit_file", "glob"
        }
        bash = next(tool for tool in lesson.TOOLS if tool["name"] == "bash")
        assert "run_in_background" in bash["input_schema"]["properties"]
        assert set(lesson.HOOKS) == {
            "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"
        }
        assert not hasattr(lesson, "Task")
        assert not hasattr(lesson, "MEMORY_DIR")


def test_background_execution_requires_an_explicit_bash_flag():
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))

        assert not lesson.should_run_background("bash", {"command": "npm install"})
        assert lesson.should_run_background(
            "bash", {"command": "printf ready", "run_in_background": True}
        )
        assert not lesson.should_run_background(
            "write_file", {"run_in_background": True}
        )


def test_background_bash_passes_permission_before_dispatch():
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))
        block = types.SimpleNamespace(
            id="tool_denied",
            name="bash",
            input={"command": "rm -rf /tmp/example", "run_in_background": True},
            type="tool_use",
        )
        responses = [
            types.SimpleNamespace(stop_reason="tool_use", content=[block]),
            types.SimpleNamespace(
                stop_reason="end_turn",
                content=[types.SimpleNamespace(type="text", text="Denied.")],
            ),
        ]
        lesson.client.messages.create = lambda **_: responses.pop(0)
        history = [{"role": "user", "content": "Delete the directory"}]

        lesson.agent_loop(history)

        assert not lesson.background_tasks
        result = history[2]["content"][0]
        assert result["type"] == "tool_result"
        assert "Permission denied" in result["content"]


def test_completed_result_is_collected_once_before_a_later_llm_call():
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))
        worker_started = threading.Event()
        release_worker = threading.Event()

        def controlled_command(command):
            assert command == "controlled command"
            worker_started.set()
            assert release_worker.wait(timeout=2)
            return "ready", 0

        lesson._run_bash_process = controlled_command
        block = types.SimpleNamespace(
            id="tool_ready",
            name="bash",
            input={"command": "controlled command", "run_in_background": True},
        )
        start_result = lesson.execute_tool(block)
        task_id = next(iter(lesson.background_tasks))

        assert worker_started.wait(timeout=2)
        assert task_id == "bg_0001"
        assert task_id in start_result
        assert lesson.background_tasks[task_id]["status"] == "running"

        release_worker.set()
        assert wait_until(
            lambda: lesson.background_tasks[task_id]["status"] == "completed"
        )

        seen_messages = []

        def respond(**kwargs):
            seen_messages.append(copy.deepcopy(kwargs["messages"]))
            return types.SimpleNamespace(
                stop_reason="end_turn",
                content=[types.SimpleNamespace(type="text", text="Received.")],
            )

        lesson.client.messages.create = respond
        history = [{"role": "user", "content": "Continue"}]
        lesson.agent_loop(history)

        delivered = str(seen_messages[0])
        assert "<task_notification>" in delivered
        assert f"<task_id>{task_id}</task_id>" in delivered
        assert "<status>completed</status>" in delivered
        assert "ready" in delivered
        assert lesson.collect_background_results() == []


def test_s11_code_is_ascii():
    LESSON.read_text(encoding="ascii")
