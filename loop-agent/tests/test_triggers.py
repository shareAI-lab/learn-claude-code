"""tests/test_triggers.py — 四种触发源测试"""

import pytest
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_manual_enqueue_and_check():
    """手动触发：入队后应能取出。"""
    from triggers import enqueue_manual, check_manual
    enqueue_manual("test task")
    event = check_manual()
    assert event is not None
    assert event.source == "manual"
    assert event.prompt == "test task"


def test_manual_empty_queue():
    """空队列应返回 None。"""
    from triggers import check_manual
    event = check_manual()
    assert event is None


def test_cron_field_matches():
    """cron 字段匹配测试。"""
    from triggers import _cron_field_matches
    assert _cron_field_matches("*", 30) is True
    assert _cron_field_matches("*/5", 15) is True
    assert _cron_field_matches("*/5", 13) is False
    assert _cron_field_matches("1,3,5", 3) is True
    assert _cron_field_matches("1,3,5", 4) is False
    assert _cron_field_matches("1-5", 3) is True
    assert _cron_field_matches("1-5", 6) is False
    assert _cron_field_matches("30", 30) is True
    assert _cron_field_matches("30", 31) is False


def test_cron_matches():
    """完整 cron 表达式匹配测试。"""
    from triggers import cron_matches
    # 每小时第 0 分钟
    dt = datetime(2025, 6, 15, 10, 0)
    assert cron_matches("0 * * * *", dt) is True
    assert cron_matches("30 * * * *", dt) is False

    # 每 6 小时
    dt = datetime(2025, 6, 15, 12, 0)
    assert cron_matches("0 */6 * * *", dt) is True
    dt = datetime(2025, 6, 15, 13, 0)
    assert cron_matches("0 */6 * * *", dt) is False


def test_cron_matches_invalid():
    """无效 cron 表达式应返回 False。"""
    from triggers import cron_matches
    dt = datetime(2025, 6, 15, 10, 0)
    assert cron_matches("invalid", dt) is False
    assert cron_matches("1 2 3", dt) is False


def test_goal_trigger_success():
    """Goal 触发：验证命令成功（exit 0）应返回 None。"""
    from triggers import check_goal
    event = check_goal("echo ok")
    assert event is None


def test_goal_trigger_failure():
    """Goal 触发：验证命令失败（exit 1）应返回事件。"""
    from triggers import check_goal
    event = check_goal("false")  # `false` 命令返回 exit 1
    assert event is not None
    assert event.source == "goal"


def test_ci_failure_trigger():
    """CI 失败触发：mock 数据应返回事件。"""
    from triggers import check_ci_failure, _last_ci_run_id
    # 重置全局状态
    import triggers
    triggers._last_ci_run_id = 0

    event = check_ci_failure()
    assert event is not None
    assert event.source == "ci_failure"
    assert "CI run #789" in event.prompt


def test_check_all_triggers_priority():
    """聚合检查：手动触发优先级最高。"""
    from triggers import enqueue_manual, check_all_triggers
    enqueue_manual("priority test")
    event = check_all_triggers()
    assert event is not None
    assert event.source == "manual"


def test_is_shell_command():
    """shell 命令检测：应区分命令和自然语言。"""
    from triggers import _is_shell_command
    # 确定是命令
    assert _is_shell_command("python -m pytest") is True
    assert _is_shell_command("npm run build") is True
    assert _is_shell_command("git status") is True
    assert _is_shell_command("./run.sh") is True
    assert _is_shell_command("echo hello") is True
    assert _is_shell_command("ls -la") is True
    # 路径 + 扩展名
    assert _is_shell_command("python loop-agent/tests/test.py") is True
    # shell 操作符
    assert _is_shell_command("echo a && echo b") is True
    # 确定是自然语言
    assert _is_shell_command("检测项目完整性") is False
    assert _is_shell_command("请帮我修复这个 bug") is False
    assert _is_shell_command("What is the project structure?") is False


def test_is_shell_command_no_false_positive():
    """shell 命令检测：不应将自然语言误判为命令。"""
    from triggers import _is_shell_command
    # "make" 是 shell 前缀，但这些是自然语言
    assert _is_shell_command("Make the code faster") is False
    assert _is_shell_command("Fix all failing tests") is False
    assert _is_shell_command("Add error handling to the API") is False
    assert _is_shell_command("Remove unused imports") is False
    assert _is_shell_command("Update the README") is False


def test_goal_natural_language():
    """自然语言 Goal：应直接返回 TriggerEvent，不执行 shell。"""
    from triggers import check_goal
    event = check_goal("检测项目完整性")
    assert event is not None
    assert event.source == "goal"
    assert event.prompt == "检测项目完整性"
