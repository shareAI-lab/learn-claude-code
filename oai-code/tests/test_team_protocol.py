"""M3-5: 团队协议 shutdown + plan_approval。"""
from __future__ import annotations

from oai_code.config import load_config
from oai_code.team import MessageBus, ProtocolTracker


def _setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    return MessageBus(cfg), ProtocolTracker()


# ---------- shutdown ----------

def test_send_shutdown_request(tmp_path, monkeypatch):
    bus, tr = _setup(tmp_path, monkeypatch)
    out = tr.send_shutdown(bus, "lead", "alice")
    assert "sent to 'alice'" in out and "pending" in out
    # alice 的 inbox 里有一条 shutdown_request
    msgs = bus.read_inbox("alice")
    assert len(msgs) == 1
    assert msgs[0]["type"] == "shutdown_request"
    assert "request_id" in msgs[0]


def test_shutdown_response_approve(tmp_path, monkeypatch):
    bus, tr = _setup(tmp_path, monkeypatch)
    tr.send_shutdown(bus, "lead", "alice")
    # 取出 req_id
    msgs = bus.read_inbox("alice")
    req_id = msgs[0]["request_id"]
    out = tr.record_shutdown_response(req_id, approve=True)
    assert "approved" in out
    entry = tr.get_shutdown(req_id)
    assert entry["status"] == "approved"


def test_shutdown_response_unknown_id(tmp_path, monkeypatch):
    bus, tr = _setup(tmp_path, monkeypatch)
    out = tr.record_shutdown_response("bogus", True)
    assert out.startswith("Error: unknown shutdown")


def test_send_shutdown_to_self_rejected(tmp_path, monkeypatch):
    bus, tr = _setup(tmp_path, monkeypatch)
    out = tr.send_shutdown(bus, "lead", "lead")
    assert out.startswith("Error")
    # 不应在 tracker 里留痕
    assert not tr.shutdown_requests


# ---------- plan_approval ----------

def test_submit_plan(tmp_path, monkeypatch):
    bus, tr = _setup(tmp_path, monkeypatch)
    out = tr.submit_plan(bus, "alice", "lead", "refactor auth module")
    assert "submitted to 'lead'" in out
    msgs = bus.read_inbox("lead")
    assert len(msgs) == 1
    assert msgs[0]["type"] == "plan_approval_request"


def test_review_plan_approve(tmp_path, monkeypatch):
    bus, tr = _setup(tmp_path, monkeypatch)
    tr.submit_plan(bus, "alice", "lead", "do the thing")
    msgs = bus.read_inbox("lead")
    req_id = msgs[0]["request_id"]
    out = tr.review_plan(bus, "lead", req_id, approve=True, feedback="ok")
    assert "approved" in out
    # alice 应收到 response
    alice_msgs = bus.read_inbox("alice")
    assert len(alice_msgs) == 1
    assert alice_msgs[0]["type"] == "plan_approval_response"
    assert alice_msgs[0]["approve"] is True


def test_review_plan_reject(tmp_path, monkeypatch):
    bus, tr = _setup(tmp_path, monkeypatch)
    tr.submit_plan(bus, "alice", "lead", "nuke the repo")
    req_id = bus.read_inbox("lead")[0]["request_id"]
    tr.review_plan(bus, "lead", req_id, approve=False, feedback="no way")
    resp = bus.read_inbox("alice")[0]
    assert resp["approve"] is False
    assert resp["content"] == "no way"
    assert tr.get_plan(req_id)["status"] == "rejected"


def test_review_unknown_plan(tmp_path, monkeypatch):
    bus, tr = _setup(tmp_path, monkeypatch)
    out = tr.review_plan(bus, "lead", "bogus", True)
    assert out.startswith("Error: unknown plan")


# ---------- tools integration ----------

def test_shutdown_request_tool_registered(tmp_path, monkeypatch):
    from oai_code.team import TeammateManager
    from oai_code.team.tools import register_team_tools
    from oai_code.tools.registry import ToolRegistry

    bus, tr = _setup(tmp_path, monkeypatch)
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    reg = ToolRegistry(cfg)
    mgr = TeammateManager(cfg=cfg)
    register_team_tools(
        reg, cfg=cfg, llm=None, bus=bus, manager=mgr, parent_registry=reg, tracker=tr
    )
    assert reg.get("ShutdownRequest") is not None
    assert reg.get("PlanApproval") is not None


def test_plan_approval_tool_end_to_end(tmp_path, monkeypatch):
    from oai_code.team import TeammateManager
    from oai_code.team.tools import register_team_tools
    from oai_code.tools.registry import ToolRegistry

    bus, tr = _setup(tmp_path, monkeypatch)
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    reg = ToolRegistry(cfg)
    mgr = TeammateManager(cfg=cfg)
    register_team_tools(
        reg, cfg=cfg, llm=None, bus=bus, manager=mgr, parent_registry=reg, tracker=tr
    )
    tr.submit_plan(bus, "alice", "lead", "rewrite everything")
    req_id = bus.read_inbox("lead")[0]["request_id"]
    pa = reg.get("PlanApproval")
    out = pa.handler(request_id=req_id, approve=True, feedback="looks good")
    assert "approved" in out
