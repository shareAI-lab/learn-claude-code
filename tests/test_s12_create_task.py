import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "s12_task_system" / "code.py"


def load_module(temp_cwd: Path):
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            pass

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None

    previous = {name: sys.modules.get(name) for name in ("anthropic", "dotenv")}
    previous_cwd = Path.cwd()
    previous_model = os.environ.get("MODEL_ID")
    spec = importlib.util.spec_from_file_location("s12_create_task_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    os.environ["MODEL_ID"] = "test-model"
    try:
        os.chdir(temp_cwd)
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous_cwd)
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
        if previous_model is None:
            os.environ.pop("MODEL_ID", None)
        else:
            os.environ["MODEL_ID"] = previous_model


class CreateTaskBlockedByTests(unittest.TestCase):
    def test_accepts_blocked_by_json_array_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = load_module(Path(tmp))
            result = module.run_create_task("write tests", blockedBy='["task_a"]')

            self.assertIn("blockedBy: task_a", result)
            self.assertEqual(module.list_tasks()[0].blockedBy, ["task_a"])

    def test_accepts_blocked_by_python_list_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = load_module(Path(tmp))
            result = module.run_create_task("write docs", blockedBy="['task_a']")

            self.assertIn("blockedBy: task_a", result)
            self.assertEqual(module.list_tasks()[0].blockedBy, ["task_a"])

    def test_rejects_non_list_blocked_by_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = load_module(Path(tmp))

            self.assertEqual(
                module.run_create_task("bad", blockedBy="not a list"),
                "Error: blockedBy must be a list or JSON array string",
            )


if __name__ == "__main__":
    unittest.main()
