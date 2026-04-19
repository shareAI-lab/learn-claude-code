"""M3-3: 消息总线 + TeammateManager 测试。"""
from __future__ import annotations

from mycode.config import load_config
from mycode.team import MessageBus, TeammateManager


def _setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    return cfg, MessageBus(cfg), TeammateManager(cfg=cfg)


# ---------- MessageBus ----------

def test_send_and_read(tmp_path, monkeypatch):
    _, bus, _ = _setup(tmp_path, monkeypatch)
    bus.send("lead", "alice", "hi")
    msgs = bus.read_inbox("alice")
    assert len(msgs) == 1
    assert msgs[0]["content"] == "hi"
    assert msgs[0]["from"] == "lead"


def test_drain_on_read(tmp_path, monkeypatch):
    _, bus, _ = _setup(tmp_path, monkeypatch)
    bus.send("lead", "alice", "first")
    bus.send("lead", "alice", "second")
    first = bus.read_inbox("alice")
    assert len(first) == 2
    # 第二次 drain 应为空
    assert bus.read_inbox("alice") == []


def test_empty_inbox_returns_list(tmp_path, monkeypatch):
    _, bus, _ = _setup(tmp_path, monkeypatch)
    assert bus.read_inbox("never-written") == []


def test_reject_self_send(tmp_path, monkeypatch):
    _, bus, _ = _setup(tmp_path, monkeypatch)
    out = bus.send("lead", "lead", "x")
    assert out.startswith("Error: cannot send to self")


def test_reject_invalid_msg_type(tmp_path, monkeypatch):
    _, bus, _ = _setup(tmp_path, monkeypatch)
    out = bus.send("lead", "alice", "x", msg_type="weird")
    assert out.startswith("Error: invalid msg_type")


def test_reject_invalid_name(tmp_path, monkeypatch):
    _, bus, _ = _setup(tmp_path, monkeypatch)
    out = bus.send("lead", "../etc/passwd", "x")
    assert out.startswith("Error: invalid teammate name")


def test_broadcast_skips_sender(tmp_path, monkeypatch):
    _, bus, _ = _setup(tmp_path, monkeypatch)
    out = bus.broadcast("lead", "ping", ["lead", "alice", "bob"])
    assert "Broadcast to 2" in out
    assert len(bus.read_inbox("alice")) == 1
    assert len(bus.read_inbox("bob")) == 1
    assert bus.read_inbox("lead") == []


def test_extra_fields_preserved(tmp_path, monkeypatch):
    _, bus, _ = _setup(tmp_path, monkeypatch)
    bus.send("lead", "alice", "stop", msg_type="shutdown_request", extra={"request_id": "abc"})
    msg = bus.read_inbox("alice")[0]
    assert msg["request_id"] == "abc"
    assert msg["type"] == "shutdown_request"


# ---------- TeammateManager ----------

def test_register_and_find(tmp_path, monkeypatch):
    _, _, mgr = _setup(tmp_path, monkeypatch)
    m = mgr.register("alice", "backend")
    assert m["status"] == "working"
    got = mgr.find("alice")
    assert got and got["role"] == "backend"


def test_register_idempotent_updates_role(tmp_path, monkeypatch):
    _, _, mgr = _setup(tmp_path, monkeypatch)
    mgr.register("alice", "backend")
    mgr.register("alice", "senior-backend")
    assert mgr.find("alice")["role"] == "senior-backend"
    # 仍只有一条
    assert len(mgr.members()) == 1


def test_set_status(tmp_path, monkeypatch):
    _, _, mgr = _setup(tmp_path, monkeypatch)
    mgr.register("alice", "dev")
    assert mgr.set_status("alice", "idle").endswith("idle")
    assert mgr.find("alice")["status"] == "idle"
    assert mgr.set_status("alice", "bogus").startswith("Error")


def test_remove_unknown(tmp_path, monkeypatch):
    _, _, mgr = _setup(tmp_path, monkeypatch)
    assert mgr.remove("nobody").startswith("Error")


def test_names_list(tmp_path, monkeypatch):
    _, _, mgr = _setup(tmp_path, monkeypatch)
    mgr.register("alice", "a")
    mgr.register("bob", "b")
    assert set(mgr.names()) == {"alice", "bob"}


def test_render_empty(tmp_path, monkeypatch):
    _, _, mgr = _setup(tmp_path, monkeypatch)
    assert "empty" in mgr.render()
