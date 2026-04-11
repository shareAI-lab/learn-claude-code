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

import agents.s03_todo_write as s03_todo_write
import agents.s_full as s_full


class FakeMessagesAPI:
    def __init__(self, responses):
        self._responses = iter(responses)

    def create(self, **kwargs):
        return next(self._responses)


def make_tool_use_response(tool_id: str, tool_name: str, tool_input: dict):
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(
                type="tool_use", id=tool_id, name=tool_name, input=tool_input
            )
        ],
    )


class ToolResultOrderingTests(unittest.TestCase):
    def test_s03_places_tool_results_before_reminders(self):
        messages = [{"role": "user", "content": "do work"}]
        fake_api = FakeMessagesAPI(
            [
                make_tool_use_response("tool-1", "bash", {"command": "pwd"}),
                make_tool_use_response("tool-2", "bash", {"command": "pwd"}),
                make_tool_use_response("tool-3", "bash", {"command": "pwd"}),
                SimpleNamespace(stop_reason="end_turn", content="done"),
            ]
        )
        original_client = s03_todo_write.client
        original_handlers = s03_todo_write.TOOL_HANDLERS
        original_state = s03_todo_write.TODO.state
        try:
            s03_todo_write.client = SimpleNamespace(messages=fake_api)
            s03_todo_write.TOOL_HANDLERS = {
                **original_handlers,
                "bash": lambda **kwargs: "ok",
            }
            # Ensure reminder path is active for this regression assertion.
            s03_todo_write.TODO.state = s03_todo_write.PlanningState(
                items=[s03_todo_write.PlanItem(content="keep plan fresh")],
                rounds_since_update=0,
            )
            s03_todo_write.agent_loop(messages)
        finally:
            s03_todo_write.client = original_client
            s03_todo_write.TOOL_HANDLERS = original_handlers
            s03_todo_write.TODO.state = original_state

        third_user_message = messages[-2]["content"]
        self.assertEqual(third_user_message[0]["type"], "tool_result")
        self.assertEqual(third_user_message[-1]["type"], "text")

    def test_s_full_places_tool_results_before_reminders(self):
        messages = [{"role": "user", "content": "do work"}]
        fake_api = FakeMessagesAPI(
            [
                make_tool_use_response("tool-1", "bash", {"command": "pwd"}),
                make_tool_use_response("tool-2", "bash", {"command": "pwd"}),
                make_tool_use_response("tool-3", "bash", {"command": "pwd"}),
                SimpleNamespace(stop_reason="end_turn", content="done"),
            ]
        )
        original_client = s_full.client
        original_handlers = s_full.TOOL_HANDLERS
        original_has_open_items = s_full.TODO.has_open_items
        try:
            s_full.client = SimpleNamespace(messages=fake_api)
            s_full.TOOL_HANDLERS = {**original_handlers, "bash": lambda **kwargs: "ok"}
            s_full.TODO.has_open_items = lambda: True
            s_full.agent_loop(messages)
        finally:
            s_full.client = original_client
            s_full.TOOL_HANDLERS = original_handlers
            s_full.TODO.has_open_items = original_has_open_items

        third_user_message = messages[-2]["content"]
        self.assertEqual(third_user_message[0]["type"], "tool_result")
        self.assertEqual(third_user_message[-1]["type"], "text")


if __name__ == "__main__":
    unittest.main()
