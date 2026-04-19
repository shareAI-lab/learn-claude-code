"""M4-2: BackgroundKill 测试。"""
from __future__ import annotations

import time

from mycode.config import load_config
from mycode.tools.background import BackgroundManager


def _mgr(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    return BackgroundManager(cfg)


def _wait_status(mgr, tid, predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with mgr._lock:
            t = mgr._tasks.get(tid)
            if t and predicate(t):
                return t
        time.sleep(0.02)
    raise TimeoutError("wait failed")


def test_kill_running_task(tmp_path, monkeypatch):
    mgr = _mgr(tmp_path, monkeypatch)
    tid = mgr.run("sleep 30").split()[2]
    # 等 pid 填上
    _wait_status(mgr, tid, lambda t: t.pid is not None)
    out = mgr.kill(tid)
    assert out.startswith("Killed")
    task = _wait_status(mgr, tid, lambda t: t.status in ("killed", "completed", "error"))
    assert task.status == "killed"


def test_kill_unknown_id(tmp_path, monkeypatch):
    mgr = _mgr(tmp_path, monkeypatch)
    out = mgr.kill("nope")
    assert out.startswith("Error: unknown")


def test_kill_already_completed(tmp_path, monkeypatch):
    mgr = _mgr(tmp_path, monkeypatch)
    tid = mgr.run("echo done").split()[2]
    _wait_status(mgr, tid, lambda t: t.status == "completed")
    out = mgr.kill(tid)
    assert out.startswith("Error") and "cannot kill" in out


def test_kill_preserves_status_across_exec_collection(tmp_path, monkeypatch):
    """kill 标记 killed 后,_exec 的 finally 路径不应把它改回 completed。"""
    mgr = _mgr(tmp_path, monkeypatch)
    tid = mgr.run("sleep 10").split()[2]
    _wait_status(mgr, tid, lambda t: t.pid is not None)
    mgr.kill(tid)
    # 给进程点时间收尾
    time.sleep(0.3)
    with mgr._lock:
        task = mgr._tasks[tid]
        assert task.status == "killed"


def test_timeout_still_works(tmp_path, monkeypatch):
    """重构为 Popen 后 timeout 仍应工作。"""
    mgr = _mgr(tmp_path, monkeypatch)
    tid = mgr.run("sleep 5", timeout=1).split()[2]
    task = _wait_status(mgr, tid, lambda t: t.status in ("timeout", "killed"), timeout=3)
    assert task.status == "timeout"


def test_exit_code_still_captured(tmp_path, monkeypatch):
    """重构后非零 exit code 仍然附录。"""
    mgr = _mgr(tmp_path, monkeypatch)
    tid = mgr.run("false").split()[2]
    task = _wait_status(mgr, tid, lambda t: t.status == "completed")
    assert "[exit code: 1]" in task.result


def test_register_adds_kill_tool(tmp_path, monkeypatch):
    from mycode.tools.background import register_background
    from mycode.tools.registry import ToolRegistry

    mgr = _mgr(tmp_path, monkeypatch)
    reg = ToolRegistry(mgr.cfg)
    register_background(reg, mgr)
    assert reg.get("BackgroundKill") is not None
