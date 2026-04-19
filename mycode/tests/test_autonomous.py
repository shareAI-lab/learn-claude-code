"""M3-6: 自治 idle + ClaimTask + 身份重注入。"""
from __future__ import annotations

import json

from mycode.agent.loop import AgentState
from mycode.config import load_config
from mycode.team import MessageBus, TeammateManager
from mycode.team.loop import (
    _build_teammate_registry,
    _claim_task,
    _reinject_identity,
    _try_autoclaim,
)
from mycode.tools.registry import ToolRegistry
from mycode.tools.tasks import TaskStore


def _setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    bus = MessageBus(cfg)
    mgr = TeammateManager(cfg=cfg)
    parent = ToolRegistry(cfg)
    store = TaskStore(cfg)
    return cfg, bus, mgr, parent, store


# ---------- ClaimTask ----------

def test_claim_registers_tool(tmp_path, monkeypatch):
    _, bus, _, parent, store = _setup(tmp_path, monkeypatch)
    sub = _build_teammate_registry(parent, bus, "alice", task_store=store)
    assert sub.get("ClaimTask") is not None


def test_claim_unclaimed_task(tmp_path, monkeypatch):
    _, _, _, _, store = _setup(tmp_path, monkeypatch)
    store.create("do something")
    out = _claim_task(store, "alice", 1)
    task = json.loads(out)
    assert task["owner"] == "alice"
    assert task["status"] == "in_progress"


def test_claim_already_owned(tmp_path, monkeypatch):
    _, _, _, _, store = _setup(tmp_path, monkeypatch)
    store.create("x")
    _claim_task(store, "alice", 1)
    out = _claim_task(store, "bob", 1)
    assert out.startswith("Error: task 1 already owned")


def test_claim_reclaim_by_same_owner_ok(tmp_path, monkeypatch):
    _, _, _, _, store = _setup(tmp_path, monkeypatch)
    store.create("x")
    _claim_task(store, "alice", 1)
    out = _claim_task(store, "alice", 1)
    # 同一人再次 claim 应该仍 ok (幂等)
    assert not out.startswith("Error")


def test_claim_blocked(tmp_path, monkeypatch):
    _, _, _, _, store = _setup(tmp_path, monkeypatch)
    store.create("a")
    store.create("b")
    store.update(2, add_blocked_by=[1])
    out = _claim_task(store, "alice", 2)
    assert "blocked by" in out


def test_claim_unknown_task(tmp_path, monkeypatch):
    _, _, _, _, store = _setup(tmp_path, monkeypatch)
    out = _claim_task(store, "alice", 999)
    assert "not found" in out or out.startswith("Error")


# ---------- auto-claim during idle ----------

def test_try_autoclaim_picks_first(tmp_path, monkeypatch):
    _, _, _, _, store = _setup(tmp_path, monkeypatch)
    store.create("first")
    store.create("second")
    state = AgentState()
    claimed = _try_autoclaim(store, "alice", state)
    assert claimed
    # 第一条被认了
    task1 = json.loads(store.get(1))
    assert task1["owner"] == "alice"
    task2 = json.loads(store.get(2))
    assert task2.get("owner") is None
    # state 里注入了 auto-claimed 标记
    assert any("auto-claimed" in (m.get("content") or "") for m in state.messages)


def test_try_autoclaim_skips_owned(tmp_path, monkeypatch):
    _, _, _, _, store = _setup(tmp_path, monkeypatch)
    store.create("taken")
    store.update(1, owner="bob")
    state = AgentState()
    claimed = _try_autoclaim(store, "alice", state)
    assert not claimed


def test_try_autoclaim_skips_blocked(tmp_path, monkeypatch):
    _, _, _, _, store = _setup(tmp_path, monkeypatch)
    store.create("a")
    store.create("b")
    store.update(2, add_blocked_by=[1])
    state = AgentState()
    # 先 claim #1
    _try_autoclaim(store, "alice", state)
    # #2 被 blocked,第二次 autoclaim 应返回 False
    state2 = AgentState()
    claimed = _try_autoclaim(store, "bob", state2)
    assert not claimed


def test_try_autoclaim_empty_board(tmp_path, monkeypatch):
    _, _, _, _, store = _setup(tmp_path, monkeypatch)
    state = AgentState()
    assert not _try_autoclaim(store, "alice", state)


# ---------- identity re-injection ----------

def test_reinject_when_short(tmp_path, monkeypatch):
    state = AgentState()
    state.messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "x"},
    ]
    _reinject_identity(state, "alice", "backend")
    assert any("<identity>" in m.get("content", "") for m in state.messages)


def test_no_reinject_when_long(tmp_path, monkeypatch):
    state = AgentState()
    state.messages = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
    before = len(state.messages)
    _reinject_identity(state, "alice", "backend")
    assert len(state.messages) == before  # 没追加
