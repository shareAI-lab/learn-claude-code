import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
S08_MODULE_PATH = REPO_ROOT / "agents" / "s08_background_tasks.py"
S_FULL_MODULE_PATH = REPO_ROOT / "agents" / "s_full.py"


def load_agent_module(temp_cwd: Path, module_path: Path, module_name: str):
    fake_anthropic = types.ModuleType("anthropic")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_dotenv = types.ModuleType("dotenv")
    setattr(fake_anthropic, "Anthropic", FakeAnthropic)
    setattr(fake_dotenv, "load_dotenv", lambda override=True: None)

    previous_anthropic = sys.modules.get("anthropic")
    previous_dotenv = sys.modules.get("dotenv")
    previous_cwd = Path.cwd()
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    try:
        os.chdir(temp_cwd)
        os.environ.setdefault("MODEL_ID", "test-model")
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous_cwd)
        if previous_anthropic is None:
            sys.modules.pop("anthropic", None)
        else:
            sys.modules["anthropic"] = previous_anthropic
        if previous_dotenv is None:
            sys.modules.pop("dotenv", None)
        else:
            sys.modules["dotenv"] = previous_dotenv


def load_s08_module(temp_cwd: Path):
    return load_agent_module(
        temp_cwd,
        S08_MODULE_PATH,
        "s08_background_tasks_under_test",
    )


def load_s_full_module(temp_cwd: Path):
    return load_agent_module(temp_cwd, S_FULL_MODULE_PATH, "s_full_under_test")


class BackgroundManagerTests(unittest.TestCase):
    def test_check_returns_running_placeholder_when_result_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = load_s_full_module(Path(tmp))
            manager = module.BackgroundManager()
            manager.tasks["abc123"] = {
                "status": "running",
                "command": "sleep 1",
                "result": None,
            }

            self.assertEqual(manager.check("abc123"), "[running] (running)")


class NotificationInjectionTests(unittest.TestCase):
    @staticmethod
    def notification():
        return {
            "task_id": "bg-1",
            "status": "completed",
            "result": "BACKGROUND_OK",
        }

    def test_string_user_tail_receives_background_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = load_s08_module(Path(tmp))
            module.BG = types.SimpleNamespace(
                drain_notifications=lambda: [self.notification()]
            )
            messages = [{"role": "user", "content": "original request"}]

            count = module.inject_background_notifications(messages)

            self.assertEqual(count, 1)
            self.assertEqual([message["role"] for message in messages], ["user"])
            self.assertEqual(
                messages[0]["content"][0],
                {"type": "text", "text": "original request"},
            )
            self.assertIn("BACKGROUND_OK", messages[0]["content"][1]["text"])

    def test_tool_result_user_tail_preserves_result_before_background_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = load_s08_module(Path(tmp))
            module.BG = types.SimpleNamespace(
                drain_notifications=lambda: [self.notification()]
            )
            tool_result = {
                "type": "tool_result",
                "tool_use_id": "tool-1",
                "content": "tool output",
            }
            messages = [{"role": "user", "content": [tool_result]}]

            module.inject_background_notifications(messages)

            self.assertEqual([message["role"] for message in messages], ["user"])
            self.assertEqual(messages[0]["content"][0], tool_result)
            self.assertIn("BACKGROUND_OK", messages[0]["content"][1]["text"])

    def test_assistant_tail_gets_one_following_user_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = load_s08_module(Path(tmp))
            module.BG = types.SimpleNamespace(
                drain_notifications=lambda: [self.notification()]
            )
            messages = [{"role": "assistant", "content": "working"}]

            module.inject_background_notifications(messages)

            self.assertEqual(
                [message["role"] for message in messages],
                ["assistant", "user"],
            )
            self.assertIn("BACKGROUND_OK", messages[1]["content"][0]["text"])

    def test_full_agent_merges_background_and_inbox_into_one_user_turn(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = load_s_full_module(Path(tmp))
            module.BG = types.SimpleNamespace(
                drain=lambda: [self.notification()]
            )
            module.BUS = types.SimpleNamespace(
                read_inbox=lambda recipient: [
                    {"from": "reviewer", "to": recipient, "content": "INBOX_OK"}
                ]
            )
            messages = [{"role": "user", "content": "original request"}]

            count = module.inject_pending_notifications(messages)

            self.assertEqual(count, 2)
            self.assertEqual([message["role"] for message in messages], ["user"])
            blocks = messages[0]["content"]
            self.assertEqual(blocks[0], {"type": "text", "text": "original request"})
            self.assertIn("BACKGROUND_OK", blocks[1]["text"])
            self.assertIn("INBOX_OK", blocks[2]["text"])


if __name__ == "__main__":
    unittest.main()
