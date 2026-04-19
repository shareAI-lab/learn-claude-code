"""M5-1: Worktree 工具测试。真实调 git worktree(需要系统有 git)。"""
from __future__ import annotations

import subprocess

import pytest

from oai_code.config import load_config
from oai_code.tools.registry import ToolRegistry
from oai_code.tools.worktree import (
    _load_state,
    _run_enter,
    _run_exit,
    _run_status,
    register_worktree,
)


def _have_git() -> bool:
    try:
        r = subprocess.run(["git", "--version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _have_git(), reason="git not available")


def _init_repo(path):
    """在 tmp_path 初始化一个有 1 个 commit 的 git 仓库。"""
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)
    (path / "hello.txt").write_text("hi\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


def _cfg(tmp_path, monkeypatch):
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    return load_config(cli_overrides={"model": "test", "provider": "custom"})


def test_status_without_session(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    out = _run_status(cfg)
    assert "Not in a worktree" in out


def test_enter_creates_worktree_and_changes_root(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    out = _run_enter(cfg, name="feature-x")
    assert "Entered worktree 'feature-x'" in out
    # 实际目录存在
    wt = tmp_path / ".oaic" / "worktrees" / "feature-x"
    assert wt.is_dir()
    # workspace_root 被改了
    assert cfg.workspace_root() == wt
    # state 持久化
    state = _load_state(cfg)
    assert state["active"] is True
    assert state["name"] == "feature-x"
    assert state["branch"] == "oaic/feature-x"


def test_enter_twice_rejected(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    _run_enter(cfg, name="a")
    out = _run_enter(cfg, name="b")
    assert out.startswith("Error: already in a worktree")


def test_invalid_name_rejected(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    out = _run_enter(cfg, name="bad name with spaces")
    assert out.startswith("Error: invalid worktree name")


def test_non_git_repo_rejected(tmp_path, monkeypatch):
    # 不调 _init_repo
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    out = _run_enter(cfg)
    assert out.startswith("Error: not inside a git repo")


def test_exit_keep_preserves_dir(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    _run_enter(cfg, name="keep-me")
    wt = tmp_path / ".oaic" / "worktrees" / "keep-me"
    out = _run_exit(cfg, action="keep")
    assert "Exited" in out
    # dir 仍存在
    assert wt.is_dir()
    # state 已清
    assert not _load_state(cfg).get("active")
    # workspace_root 恢复
    assert cfg.workspace_root() == tmp_path


def test_exit_remove_clean_worktree(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    _run_enter(cfg, name="rm-me")
    wt = tmp_path / ".oaic" / "worktrees" / "rm-me"
    out = _run_exit(cfg, action="remove")
    assert "Exited and removed" in out
    assert not wt.exists()


def test_exit_remove_rejects_dirty(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    _run_enter(cfg, name="dirty")
    wt = tmp_path / ".oaic" / "worktrees" / "dirty"
    (wt / "new.txt").write_text("uncommitted\n")
    out = _run_exit(cfg, action="remove")
    assert out.startswith("Error: worktree 'dirty' has uncommitted")
    assert wt.is_dir()  # 未被删


def test_exit_remove_with_discard(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    _run_enter(cfg, name="force-rm")
    wt = tmp_path / ".oaic" / "worktrees" / "force-rm"
    (wt / "new.txt").write_text("uncommitted\n")
    out = _run_exit(cfg, action="remove", discard_changes=True)
    assert "removed" in out
    assert not wt.exists()


def test_exit_without_enter(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    out = _run_exit(cfg)
    assert out.startswith("Error: not in a worktree session")


def test_exit_invalid_action(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    _run_enter(cfg)
    out = _run_exit(cfg, action="nuke")
    assert out.startswith("Error: action must be")


def test_tools_registered(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    reg = ToolRegistry(cfg)
    register_worktree(reg, cfg)
    assert reg.get("EnterWorktree") is not None
    assert reg.get("ExitWorktree") is not None
    assert reg.get("WorktreeStatus") is not None
