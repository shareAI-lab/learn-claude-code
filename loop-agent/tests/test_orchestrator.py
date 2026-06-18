"""tests/test_orchestrator.py — 编排器端到端测试"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_state(tmp_path):
    """创建临时状态。"""
    state_file = tmp_path / ".loop-state.json"
    with patch("config.STATE_FILE", state_file):
        with patch("config.STATE_DIR", tmp_path):
            from state import LoopState
            yield LoopState()


def test_cycle_result_dataclass():
    """CycleResult 数据结构测试。"""
    from orchestrator import CycleResult
    result = CycleResult(
        cycle_id=1,
        task_id="test_1",
        trigger_source="manual",
        final_status="approved",
    )
    assert result.cycle_id == 1
    assert result.final_status == "approved"


@patch("orchestrator.discover_from_trigger")
@patch("orchestrator.run_maker")
@patch("orchestrator.run_checker")
def test_orchestrate_approved(mock_checker, mock_maker, mock_discover, mock_state):
    """完整循环：Maker 成功 + Checker 通过。"""
    from orchestrator import orchestrate_cycle
    from triggers import TriggerEvent
    from loop_agent import MakerResult, CheckerResult
    from task_discovery import TaskItem

    mock_discover.return_value = TaskItem(
        id="manual_test", source="manual",
        title="test task", description="test task",
        branch_hint="test",
    )
    mock_maker.return_value = MakerResult(
        success=True,
        diff_stat="1 file changed",
        test_output="",
        summary="Done",
        worktree_name="test",
    )
    mock_checker.return_value = CheckerResult(
        approved=True,
        feedback="Looks good",
        issues=[],
    )

    event = TriggerEvent(source="manual", prompt="test task")
    result = orchestrate_cycle(event, mock_state)

    assert result.final_status == "approved"
    assert "manual_test" in mock_state.processed_items


@patch("orchestrator.discover_from_trigger")
@patch("orchestrator.run_maker")
@patch("orchestrator.run_checker")
def test_orchestrate_rejected(mock_checker, mock_maker, mock_discover, mock_state):
    """完整循环：Maker 成功 + Checker 拒绝。"""
    from orchestrator import orchestrate_cycle
    from triggers import TriggerEvent
    from loop_agent import MakerResult, CheckerResult
    from task_discovery import TaskItem

    mock_discover.return_value = TaskItem(
        id="manual_test", source="manual",
        title="test task", description="test task",
        branch_hint="test",
    )
    mock_maker.return_value = MakerResult(
        success=True,
        diff_stat="1 file changed",
        test_output="",
        summary="Done",
        worktree_name="test",
    )
    mock_checker.return_value = CheckerResult(
        approved=False,
        feedback="Needs work",
        issues=["Missing tests"],
    )

    event = TriggerEvent(source="manual", prompt="test task")
    result = orchestrate_cycle(event, mock_state)

    assert result.final_status == "rejected"
    assert "manual_test" not in mock_state.processed_items


@patch("orchestrator.discover_from_trigger")
@patch("orchestrator.run_maker")
def test_orchestrate_maker_failure(mock_maker, mock_discover, mock_state):
    """完整循环：Maker 失败。"""
    from orchestrator import orchestrate_cycle
    from triggers import TriggerEvent
    from loop_agent import MakerResult
    from task_discovery import TaskItem

    mock_discover.return_value = TaskItem(
        id="manual_test", source="manual",
        title="test task", description="test task",
        branch_hint="test",
    )
    mock_maker.return_value = MakerResult(
        success=False,
        diff_stat="",
        test_output="",
        summary="Worktree creation failed",
        worktree_name="",
    )

    event = TriggerEvent(source="manual", prompt="test task")
    result = orchestrate_cycle(event, mock_state)

    assert result.final_status == "needs_human"
    assert len(mock_state.error_log) > 0


@patch("orchestrator.discover_from_trigger")
@patch("orchestrator.run_maker")
@patch("orchestrator.run_checker")
def test_orchestrate_three_rejections(mock_checker, mock_maker, mock_discover, mock_state):
    """3 次拒绝应标记 needs_human。"""
    from orchestrator import orchestrate_cycle
    from triggers import TriggerEvent
    from loop_agent import MakerResult, CheckerResult
    from state import record_cycle
    from task_discovery import TaskItem

    mock_discover.return_value = TaskItem(
        id="manual_test", source="manual",
        title="test task", description="test task",
        branch_hint="test",
    )
    mock_maker.return_value = MakerResult(
        success=True,
        diff_stat="1 file changed",
        test_output="",
        summary="Done",
        worktree_name="test",
    )
    mock_checker.return_value = CheckerResult(
        approved=False,
        feedback="Still broken",
        issues=["Still broken"],
    )

    # 先记录 3 次拒绝（MAX_CHECKER_RETRIES=3）
    record_cycle(mock_state, "manual_test", "rejected", "attempt 1")
    record_cycle(mock_state, "manual_test", "rejected", "attempt 2")
    record_cycle(mock_state, "manual_test", "rejected", "attempt 3")

    event = TriggerEvent(source="manual", prompt="test task")
    result = orchestrate_cycle(event, mock_state)

    assert result.final_status == "needs_human"


def test_filter_already_processed(mock_state):
    """已处理的任务应被跳过。"""
    from orchestrator import orchestrate_cycle
    from triggers import TriggerEvent
    from state import mark_processed

    mark_processed(mock_state, "manual_test")

    event = TriggerEvent(source="manual", prompt="test task")
    with patch("orchestrator.discover_from_trigger") as mock_discover:
        from task_discovery import TaskItem
        mock_discover.return_value = TaskItem(
            id="manual_test", source="manual",
            title="test", description="test",
            branch_hint="test",
        )
        result = orchestrate_cycle(event, mock_state)

    assert result.final_status == "skipped"


@patch("orchestrator.discover_from_trigger")
@patch("orchestrator.run_maker")
@patch("orchestrator.run_checker")
def test_total_tokens_in_result(mock_checker, mock_maker, mock_discover, mock_state):
    """CycleResult 应包含 total_tokens。"""
    from orchestrator import orchestrate_cycle
    from triggers import TriggerEvent
    from loop_agent import MakerResult, CheckerResult
    from task_discovery import TaskItem

    mock_discover.return_value = TaskItem(
        id="manual_test", source="manual",
        title="test task", description="test task",
        branch_hint="test",
    )
    mock_maker.return_value = MakerResult(
        success=True, diff_stat="1 file changed", test_output="",
        summary="Done", worktree_name="test", tokens_used=1000,
    )
    mock_checker.return_value = CheckerResult(
        approved=True, feedback="Looks good", issues=[],
        verdict="APPROVED", tokens_used=500,
    )

    event = TriggerEvent(source="manual", prompt="test task")
    result = orchestrate_cycle(event, mock_state)

    assert result.total_tokens == 1500


@patch("orchestrator.check_all_triggers")
def test_run_loop_once_no_triggers(mock_triggers):
    """run_loop(mode='once') 无触发时立即停止。"""
    from orchestrator import run_loop

    mock_triggers.return_value = None
    results = run_loop(mode="once", max_cycles=5)
    assert len(results) == 0
