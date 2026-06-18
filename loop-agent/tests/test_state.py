"""tests/test_state.py — 状态文件读写测试"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def tmp_state(tmp_path):
    """创建临时状态环境。"""
    state_file = tmp_path / ".loop-state.json"
    with patch("state.STATE_FILE", state_file):
        from state import LoopState
        yield LoopState(), state_file


def test_load_state_empty(tmp_state):
    """空文件应返回默认状态。"""
    _, state_file = tmp_state
    from state import load_state
    state = load_state()
    assert state.version == 1
    assert state.processed_items == []
    assert state.history == []


def test_save_and_load(tmp_state):
    """保存后应能正确加载。"""
    _, state_file = tmp_state
    from state import load_state, save_state, LoopState
    state = LoopState()
    state.processed_items.append("test_item")
    state.last_run_ts = 1234567890.0
    save_state(state)

    loaded = load_state()
    assert "test_item" in loaded.processed_items
    assert loaded.last_run_ts == 1234567890.0


def test_record_cycle(tmp_state):
    """record_cycle 应添加历史记录。"""
    _, state_file = tmp_state
    from state import load_state, record_cycle
    state = load_state()
    record_cycle(state, "task_1", "approved", "Looks good")

    assert len(state.history) == 1
    assert state.history[0]["task_id"] == "task_1"
    assert state.history[0]["status"] == "approved"


def test_mark_processed(tmp_state):
    """mark_processed 应去重添加。"""
    _, state_file = tmp_state
    from state import load_state, mark_processed
    state = load_state()
    mark_processed(state, "item_1")
    mark_processed(state, "item_1")  # 重复

    assert state.processed_items.count("item_1") == 1


def test_atomic_write(tmp_state):
    """原子写入：不应留下 .tmp 文件。"""
    _, state_file = tmp_state
    from state import load_state, save_state, LoopState
    state = LoopState()
    save_state(state)

    assert state_file.exists()
    assert not state_file.with_suffix(".tmp").exists()


def test_add_worktree(tmp_state):
    """add_worktree 应去重添加 worktree。"""
    _, state_file = tmp_state
    from state import load_state, add_worktree
    state = load_state()
    add_worktree(state, "wt_test")
    add_worktree(state, "wt_test")  # 重复

    assert state.active_worktrees.count("wt_test") == 1


def test_remove_worktree(tmp_state):
    """remove_worktree 应移除 worktree。"""
    _, state_file = tmp_state
    from state import load_state, add_worktree, remove_worktree
    state = load_state()
    add_worktree(state, "wt_test")
    remove_worktree(state, "wt_test")

    assert "wt_test" not in state.active_worktrees


def test_remove_worktree_nonexistent(tmp_state):
    """移除不存在的 worktree 不应报错。"""
    _, state_file = tmp_state
    from state import load_state, remove_worktree
    state = load_state()
    remove_worktree(state, "nonexistent")  # 不应抛出异常


def test_add_error(tmp_state):
    """add_error 应记录错误到 error_log。"""
    _, state_file = tmp_state
    from state import load_state, add_error
    state = load_state()
    add_error(state, "task_1", "Something went wrong")

    assert len(state.error_log) == 1
    assert state.error_log[0]["task_id"] == "task_1"
    assert state.error_log[0]["error"] == "Something went wrong"


def test_load_state_corrupted(tmp_path):
    """损坏的状态文件应返回默认状态并打印警告。"""
    state_file = tmp_path / ".loop-state.json"
    state_file.write_text("not valid json{{{", encoding="utf-8")

    with patch("state.STATE_FILE", state_file):
        from state import load_state
        state = load_state()

    assert state.version == 1
    assert state.processed_items == []


def test_remove_worktree_save_false(tmp_path):
    """remove_worktree(_save=False) 不应写入文件。"""
    state_file = tmp_path / ".loop-state.json"
    with patch("state.STATE_FILE", state_file):
        from state import LoopState, add_worktree, remove_worktree, save_state

        state = LoopState()
        add_worktree(state, "wt1")
        assert "wt1" in state.active_worktrees

        # _save=False：对象中移除了，但不写文件
        remove_worktree(state, "wt1", _save=False)
        assert "wt1" not in state.active_worktrees


def test_record_cycle_updates_last_run_ts(tmp_path):
    """record_cycle 应更新 last_run_ts。"""
    state_file = tmp_path / ".loop-state.json"
    with patch("state.STATE_FILE", state_file):
        from state import LoopState, record_cycle

        state = LoopState()
        assert state.last_run_ts == 0.0

        record_cycle(state, "task1", "approved", _save=False)
        assert state.last_run_ts > 0.0
