"""M4-1: 队友 auto-compact 接入测试(signature 层面)。"""
from __future__ import annotations

import inspect

from oai_code.team.loop import start_teammate_loop
from oai_code.team.tools import register_team_tools


def test_teammate_loop_accepts_summarize_llm():
    sig = inspect.signature(start_teammate_loop)
    assert "summarize_llm" in sig.parameters
    p = sig.parameters["summarize_llm"]
    # 是 keyword-only
    assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_register_team_tools_accepts_summarize_llm():
    sig = inspect.signature(register_team_tools)
    assert "summarize_llm" in sig.parameters


def test_summarize_llm_reaches_start_call(tmp_path, monkeypatch):
    """register_team_tools → SpawnTeammate handler → start_teammate_loop
    整条链路要把 summarize_llm 传过去。用 monkeypatch 拦截 start_teammate_loop 验证。
    """
    from oai_code.config import load_config
    from oai_code.team import MessageBus, TeammateManager
    from oai_code.tools.registry import ToolRegistry

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    bus = MessageBus(cfg)
    mgr = TeammateManager(cfg=cfg)
    parent = ToolRegistry(cfg)

    captured = {}
    import oai_code.team.tools as tools_mod

    def _fake_start(**kw):
        captured.update(kw)
        class _T:
            pass
        return _T()

    monkeypatch.setattr(tools_mod, "start_teammate_loop", _fake_start)

    sentinel = object()
    reg = ToolRegistry(cfg)
    register_team_tools(
        reg,
        cfg=cfg,
        llm=None,
        bus=bus,
        manager=mgr,
        parent_registry=parent,
        summarize_llm=sentinel,
    )

    out = reg.get("SpawnTeammate").handler(
        name="alice", role="dev", prompt="hi"
    )
    assert "Spawned" in out
    assert captured.get("summarize_llm") is sentinel
