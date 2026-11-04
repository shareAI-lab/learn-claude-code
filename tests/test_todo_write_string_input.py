import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COURSE_MODULES = [
    ("s05", REPO_ROOT / "s05_todo_write" / "code.py"),
    ("s15", REPO_ROOT / "s15_integrated_harness" / "code.py"),
]


def todo_items(module):
    if hasattr(module, "TODO"):
        return module.TODO.items
    return module.CURRENT_TODOS


def load_course_module(module_name: str, module_path: Path, temp_cwd: Path):
    fake_anthropic = types.ModuleType("anthropic")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_dotenv = types.ModuleType("dotenv")
    fake_yaml = types.ModuleType("yaml")
    setattr(fake_anthropic, "Anthropic", FakeAnthropic)
    setattr(fake_dotenv, "load_dotenv", lambda override=True: None)
    setattr(fake_yaml, "safe_load", lambda text: {})
    setattr(fake_yaml, "YAMLError", Exception)

    previous_modules = {
        "anthropic": sys.modules.get("anthropic"),
        "dotenv": sys.modules.get("dotenv"),
        "yaml": sys.modules.get("yaml"),
    }
    previous_cwd = Path.cwd()
    previous_model_id = os.environ.get("MODEL_ID")

    spec = importlib.util.spec_from_file_location(f"{module_name}_todo_test", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    sys.modules["yaml"] = fake_yaml
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


class TodoWriteStringInputTests(unittest.TestCase):
    def test_issue_340_accepts_json_array_string(self):
        for module_name, module_path in COURSE_MODULES:
            with self.subTest(module=module_name), tempfile.TemporaryDirectory() as tmp:
                module = load_course_module(module_name, module_path, Path(tmp))

                result = module.run_todo_write(
                    '[{"content": "inspect repo", "status": "pending"}]'
                )

                self.assertTrue("Updated 1" in result or "[ ] inspect repo" in result)
                self.assertEqual(
                    todo_items(module),
                    [{"content": "inspect repo", "status": "pending"}],
                )

    def test_issue_340_accepts_python_list_repr_string(self):
        for module_name, module_path in COURSE_MODULES:
            with self.subTest(module=module_name), tempfile.TemporaryDirectory() as tmp:
                module = load_course_module(module_name, module_path, Path(tmp))

                result = module.run_todo_write(
                    "[{'content': 'write tests', 'status': 'in_progress'}]"
                )

                self.assertTrue("Updated 1" in result or "[>] write tests" in result)
                self.assertEqual(
                    todo_items(module),
                    [{"content": "write tests", "status": "in_progress"}],
                )

    def test_issue_340_does_not_eval_string_inputs(self):
        for module_name, module_path in COURSE_MODULES:
            with self.subTest(module=module_name), tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                marker = tmp_path / "eval_was_executed"
                module = load_course_module(module_name, module_path, tmp_path)

                result = module.run_todo_write(
                    f"__import__('pathlib').Path({str(marker)!r}).write_text('bad')"
                )

                self.assertIn("Error:", result)
                self.assertFalse(marker.exists())


class S05TodoManagerTests(unittest.TestCase):
    def load_s05(self, temp_cwd: Path):
        return load_course_module("s05", COURSE_MODULES[0][1], temp_cwd)

    def test_returns_rendered_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = self.load_s05(Path(tmp))

            result = module.run_todo_write([
                {"content": "inspect repo", "status": "completed"},
                {"content": "write tests", "status": "in_progress"},
            ])

            self.assertIn("[x] inspect repo", result)
            self.assertIn("[>] write tests", result)
            self.assertIn("(1/2 completed)", result)

    def test_rejects_invalid_updates_without_replacing_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = self.load_s05(Path(tmp))
            module.run_todo_write([
                {"content": "keep this", "status": "pending"},
            ])

            invalid_updates = [
                [{"content": "", "status": "pending"}],
                [
                    {"content": "first", "status": "in_progress"},
                    {"content": "second", "status": "in_progress"},
                ],
                [
                    {"content": f"task {index}", "status": "pending"}
                    for index in range(21)
                ],
            ]
            for update in invalid_updates:
                with self.subTest(update=update):
                    result = module.run_todo_write(update)
                    self.assertIn("Error:", result)
                    self.assertEqual(
                        module.TODO.items,
                        [{"content": "keep this", "status": "pending"}],
                    )

    def test_appends_one_reminder_to_the_third_tool_result_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = self.load_s05(Path(tmp))
            responses = [
                types.SimpleNamespace(
                    stop_reason="tool_use",
                    content=[types.SimpleNamespace(
                        type="tool_use",
                        id=f"tool_{index}",
                        name="glob",
                        input={"pattern": "*.py"},
                    )],
                )
                for index in range(3)
            ]
            responses.append(types.SimpleNamespace(stop_reason="end_turn", content=[]))
            module.client.messages.create = lambda **kwargs: responses.pop(0)

            messages = []
            module.agent_loop(messages)

            result_batches = [
                message["content"] for message in messages
                if message["role"] == "user" and isinstance(message["content"], list)
            ]
            self.assertEqual(len(result_batches), 3)
            self.assertFalse(any(item["type"] == "text" for item in result_batches[0]))
            self.assertFalse(any(item["type"] == "text" for item in result_batches[1]))
            self.assertEqual(
                [item for item in result_batches[2] if item["type"] == "text"],
                [{"type": "text", "text": "<reminder>Update your todos.</reminder>"}],
            )


if __name__ == "__main__":
    unittest.main()
