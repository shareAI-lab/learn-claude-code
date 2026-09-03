import importlib.util
import os
import sys
import threading
import time
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "s15_integrated_harness" / "code.py"


def load_lesson(workdir: Path):
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None

    previous_modules = {
        "anthropic": sys.modules.get("anthropic"),
        "dotenv": sys.modules.get("dotenv"),
    }
    previous_cwd = Path.cwd()
    previous_model = os.environ.get("MODEL_ID")
    module_name = f"s15_readonly_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, LESSON)
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


def make_block(command: str):
    return types.SimpleNamespace(name="bash", input={"command": command})


READ_ONLY_CASES = (
    "ls",
    "ls -la",
    "cat notes.md",
    "head -5 code.py",
    "grep -rn TODO src",
    "pwd",
    "echo hello",
    "echo 'a > b && c'",
    "git status",
    "git log --oneline -5",
    "git diff --stat",
    "find . -name '*.py'",
    "cat a.txt | wc -l",
    "echo one && pwd",
    "cat a; cat b",
    "/bin/ls -la",
    "command cat f.txt",
    "FOO=bar ls",
)

PROMPT_CASES = (
    ("rm file.txt", "Permission denied by user"),
    ("echo hi > out.txt", "Permission denied by user"),
    ("ls >> log.txt", "Permission denied by user"),
    ("git push origin main", "Permission denied by user"),
    ("find . -name x -delete", "Permission denied by user"),
    ("sort -o out.txt in.txt", "Permission denied by user"),
    ("cat a; rm b", "Permission denied by user"),
    ("python script.py", "Permission denied by user"),
    ("echo $(whoami)", "Permission denied by user"),
    ("sudo ls", "Permission denied: 'sudo' is on the deny list"),
)


@pytest.fixture()
def lesson(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = load_lesson(tmp_path)
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt="": (_ for _ in ()).throw(
            AssertionError("permission prompt opened for a read-only command")
        ),
    )
    return module


@pytest.mark.parametrize("command", READ_ONLY_CASES)
def test_read_only_commands_run_without_a_prompt(lesson, command: str):
    assert lesson.permission_hook(make_block(command)) is None


@pytest.mark.parametrize("command, expected", PROMPT_CASES)
def test_other_commands_still_ask_and_fail_closed(
    lesson, monkeypatch: pytest.MonkeyPatch, command: str, expected: str
):
    monkeypatch.setattr("builtins.input", lambda _prompt="": "n")
    result = lesson.permission_hook(make_block(command))
    assert result == expected


def test_read_only_commands_are_allowed_in_asynchronous_turns(lesson):
    outcome = {}

    def worker():
        outcome["result"] = lesson.permission_hook(make_block("ls -la"))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert outcome["result"] is None


def test_mutable_commands_still_fail_closed_in_asynchronous_turns(lesson):
    outcome = {}

    def worker():
        outcome["result"] = lesson.permission_hook(make_block("rm file.txt"))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert "asynchronous turn" in outcome["result"]
