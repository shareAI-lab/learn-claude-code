import importlib.util
import os
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "s13": REPO_ROOT / "s13_background_tasks" / "code.py",
    "s14": REPO_ROOT / "s14_cron_scheduler" / "code.py",
    "s20": REPO_ROOT / "s20_comprehensive" / "code.py",
}


def load_module(name: str, path: Path, temp_cwd: Path):
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
    previous_model = os.environ.get("MODEL_ID")

    spec = importlib.util.spec_from_file_location(f"{name}_bg_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
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
        if previous_model is None:
            os.environ.pop("MODEL_ID", None)
        else:
            os.environ["MODEL_ID"] = previous_model
        for mod_name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(mod_name, None)
            else:
                sys.modules[mod_name] = previous


def boom(**kwargs):
    raise RuntimeError("handler exploded")


def start_failing_task(module, name: str):
    """Dispatch a background task whose handler raises, per-module wiring."""
    block = types.SimpleNamespace(name="bash", input={"command": "boom"}, id="tu_1")
    if name == "s20":
        return module.start_background_task(block, {"bash": boom})
    if name == "s14":
        # s14 builds its handler table inline from module globals.
        module.run_bash = boom
        return module.start_background_task(block)
    module.TOOL_HANDLERS["bash"] = boom
    return module.start_background_task(block)


def wait_for_terminal_status(module, bg_id: str, timeout: float = 5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with module.background_lock:
            task = module.background_tasks.get(bg_id)
            status = task["status"] if task else None
        if status is None or status != "running":
            return status
        time.sleep(0.01)
    return "running"


class BackgroundTaskFailureTests(unittest.TestCase):
    def test_failing_handler_does_not_leave_task_running_forever(self):
        for name, path in MODULES.items():
            with self.subTest(module=name), tempfile.TemporaryDirectory() as tmp:
                module = load_module(name, path, Path(tmp))
                bg_id = start_failing_task(module, name)

                status = wait_for_terminal_status(module, bg_id)
                self.assertNotEqual(
                    status, "running",
                    f"{name}: background task stayed 'running' after the handler raised")

    def test_failure_is_reported_back_to_the_model(self):
        for name, path in MODULES.items():
            with self.subTest(module=name), tempfile.TemporaryDirectory() as tmp:
                module = load_module(name, path, Path(tmp))
                bg_id = start_failing_task(module, name)
                wait_for_terminal_status(module, bg_id)

                notifications = module.collect_background_results()
                self.assertEqual(
                    len(notifications), 1,
                    f"{name}: failed background task produced no notification")
                self.assertIn("<status>failed</status>", notifications[0])
                self.assertIn("handler exploded", notifications[0])

    def test_successful_task_still_reports_completed(self):
        for name, path in MODULES.items():
            with self.subTest(module=name), tempfile.TemporaryDirectory() as tmp:
                module = load_module(name, path, Path(tmp))
                block = types.SimpleNamespace(
                    name="bash", input={"command": "ok"}, id="tu_2")
                ok = lambda **kwargs: "all good"
                if name == "s20":
                    bg_id = module.start_background_task(block, {"bash": ok})
                elif name == "s14":
                    module.run_bash = ok
                    bg_id = module.start_background_task(block)
                else:
                    module.TOOL_HANDLERS["bash"] = ok
                    bg_id = module.start_background_task(block)

                wait_for_terminal_status(module, bg_id)
                notifications = module.collect_background_results()
                self.assertEqual(len(notifications), 1)
                self.assertIn("<status>completed</status>", notifications[0])
                self.assertIn("all good", notifications[0])


if __name__ == "__main__":
    unittest.main()
