import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
S10_PATH = REPO_ROOT / "agents" / "s10_team_protocols.py"


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
    """Tests for MessageBus message-type validation (s10 shares s09 bus)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.module = load_module(
            "s10_bus_under_test", S10_PATH, Path(self.tmp.name)
        )
        self.inbox_dir = Path(self.tmp.name) / ".team" / "inbox"
        self.bus = self.module.BUS

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_msg_types_set(self):
        expected = {
            "message",
            "broadcast",
            "shutdown_request",
            "shutdown_response",
            "plan_approval_response",
        }
        self.assertEqual(self.module.VALID_MSG_TYPES, expected)

    def test_send_invalid_type_rejected(self):
        result = self.bus.send("alice", "bob", "hi", msg_type="bad_type")
        self.assertTrue(result.startswith("Error:"))
        self.assertIn("bad_type", result)

    def test_send_shutdown_request(self):
        result = self.bus.send(
            "lead", "alice", "shut down", "shutdown_request",
            extra={"request_id": "r1"},
        )
        self.assertEqual(result, "Sent shutdown_request to alice")

    def test_send_plan_approval_response(self):
        result = self.bus.send(
            "alice", "lead", "plan text", "plan_approval_response",
            extra={"request_id": "p1", "approve": True},
        )
        self.assertEqual(result, "Sent plan_approval_response to lead")


class ShutdownProtocolTests(unittest.TestCase):
    """Tests for the shutdown_request / shutdown_response handshake."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.module = load_module(
            "s10_shutdown_under_test", S10_PATH, Path(self.tmp.name)
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_handle_shutdown_request_creates_pending_tracker(self):
        result = self.module.handle_shutdown_request("alice")
        self.assertIn("alice", result)
        self.assertIn("pending", result)
        self.assertEqual(len(self.module.shutdown_requests), 1)
        req_id = next(iter(self.module.shutdown_requests))
        self.assertEqual(
            self.module.shutdown_requests[req_id],
            {"target": "alice", "status": "pending"},
        )

    def test_handle_shutdown_request_sends_message(self):
        self.module.handle_shutdown_request("alice")
        msgs = self.module.BUS.read_inbox("alice")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["type"], "shutdown_request")
        self.assertEqual(msgs[0]["from"], "lead")
        self.assertIn("request_id", msgs[0])

    def test_teammate_shutdown_response_approves(self):
        self.module.handle_shutdown_request("alice")
        req_id = next(iter(self.module.shutdown_requests))
        result = self.module.TEAM._exec(
            "alice", "shutdown_response",
            {"request_id": req_id, "approve": True},
        )
        self.assertEqual(result, "Shutdown approved")
        self.assertEqual(
            self.module.shutdown_requests[req_id]["status"], "approved"
        )

    def test_teammate_shutdown_response_rejects(self):
        self.module.handle_shutdown_request("alice")
        req_id = next(iter(self.module.shutdown_requests))
        result = self.module.TEAM._exec(
            "alice", "shutdown_response",
            {"request_id": req_id, "approve": False, "reason": "busy"},
        )
        self.assertEqual(result, "Shutdown rejected")
        self.assertEqual(
            self.module.shutdown_requests[req_id]["status"], "rejected"
        )

    def test_shutdown_response_sends_message_to_lead(self):
        self.module.handle_shutdown_request("alice")
        req_id = next(iter(self.module.shutdown_requests))
        self.module.TEAM._exec(
            "alice", "shutdown_response",
            {"request_id": req_id, "approve": True},
        )
        lead_msgs = self.module.BUS.read_inbox("lead")
        self.assertEqual(len(lead_msgs), 1)
        self.assertEqual(lead_msgs[0]["type"], "shutdown_response")
        self.assertEqual(lead_msgs[0]["from"], "alice")
        self.assertTrue(lead_msgs[0]["approve"])

    def test_check_shutdown_status_pending(self):
        self.module.handle_shutdown_request("alice")
        req_id = next(iter(self.module.shutdown_requests))
        status = json.loads(self.module._check_shutdown_status(req_id))
        self.assertEqual(status["status"], "pending")
        self.assertEqual(status["target"], "alice")

    def test_check_shutdown_status_approved(self):
        self.module.handle_shutdown_request("alice")
        req_id = next(iter(self.module.shutdown_requests))
        self.module.TEAM._exec(
            "alice", "shutdown_response",
            {"request_id": req_id, "approve": True},
        )
        status = json.loads(self.module._check_shutdown_status(req_id))
        self.assertEqual(status["status"], "approved")

    def test_check_shutdown_status_not_found(self):
        status = json.loads(self.module._check_shutdown_status("nonexistent"))
        self.assertEqual(status, {"error": "not found"})

    def test_full_shutdown_handshake(self):
        # Lead requests shutdown.
        self.module.handle_shutdown_request("bob")
        req_id = next(iter(self.module.shutdown_requests))
        # Teammate receives and approves.
        inbox = self.module.BUS.read_inbox("bob")
        self.assertEqual(inbox[0]["type"], "shutdown_request")
        self.module.TEAM._exec(
            "bob", "shutdown_response",
            {"request_id": req_id, "approve": True},
        )
        # Lead verifies approved status.
        status = json.loads(self.module._check_shutdown_status(req_id))
        self.assertEqual(status["status"], "approved")


class PlanApprovalProtocolTests(unittest.TestCase):
    """Tests for the plan_approval submission and review gate."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.module = load_module(
            "s10_plan_under_test", S10_PATH, Path(self.tmp.name)
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_teammate_submits_plan_creates_pending(self):
        result = self.module.TEAM._exec(
            "alice", "plan_approval", {"plan": "refactor module X"}
        )
        self.assertIn("Plan submitted", result)
        self.assertIn("request_id", result)
        self.assertEqual(len(self.module.plan_requests), 1)
        req_id = next(iter(self.module.plan_requests))
        entry = self.module.plan_requests[req_id]
        self.assertEqual(entry["from"], "alice")
        self.assertEqual(entry["plan"], "refactor module X")
        self.assertEqual(entry["status"], "pending")

    def test_plan_submission_sends_message_to_lead(self):
        self.module.TEAM._exec(
            "alice", "plan_approval", {"plan": "do work"}
        )
        lead_msgs = self.module.BUS.read_inbox("lead")
        self.assertEqual(len(lead_msgs), 1)
        self.assertEqual(lead_msgs[0]["type"], "plan_approval_response")
        self.assertEqual(lead_msgs[0]["from"], "alice")
        self.assertEqual(lead_msgs[0]["content"], "do work")
        self.assertIn("request_id", lead_msgs[0])

    def test_lead_approves_plan(self):
        self.module.TEAM._exec(
            "alice", "plan_approval", {"plan": "do work"}
        )
        req_id = next(iter(self.module.plan_requests))
        result = self.module.handle_plan_review(req_id, True, "looks good")
        self.assertIn("approved", result)
        self.assertIn("alice", result)
        self.assertEqual(
            self.module.plan_requests[req_id]["status"], "approved"
        )

    def test_lead_rejects_plan(self):
        self.module.TEAM._exec(
            "alice", "plan_approval", {"plan": "bad plan"}
        )
        req_id = next(iter(self.module.plan_requests))
        result = self.module.handle_plan_review(req_id, False, "needs rework")
        self.assertIn("rejected", result)
        self.assertEqual(
            self.module.plan_requests[req_id]["status"], "rejected"
        )

    def test_plan_review_unknown_request_id(self):
        result = self.module.handle_plan_review("nonexistent", True, "")
        self.assertTrue(result.startswith("Error:"))
        self.assertIn("nonexistent", result)

    def test_plan_review_sends_response_to_teammate(self):
        self.module.TEAM._exec(
            "alice", "plan_approval", {"plan": "do work"}
        )
        req_id = next(iter(self.module.plan_requests))
        self.module.handle_plan_review(req_id, True, "approved!")
        alice_msgs = self.module.BUS.read_inbox("alice")
        self.assertEqual(len(alice_msgs), 1)
        self.assertEqual(alice_msgs[0]["type"], "plan_approval_response")
        self.assertTrue(alice_msgs[0]["approve"])
        self.assertEqual(alice_msgs[0]["feedback"], "approved!")

    def test_plan_pending_until_reviewed(self):
        # Plan stays pending until lead reviews it.
        self.module.TEAM._exec(
            "alice", "plan_approval", {"plan": "do work"}
        )
        req_id = next(iter(self.module.plan_requests))
        self.assertEqual(
            self.module.plan_requests[req_id]["status"], "pending"
        )
        # Simulate lead checking inbox but not yet reviewing.
        lead_msgs = self.module.BUS.read_inbox("lead")
        self.assertEqual(len(lead_msgs), 1)
        self.assertEqual(
            self.module.plan_requests[req_id]["status"], "pending"
        )

    def test_full_plan_approval_flow(self):
        # Teammate submits plan.
        self.module.TEAM._exec(
            "alice", "plan_approval", {"plan": "implement feature"}
        )
        req_id = next(iter(self.module.plan_requests))
        # Lead reads submission.
        lead_msgs = self.module.BUS.read_inbox("lead")
        self.assertEqual(lead_msgs[0]["plan"], "implement feature")
        # Lead approves.
        self.module.handle_plan_review(req_id, True, "go ahead")
        # Teammate receives approval.
        alice_msgs = self.module.BUS.read_inbox("alice")
        self.assertTrue(alice_msgs[0]["approve"])
        # Tracker reflects approved.
        self.assertEqual(
            self.module.plan_requests[req_id]["status"], "approved"
        )


if __name__ == "__main__":
    unittest.main()
