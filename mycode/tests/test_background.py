"""M2-2: BackgroundRun / BackgroundCheck 测试。"""
from __future__ import annotations

import time

from mycode.config import load_config
from mycode.tools.background import BackgroundManager


def _mgr(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    return BackgroundManager(cfg)


def _wait_done(mgr, tid, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with mgr._lock:
            t = mgr._tasks.get(tid)
            if t and t.status in ("completed", "error", "timeout"):
                return t
        time.sleep(0.02)
    raise TimeoutError(f"task {tid} did not finish")


def test_run_returns_task_id(tmp_path, monkeypatch):
    mgr = _mgr(tmp_path, monkeypatch)
    out = mgr.run("echo hello", timeout=10, description="demo")
    assert "Background task" in out
    # 格式: "Background task <id> started: ..."
    tid = out.split()[2]
    assert len(tid) == 8


def test_task_completes(tmp_path, monkeypatch):
    mgr = _mgr(tmp_path, monkeypatch)
    out = mgr.run("echo done", timeout=10)
    tid = out.split()[2]
    task = _wait_done(mgr, tid)
    assert task.status == "completed"
    assert "done" in task.result


def test_check_known_and_unknown(tmp_path, monkeypatch):
    mgr = _mgr(tmp_path, monkeypatch)
    tid = mgr.run("echo x").split()[2]
    _wait_done(mgr, tid)
    assert "completed" in mgr.check(tid)
    assert mgr.check("nope").startswith("Error")


def test_check_all_empty_and_listed(tmp_path, monkeypatch):
    mgr = _mgr(tmp_path, monkeypatch)
    assert "no background" in mgr.check()
    mgr.run("echo y")
    out = mgr.check()
    assert "echo y" in out


def test_drain_returns_once(tmp_path, monkeypatch):
    mgr = _mgr(tmp_path, monkeypatch)
    tid = mgr.run("echo drained").split()[2]
    _wait_done(mgr, tid)
    first = mgr.drain()
    assert len(first) == 1
    assert first[0].id == tid
    # 第二次 drain 应为空
    assert mgr.drain() == []


def test_exit_code_captured(tmp_path, monkeypatch):
    mgr = _mgr(tmp_path, monkeypatch)
    tid = mgr.run("false").split()[2]
    task = _wait_done(mgr, tid)
    assert task.status == "completed"
    assert "[exit code: 1]" in task.result


def test_timeout(tmp_path, monkeypatch):
    mgr = _mgr(tmp_path, monkeypatch)
    tid = mgr.run("sleep 5", timeout=1).split()[2]
    task = _wait_done(mgr, tid, timeout=3)
    assert task.status == "timeout"
