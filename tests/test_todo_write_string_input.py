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
    ("s06", REPO_ROOT / "s06_subagent" / "code.py"),
    ("s07", REPO_ROOT / "s07_skill_loading" / "code.py"),
    ("s08", REPO_ROOT / "s08_context_compact" / "code.py"),
    ("s20", REPO_ROOT / "s20_comprehensive" / "code.py"),
]


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

                self.assertIn("Updated 1", result)
                self.assertEqual(
                    module.CURRENT_TODOS,
                    [{"content": "inspect repo", "status": "pending"}],
                )

    def test_issue_340_accepts_python_list_repr_string(self):
        for module_name, module_path in COURSE_MODULES:
            with self.subTest(module=module_name), tempfile.TemporaryDirectory() as tmp:
                module = load_course_module(module_name, module_path, Path(tmp))

                result = module.run_todo_write(
                    "[{'content': 'write tests', 'status': 'in_progress'}]"
                )

                self.assertIn("Updated 1", result)
                self.assertEqual(
                    module.CURRENT_TODOS,
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


if __name__ == "__main__":
    unittest.main()
