"""M1-3: 持久化 Tasks 测试。"""
from __future__ import annotations

import json

from oai_code.config import load_config
from oai_code.tools.tasks import TaskStore


def _store(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    return TaskStore(cfg)


def test_create_and_get(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    out = s.create("write docs", "write docs for M1")
    task = json.loads(out)
    assert task["id"] == 1
    assert task["status"] == "pending"
    assert task["subject"] == "write docs"

    got = json.loads(s.get(1))
    assert got["id"] == 1


def test_create_reject_empty(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    assert s.create("   ").startswith("Error")


def test_list_ordering(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    s.create("a")
    s.create("b")
    out = s.list_all()
    assert "#1: a" in out
    assert "#2: b" in out


def test_update_status(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    s.create("x")
    out = json.loads(s.update(1, status="in_progress"))
    assert out["status"] == "in_progress"


def test_update_invalid_status(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    s.create("x")
    out = s.update(1, status="weird")
    assert "invalid status" in out


def test_cascade_unblock(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    s.create("a")
    s.create("b")
    s.update(2, add_blocked_by=[1])
    b = json.loads(s.get(2))
    assert b["blockedBy"] == [1]
    s.update(1, status="completed")
    b = json.loads(s.get(2))
    assert b["blockedBy"] == []


def test_delete_removes_file(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    s.create("x")
    assert (tmp_path / ".oaic" / "tasks" / "task_1.json").exists()
    s.update(1, status="deleted")
    assert not (tmp_path / ".oaic" / "tasks" / "task_1.json").exists()


def test_get_missing(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    assert "not found" in s.get(99)


def test_add_remove_blocked_by(tmp_path, monkeypatch):
    s = _store(tmp_path, monkeypatch)
    s.create("a")
    s.update(1, add_blocked_by=[2, 3])
    t = json.loads(s.get(1))
    assert t["blockedBy"] == [2, 3]
    s.update(1, remove_blocked_by=[2])
    t = json.loads(s.get(1))
    assert t["blockedBy"] == [3]
