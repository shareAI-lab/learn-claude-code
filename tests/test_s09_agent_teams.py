import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
S09_PATH = REPO_ROOT / "agents" / "s09_agent_teams.py"


def load_module(name: str, path: Path, temp_cwd: Path):
    """Load an agent module with mocked Anthropic SDK and dotenv.

    Args:
        name: Module name to register in sys.modules.
        path: Absolute path to the .py source file.
        temp_cwd: Directory to chdir into before exec (isolates .team/ files).

    Returns:
        The loaded module object.
    """
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
    previous_model = os.environ.get("MODEL_ID")
    previous_key = os.environ.get("ANTHROPIC_API_KEY")

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    os.environ["MODEL_ID"] = "test-model"
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    try:
        os.chdir(temp_cwd)
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
        if previous_model is None:
            os.environ.pop("MODEL_ID", None)
        else:
            os.environ["MODEL_ID"] = previous_model
        if previous_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = previous_key


class MessageBusTests(unittest.TestCase):
    """Tests for MessageBus.send / read_inbox / broadcast."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.module = load_module(
            "s09_bus_under_test", S09_PATH, Path(self.tmp.name)
        )
        self.inbox_dir = Path(self.tmp.name) / "inbox"
        self.bus = self.module.MessageBus(self.inbox_dir)

    def tearDown(self):
        self.tmp.cleanup()

    def test_send_valid_message_writes_jsonl(self):
        result = self.bus.send("alice", "bob", "hello")
        self.assertEqual(result, "Sent message to bob")
        inbox_path = self.inbox_dir / "bob.jsonl"
        self.assertTrue(inbox_path.exists())
        msg = json.loads(inbox_path.read_text().strip())
        self.assertEqual(msg["type"], "message")
        self.assertEqual(msg["from"], "alice")
        self.assertEqual(msg["content"], "hello")
        self.assertIn("timestamp", msg)

    def test_send_invalid_msg_type_returns_error(self):
        result = self.bus.send("alice", "bob", "hello", msg_type="invalid_type")
        self.assertTrue(result.startswith("Error:"))
        self.assertIn("invalid_type", result)
        self.assertFalse((self.inbox_dir / "bob.jsonl").exists())

    def test_send_all_valid_msg_types(self):
        for msg_type in self.module.VALID_MSG_TYPES:
            result = self.bus.send("alice", "bob", "x", msg_type=msg_type)
            self.assertEqual(result, f"Sent {msg_type} to bob")

    def test_send_with_extra_fields(self):
        result = self.bus.send(
            "alice", "bob", "hello", extra={"request_id": "abc"}
        )
        self.assertEqual(result, "Sent message to bob")
        msg = json.loads((self.inbox_dir / "bob.jsonl").read_text().strip())
        self.assertEqual(msg["request_id"], "abc")

    def test_send_appends_multiple_messages(self):
        self.bus.send("alice", "bob", "first")
        self.bus.send("alice", "bob", "second")
        lines = (self.inbox_dir / "bob.jsonl").read_text().strip().splitlines()
        self.assertEqual(len(lines), 2)

    def test_read_inbox_drains_messages(self):
        self.bus.send("alice", "bob", "first")
        self.bus.send("alice", "bob", "second")
        msgs = self.bus.read_inbox("bob")
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["content"], "first")
        self.assertEqual(msgs[1]["content"], "second")
        # Second read returns empty (drained).
        self.assertEqual(self.bus.read_inbox("bob"), [])

    def test_read_inbox_nonexistent_returns_empty(self):
        self.assertEqual(self.bus.read_inbox("nobody"), [])

    def test_broadcast_excludes_sender(self):
        result = self.bus.broadcast("alice", "hi", ["alice", "bob", "carol"])
        self.assertEqual(result, "Broadcast to 2 teammates")
        self.assertEqual(len(self.bus.read_inbox("bob")), 1)
        self.assertEqual(len(self.bus.read_inbox("carol")), 1)
        self.assertEqual(self.bus.read_inbox("alice"), [])

    def test_broadcast_uses_broadcast_type(self):
        self.bus.broadcast("alice", "hi", ["bob"])
        msg = self.bus.read_inbox("bob")[0]
        self.assertEqual(msg["type"], "broadcast")

    def test_broadcast_empty_teammates(self):
        result = self.bus.broadcast("alice", "hi", [])
        self.assertEqual(result, "Broadcast to 0 teammates")


class TeammateManagerTests(unittest.TestCase):
    """Tests for TeammateManager.spawn / list_all / member_names."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.module = load_module(
            "s09_team_under_test", S09_PATH, Path(self.tmp.name)
        )
        self.team_dir = Path(self.tmp.name) / "team"
        self.team = self.module.TeammateManager(self.team_dir)

    def tearDown(self):
        self.tmp.cleanup()

    def _join(self, name):
        thread = self.team.threads.get(name)
        if thread is not None:
            thread.join(timeout=5)

    def test_spawn_new_member_returns_string(self):
        result = self.team.spawn("alice", "coder", "do something")
        self.assertEqual(result, "Spawned 'alice' (role: coder)")
        self._join("alice")

    def test_spawn_adds_member_to_config(self):
        self.team.spawn("alice", "coder", "do something")
        self._join("alice")
        self.assertIn("alice", self.team.member_names())

    def test_spawn_status_transitions_to_idle(self):
        self.team.spawn("alice", "coder", "do something")
        self._join("alice")
        member = self.team._find_member("alice")
        self.assertIsNotNone(member)
        self.assertEqual(member["status"], "idle")

    def test_spawn_existing_idle_resets_to_working(self):
        self.team.spawn("alice", "coder", "first task")
        self._join("alice")
        self.assertEqual(self.team._find_member("alice")["status"], "idle")
        result = self.team.spawn("alice", "reviewer", "second task")
        self.assertEqual(result, "Spawned 'alice' (role: reviewer)")
        self._join("alice")
        member = self.team._find_member("alice")
        self.assertEqual(member["role"], "reviewer")

    def test_spawn_existing_working_returns_error(self):
        self.team.config["members"].append(
            {"name": "alice", "role": "coder", "status": "working"}
        )
        self.team._save_config()
        result = self.team.spawn("alice", "coder", "do something")
        self.assertTrue(result.startswith("Error:"))
        self.assertIn("working", result)

    def test_list_all_empty(self):
        self.assertEqual(self.team.list_all(), "No teammates.")

    def test_list_all_shows_members(self):
        self.team.spawn("alice", "coder", "do something")
        self._join("alice")
        listing = self.team.list_all()
        self.assertIn("alice", listing)
        self.assertIn("coder", listing)

    def test_member_names_empty(self):
        self.assertEqual(self.team.member_names(), [])

    def test_member_names_multiple(self):
        self.team.spawn("alice", "coder", "task a")
        self.team.spawn("bob", "tester", "task b")
        self._join("alice")
        self._join("bob")
        self.assertEqual(set(self.team.member_names()), {"alice", "bob"})

    def test_config_persisted_to_disk(self):
        self.team.spawn("alice", "coder", "do something")
        self._join("alice")
        config_path = self.team_dir / "config.json"
        self.assertTrue(config_path.exists())
        config = json.loads(config_path.read_text())
        self.assertEqual(config["team_name"], "default")
        self.assertEqual(len(config["members"]), 1)


if __name__ == "__main__":
    unittest.main()
