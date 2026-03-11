import importlib
import os
import sys
import threading
import time
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("MODEL_ID", "test-model")

if "dotenv" not in sys.modules:
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda override=True: None
    sys.modules["dotenv"] = dotenv

if "anthropic" not in sys.modules:
    anthropic = types.ModuleType("anthropic")

    class Anthropic:  # pragma: no cover - import shim only
        def __init__(self, *args, **kwargs):
            self.messages = SimpleNamespace(create=lambda **kwargs: None)

    anthropic.Anthropic = Anthropic
    sys.modules["anthropic"] = anthropic


s08 = importlib.import_module("agents.s08_background_tasks")


class FakeMessagesAPI:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class BackgroundTasksTests(unittest.TestCase):
    def setUp(self):
        self.original_client = s08.client
        self.original_bg = s08.BG

    def tearDown(self):
        s08.client = self.original_client
        s08.BG = self.original_bg

    def test_wait_for_notifications_unblocks_when_task_finishes(self):
        bg = s08.BackgroundManager()
        bg.tasks["task-1"] = {"status": "running", "result": None, "command": "demo"}

        def complete_task():
            time.sleep(0.05)
            with bg._notifications_ready:
                bg.tasks["task-1"]["status"] = "completed"
                bg.tasks["task-1"]["result"] = "done"
                bg._notification_queue.append(
                    {
                        "task_id": "task-1",
                        "status": "completed",
                        "command": "demo",
                        "result": "done",
                    }
                )
                bg._notifications_ready.notify_all()

        threading.Thread(target=complete_task, daemon=True).start()
        notifs = bg.wait_for_notifications()

        self.assertEqual(
            notifs,
            [
                {
                    "task_id": "task-1",
                    "status": "completed",
                    "command": "demo",
                    "result": "done",
                }
            ],
        )

    def test_agent_loop_resumes_after_background_completion(self):
        bg = s08.BackgroundManager()
        bg.tasks["task-1"] = {"status": "running", "result": None, "command": "demo"}
        s08.BG = bg

        responses = [
            SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="running")]),
            SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="done")]),
        ]
        fake_messages = FakeMessagesAPI(responses)
        s08.client = SimpleNamespace(messages=fake_messages)

        def complete_task():
            time.sleep(0.05)
            with bg._notifications_ready:
                bg.tasks["task-1"]["status"] = "completed"
                bg.tasks["task-1"]["result"] = "done"
                bg._notification_queue.append(
                    {
                        "task_id": "task-1",
                        "status": "completed",
                        "command": "demo",
                        "result": "done",
                    }
                )
                bg._notifications_ready.notify_all()

        threading.Thread(target=complete_task, daemon=True).start()
        messages = [{"role": "user", "content": "run task in background"}]

        s08.agent_loop(messages)

        self.assertEqual(len(fake_messages.calls), 2)
        second_call_messages = fake_messages.calls[1]["messages"]
        self.assertTrue(
            any(
                msg["role"] == "user"
                and isinstance(msg["content"], str)
                and "<background-results>" in msg["content"]
                and "[bg:task-1] completed: done" in msg["content"]
                for msg in second_call_messages
            )
        )


if __name__ == "__main__":
    unittest.main()
