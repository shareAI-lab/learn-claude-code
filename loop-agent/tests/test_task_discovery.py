"""tests/test_task_discovery.py — 任务发现单元测试"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from triggers import TriggerEvent
from task_discovery import TaskItem, discover_from_trigger, filter_already_processed
from state import LoopState


def test_discover_ci_failure():
    """CI 失败触发应生成正确的 TaskItem。"""
    event = TriggerEvent(
        source="ci_failure",
        prompt="Fix CI failure",
        metadata={"run_id": 789},
    )
    task = discover_from_trigger(event)
    assert task.id == "ci_run_789"
    assert task.source == "ci_failure"
    assert task.branch_hint == "fix-ci-789"


def test_discover_goal():
    """Goal 触发应生成正确的 TaskItem。"""
    event = TriggerEvent(
        source="goal",
        prompt="Make all tests pass",
    )
    task = discover_from_trigger(event)
    assert task.id.startswith("goal_")
    assert task.id != "goal_task"  # 不再是固定 ID
    assert task.source == "goal"
    assert task.branch_hint.startswith("goal-")


def test_discover_goal_unique_ids():
    """不同 goal 应生成不同的 ID。"""
    event1 = TriggerEvent(source="goal", prompt="Fix tests")
    event2 = TriggerEvent(source="goal", prompt="Fix lint")
    task1 = discover_from_trigger(event1)
    task2 = discover_from_trigger(event2)
    assert task1.id != task2.id


def test_discover_cron():
    """Cron 触发应生成正确的 TaskItem。"""
    event = TriggerEvent(
        source="cron",
        prompt="Run CI check",
        metadata={"job_id": "ci_check"},
    )
    task = discover_from_trigger(event)
    assert task.id.startswith("cron_ci_check_")
    assert task.source == "cron"
    assert task.branch_hint.startswith("cron-ci_check-")


def test_discover_manual_stable_id():
    """相同 prompt 的 manual 触发应生成稳定的 ID。"""
    event1 = TriggerEvent(source="manual", prompt="Fix the login bug")
    event2 = TriggerEvent(source="manual", prompt="Fix the login bug")
    task1 = discover_from_trigger(event1)
    task2 = discover_from_trigger(event2)
    assert task1.id == task2.id
    assert task1.id.startswith("manual_")


def test_discover_manual_different_id():
    """不同 prompt 的 manual 触发应生成不同的 ID。"""
    event1 = TriggerEvent(source="manual", prompt="Fix the login bug")
    event2 = TriggerEvent(source="manual", prompt="Add dark mode")
    task1 = discover_from_trigger(event1)
    task2 = discover_from_trigger(event2)
    assert task1.id != task2.id


def test_filter_already_processed():
    """已处理的任务应被过滤。"""
    state = LoopState(processed_items=["manual_abc123"])
    items = [
        TaskItem(id="manual_abc123", source="manual", title="t1", description="d1", branch_hint="b1"),
        TaskItem(id="manual_def456", source="manual", title="t2", description="d2", branch_hint="b2"),
    ]
    filtered = filter_already_processed(items, state)
    assert len(filtered) == 1
    assert filtered[0].id == "manual_def456"


def test_filter_none_processed():
    """无已处理项时应返回全部。"""
    state = LoopState()
    items = [
        TaskItem(id="manual_abc123", source="manual", title="t1", description="d1", branch_hint="b1"),
    ]
    filtered = filter_already_processed(items, state)
    assert len(filtered) == 1
