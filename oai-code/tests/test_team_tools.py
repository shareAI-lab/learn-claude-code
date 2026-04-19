"""M3-4: 多 Agent 工具注册与 spawn 防重测试。"""
from __future__ import annotations

from oai_code.config import load_config
from oai_code.team import MessageBus, TeammateManager
from oai_code.team.tools import register_team_tools
from oai_code.tools.builtin import register_builtins
from oai_code.tools.registry import ToolRegistry


def _setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    reg = ToolRegistry(cfg)
    register_builtins(reg)
    bus = MessageBus(cfg)
    mgr = TeammateManager(cfg=cfg)
    return cfg, reg, bus, mgr


def test_team_tools_registered(tmp_path, monkeypatch):
    cfg, reg, bus, mgr = _setup(tmp_path, monkeypatch)
    register_team_tools(reg, cfg=cfg, llm=None, bus=bus, manager=mgr, parent_registry=reg)
    names = set(reg.names())
    assert {"SpawnTeammate", "SendMessage", "Broadcast", "ReadInbox", "ListTeammates"} <= names


def test_send_message_tool_uses_lead_as_sender(tmp_path, monkeypatch):
    cfg, reg, bus, mgr = _setup(tmp_path, monkeypatch)
    register_team_tools(reg, cfg=cfg, llm=None, bus=bus, manager=mgr, parent_registry=reg)
    send = reg.get("SendMessage")
    out = send.handler(to="alice", content="hi")
    assert "Sent message to alice" in out
    msgs = bus.read_inbox("alice")
    assert msgs[0]["from"] == "lead"


def test_read_inbox_tool_empty(tmp_path, monkeypatch):
    cfg, reg, bus, mgr = _setup(tmp_path, monkeypatch)
    register_team_tools(reg, cfg=cfg, llm=None, bus=bus, manager=mgr, parent_registry=reg)
    out = reg.get("ReadInbox").handler()
    assert "empty" in out


def test_list_teammates_tool_empty(tmp_path, monkeypatch):
    cfg, reg, bus, mgr = _setup(tmp_path, monkeypatch)
    register_team_tools(reg, cfg=cfg, llm=None, bus=bus, manager=mgr, parent_registry=reg)
    out = reg.get("ListTeammates").handler()
    assert "empty" in out


def test_broadcast_tool(tmp_path, monkeypatch):
    cfg, reg, bus, mgr = _setup(tmp_path, monkeypatch)
    mgr.register("alice", "dev")
    mgr.register("bob", "ops")
    register_team_tools(reg, cfg=cfg, llm=None, bus=bus, manager=mgr, parent_registry=reg)
    out = reg.get("Broadcast").handler(content="standup in 5")
    assert "Broadcast to 2" in out


def test_teammate_registry_whitelist(tmp_path, monkeypatch):
    """队友内部的工具集必须去掉 Write/Edit(read_only=True 时)。"""
    cfg, reg, bus, mgr = _setup(tmp_path, monkeypatch)
    from oai_code.team.loop import _build_teammate_registry

    sub = _build_teammate_registry(reg, bus, "alice", read_only=True)
    names = set(sub.names())
    assert "Read" in names and "Grep" in names and "Glob" in names and "Bash" in names
    assert "Write" not in names and "Edit" not in names
    # team 工具加进去了
    assert "SendMessage" in names and "Idle" in names


def test_teammate_registry_full_mode(tmp_path, monkeypatch):
    cfg, reg, bus, mgr = _setup(tmp_path, monkeypatch)
    from oai_code.team.loop import _build_teammate_registry

    sub = _build_teammate_registry(reg, bus, "alice", read_only=False)
    names = set(sub.names())
    assert "Write" in names and "Edit" in names


def test_teammate_send_message_uses_self_name(tmp_path, monkeypatch):
    cfg, reg, bus, mgr = _setup(tmp_path, monkeypatch)
    from oai_code.team.loop import _build_teammate_registry

    sub = _build_teammate_registry(reg, bus, "alice", read_only=True)
    send = sub.get("SendMessage")
    send.handler(to="bob", content="yo")
    assert bus.read_inbox("bob")[0]["from"] == "alice"
