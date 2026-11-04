import importlib.util
import os
import sys
import time
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PERMISSION_LESSONS = tuple(
    ROOT / chapter / "code.py"
    for chapter in (
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
        "s17_goal_loop",
    )
)


def load_lesson(workdir: Path, lesson_path: Path):
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
    module_name = f"permission_words_{lesson_path.parent.name}_{time.time_ns()}"
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


def permission_result(lesson, block):
    if hasattr(lesson, "check_rules"):
        return lesson.check_rules(block.name, block.input)
    if hasattr(lesson, "permission_hook"):
        return lesson.permission_hook(block)

    goal = lesson.GoalController(evaluator=None)
    session = lesson.AgentSession(
        client=None,
        model="test-model",
        goal=goal,
        workdir=Path.cwd(),
    )
    return session._permission_hook(block)


COMMAND_CASES = (
    ("rm file.txt", True),
    ("/usr/bin/rm file.txt", True),
    ("command rm file.txt", True),
    ("DEL file.txt", True),
    ("echo ready; rm file.txt", True),
    ("echo ready && del file.txt", True),
    ("echo ready || RM file.txt", True),
    ("echo ready | del file.txt", True),
    ("echo ready & rm file.txt", True),
    ("(del file.txt)", True),
    ("rm; echo ready", True),
    ("model list", False),
    ("delimiter file.txt", False),
    ("echo del file.txt", False),
    ("echo; delimiter file.txt", False),
)


@pytest.mark.parametrize(
    "lesson_path", PERMISSION_LESSONS, ids=lambda path: path.parent.name
)
@pytest.mark.parametrize("command, expected", COMMAND_CASES)
def test_permission_command_words_cover_position_case_and_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lesson_path: Path,
    command: str,
    expected: bool,
) -> None:
    lesson = load_lesson(tmp_path, lesson_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    block = types.SimpleNamespace(name="bash", input={"command": command})

    result = permission_result(lesson, block)

    assert bool(result) is expected
