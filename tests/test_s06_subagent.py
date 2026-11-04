import builtins
import importlib.util
import os
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "s06_subagent" / "code.py"


def load_lesson(temp_cwd: Path):
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
    previous_model_id = os.environ.get("MODEL_ID")
    spec = importlib.util.spec_from_file_location("s06_subagent_test", LESSON)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {LESSON}")
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    try:
        os.chdir(temp_cwd)
        os.environ["MODEL_ID"] = "test-model"
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous_cwd)
        if previous_model_id is None:
            os.environ.pop("MODEL_ID", None)
        else:
            os.environ["MODEL_ID"] = previous_model_id
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def tool_block(name: str, tool_id: str, **tool_input):
    return types.SimpleNamespace(
        type="tool_use",
        id=tool_id,
        name=name,
        input=tool_input,
    )


def test_s06_is_kernel_plus_task():
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))

    base_names = {tool["name"] for tool in lesson.BASE_TOOLS}
    parent_names = {tool["name"] for tool in lesson.TOOLS}
    child_names = {tool["name"] for tool in lesson.SUB_TOOLS}

    assert base_names == {"bash", "read_file", "write_file", "edit_file", "glob"}
    assert parent_names == base_names | {"task"}
    assert child_names == base_names
    assert "todo_write" not in parent_names
    assert "task" not in child_names
    assert lesson.TASK_TOOL["input_schema"]["required"] == ["prompt"]
    assert lesson.large_output_hook in lesson.HOOKS["PostToolUse"]


def test_subagent_starts_with_fresh_messages_and_returns_final_text():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "note.txt").write_text("child input")
        lesson = load_lesson(root)
        calls = []
        responses = [
            types.SimpleNamespace(
                stop_reason="tool_use",
                content=[tool_block("read_file", "read_1", path="note.txt")],
            ),
            types.SimpleNamespace(
                stop_reason="end_turn",
                content=[types.SimpleNamespace(type="text", text="The note says child input.")],
            ),
        ]

        def create(**kwargs):
            calls.append({**kwargs, "messages": list(kwargs["messages"])})
            return responses.pop(0)

        lesson.client.messages.create = create
        result = lesson.run_subagent("Read note.txt and report its contents.")

    assert calls[0]["messages"] == [
        {"role": "user", "content": "Read note.txt and report its contents."}
    ]
    assert {tool["name"] for tool in calls[0]["tools"]} == {
        "bash", "read_file", "write_file", "edit_file", "glob",
    }
    assert result == "The note says child input."


def test_subagent_file_tools_keep_the_kernel_permission_boundary():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        lesson = load_lesson(root)
        outside = root.parent / "s06-outside.txt"
        block = tool_block(
            "write_file",
            "write_1",
            path=str(outside),
            content="not allowed",
        )

        with patch.object(builtins, "input", return_value="n"):
            result = lesson.execute_tool(block, lesson.SUB_HANDLERS)

        assert result == "Permission denied by user"
        assert not outside.exists()
