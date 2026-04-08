import os
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("MODEL_ID", "test-model")

fake_anthropic = types.ModuleType("anthropic")


class FakeAnthropic:
    def __init__(self, *args, **kwargs):
        self.messages = SimpleNamespace(create=None)


setattr(fake_anthropic, "Anthropic", FakeAnthropic)
sys.modules.setdefault("anthropic", fake_anthropic)

fake_dotenv = types.ModuleType("dotenv")
setattr(fake_dotenv, "load_dotenv", lambda *args, **kwargs: None)
sys.modules.setdefault("dotenv", fake_dotenv)

import agents.s13_background_tasks as s13_background_tasks
import agents.s_full as s_full


class FakeMessagesAPI:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.call_count = 0

    def create(self, **kwargs):
        self.call_count += 1
        return next(self._responses)


class FakeS13BackgroundManager:
    def __init__(self):
        self._running = True
        self.wait_called = False

    def drain_notifications(self):
        return []

    def has_running_tasks(self):
        return self._running

    def wait_for_notifications(self):
        self.wait_called = True
        self._running = False
        return [
            {
                "task_id": "bg-1",
                "status": "completed",
                "preview": "done",
                "output_file": ".runtime-tasks/bg-1.log",
            }
        ]


class FakeSFullBackgroundManager:
    def __init__(self):
        self._running = True
        self.wait_called = False

    def drain(self):
        return []

    def has_running_tasks(self):
        return self._running

    def wait_for_notifications(self):
        self.wait_called = True
        self._running = False
        return [{"task_id": "bg-1", "status": "completed", "result": "done"}]


class BackgroundNotificationTests(unittest.TestCase):
    def test_s13_agent_loop_waits_for_background_results_after_end_turn(self):
        messages = [{"role": "user", "content": "Run tests in the background"}]
        fake_bg = FakeS13BackgroundManager()
        fake_api = FakeMessagesAPI(
            [
                SimpleNamespace(
                    stop_reason="end_turn", content="Started background work."
                ),
                SimpleNamespace(
                    stop_reason="end_turn", content="Background work completed."
                ),
            ]
        )
        original_bg = s13_background_tasks.BG
        original_client = s13_background_tasks.client
        try:
            s13_background_tasks.BG = fake_bg
            s13_background_tasks.client = SimpleNamespace(messages=fake_api)
            s13_background_tasks.agent_loop(messages)
        finally:
            s13_background_tasks.BG = original_bg
            s13_background_tasks.client = original_client

        self.assertTrue(fake_bg.wait_called)
        self.assertEqual(fake_api.call_count, 2)
        self.assertTrue(
            any(
                message["role"] == "user"
                and isinstance(message["content"], str)
                and "<background-results>" in message["content"]
                for message in messages
            )
        )

    def test_s_full_agent_loop_waits_for_background_results_after_end_turn(self):
        messages = [{"role": "user", "content": "Run tests in the background"}]
        fake_bg = FakeSFullBackgroundManager()
        fake_api = FakeMessagesAPI(
            [
                SimpleNamespace(
                    stop_reason="end_turn", content="Started background work."
                ),
                SimpleNamespace(
                    stop_reason="end_turn", content="Background work completed."
                ),
            ]
        )
        original_bg = s_full.BG
        original_client = s_full.client
        try:
            s_full.BG = fake_bg
            s_full.client = SimpleNamespace(messages=fake_api)
            s_full.agent_loop(messages)
        finally:
            s_full.BG = original_bg
            s_full.client = original_client

        self.assertTrue(fake_bg.wait_called)
        self.assertEqual(fake_api.call_count, 2)
        self.assertTrue(
            any(
                message["role"] == "user"
                and isinstance(message["content"], str)
                and "<background-results>" in message["content"]
                for message in messages
            )
        )


if __name__ == "__main__":
    unittest.main()
