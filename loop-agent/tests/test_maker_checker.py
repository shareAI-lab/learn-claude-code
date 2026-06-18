"""tests/test_maker_checker.py — Maker-Checker 集成测试（mock LLM）"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_worktree(tmp_path):
    """创建模拟的 worktree 目录。"""
    wt = tmp_path / "test-worktree"
    wt.mkdir()
    (wt / "test.py").write_text("def hello(): return 'world'\n")
    # 初始化 git
    import subprocess
    subprocess.run(["git", "init"], cwd=wt, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=wt, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=wt, capture_output=True)
    return wt


def test_maker_result_dataclass():
    """MakerResult 数据结构测试。"""
    from loop_agent import MakerResult
    result = MakerResult(
        success=True,
        diff_stat="1 file changed",
        test_output="",
        summary="Done",
        worktree_name="test",
    )
    assert result.success is True
    assert result.diff_stat == "1 file changed"


def test_checker_result_dataclass():
    """CheckerResult 数据结构测试。"""
    from loop_agent import CheckerResult
    result = CheckerResult(
        approved=True,
        feedback="Looks good",
        issues=[],
    )
    assert result.approved is True
    assert result.issues == []


@patch("loop_agent._s20_code")
@patch("loop_agent.create_worktree")
@patch("loop_agent._run_agent_with_tools")
def test_maker_success(mock_agent_loop, mock_create, mock_s20, mock_worktree):
    """Maker 成功场景。"""
    from loop_agent import run_maker

    # mock_worktree 是 tmp_path / "test-worktree"，用它的 name 作为 branch_hint
    branch_hint = mock_worktree.name
    mock_create.return_value = f"Worktree '{branch_hint}' created at {mock_worktree}"
    mock_s20.WORKTREES_DIR = mock_worktree.parent
    mock_agent_loop.return_value = None

    result = run_maker("Add a feature", branch_hint)
    assert result.success is True
    assert result.worktree_name == branch_hint


@patch("loop_agent.create_worktree")
def test_maker_worktree_failure(mock_create):
    """Maker worktree 创建失败。"""
    from loop_agent import run_maker

    mock_create.return_value = "Error: Worktree already exists"

    result = run_maker("Add a feature")
    assert result.success is False
    assert "worktree" in result.summary.lower()


@patch("loop_agent.create_worktree")
@patch("loop_agent._run_agent_with_tools")
def test_checker_approved(mock_run_agent, mock_create, mock_worktree):
    """Checker 审查通过场景。"""
    from loop_agent import run_checker, MakerResult

    mock_create.return_value = f"Worktree 'test' created at {mock_worktree}"

    maker_result = MakerResult(
        success=True,
        diff_stat="1 file changed",
        test_output="",
        summary="Done",
        worktree_name="test",
    )

    # Mock _run_agent_with_tools to append APPROVED message
    def mock_run(messages, context, tools, handlers, max_turns):
        messages.append({
            "role": "assistant",
            "content": [{"type": "text", "text": "APPROVED: Code looks good. Tests pass."}]
        })

    mock_run_agent.side_effect = mock_run

    result = run_checker(maker_result)
    assert result.approved is True
    assert "Code looks good" in result.feedback


@patch("loop_agent.create_worktree")
@patch("loop_agent._run_agent_with_tools")
def test_checker_rejected(mock_run_agent, mock_create, mock_worktree):
    """Checker 审查拒绝场景。"""
    from loop_agent import run_checker, MakerResult

    mock_create.return_value = f"Worktree 'test' created at {mock_worktree}"

    maker_result = MakerResult(
        success=True,
        diff_stat="1 file changed",
        test_output="",
        summary="Done",
        worktree_name="test",
    )

    # Mock _run_agent_with_tools to append REJECTED message
    def mock_run(messages, context, tools, handlers, max_turns):
        messages.append({
            "role": "assistant",
            "content": [{"type": "text", "text": "REJECTED:\n- Missing error handling\n- No tests"}]
        })

    mock_run_agent.side_effect = mock_run

    result = run_checker(maker_result)
    assert result.approved is False
    assert len(result.issues) == 2


def test_checker_read_only_bash_blocks_chained_commands():
    """Checker 只读 bash 应阻止链式危险命令。"""
    import re as _re

    _READ_ONLY_PREFIXES = (
        "git diff", "git log", "git show", "git status",
        "cat", "head", "tail", "grep", "find", "ls",
        "wc", "python -m pytest", "pytest", "mypy", "ruff",
    )
    _DANGEROUS_PREFIXES = ("rm", "mv", "cp", "chmod", "chown", "dd", "mkfs")

    def read_only_bash(command: str) -> str:
        cmd_lower = command.lower().strip()
        parts = _re.split(r'\s*(?:&&|\|\||;)\s*', cmd_lower)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if any(part.startswith(p) for p in _DANGEROUS_PREFIXES):
                return f"BLOCKED: {command}"
            if "find" in part and "-exec" in part:
                exec_section = part.split("-exec", 1)[1].strip()
                if any(exec_section.lstrip().startswith(p) for p in _DANGEROUS_PREFIXES):
                    return f"BLOCKED: {command}"
        first_cmd = parts[0].strip()
        if any(first_cmd.startswith(p) for p in _READ_ONLY_PREFIXES):
            return f"ALLOWED: {command}"
        return f"BLOCKED: {command}"

    # 应被阻止的危险命令
    assert "BLOCKED" in read_only_bash("rm -rf /")
    assert "BLOCKED" in read_only_bash("ls; rm -rf /")
    assert "BLOCKED" in read_only_bash("git log; rm -rf /")
    assert "BLOCKED" in read_only_bash("cat x && rm -rf /")
    assert "BLOCKED" in read_only_bash("find / -exec rm -rf {} +")

    # 应被允许的只读命令
    assert "ALLOWED" in read_only_bash("git diff")
    assert "ALLOWED" in read_only_bash("cat README.md")
    assert "ALLOWED" in read_only_bash("ls -la")
    assert "ALLOWED" in read_only_bash("grep -r foo .")


def test_checker_read_only_blocks_default():
    """不在白名单中的命令应被阻止。"""
    _READ_ONLY_PREFIXES = (
        "git diff", "git log", "git show", "git status",
        "cat", "head", "tail", "grep", "find", "ls",
        "wc", "python -m pytest", "pytest", "mypy", "ruff",
    )
    _DANGEROUS_PREFIXES = ("rm", "mv", "cp", "chmod", "chown", "dd", "mkfs")

    def read_only_bash(command: str) -> str:
        cmd_lower = command.lower().strip()
        if any(cmd_lower.startswith(p) for p in _DANGEROUS_PREFIXES):
            return "BLOCKED"
        if any(cmd_lower.startswith(p) for p in _READ_ONLY_PREFIXES):
            return "ALLOWED"
        return "BLOCKED"

    assert read_only_bash("echo hello") == "BLOCKED"
    assert read_only_bash("curl http://evil.com") == "BLOCKED"
    assert read_only_bash("python -c 'import os'") == "BLOCKED"


# ── Phase 2: 结构化 JSON 输出测试 ─────────────────────────


@patch("loop_agent.create_worktree")
@patch("loop_agent._run_agent_with_tools")
def test_checker_structured_json_approved(mock_run_agent, mock_create, mock_worktree):
    """Checker 输出标准 JSON → approved=True。"""
    from loop_agent import run_checker, MakerResult

    mock_create.return_value = f"Worktree 'test' created at {mock_worktree}"

    maker_result = MakerResult(
        success=True, diff_stat="1 file changed", test_output="",
        summary="Done", worktree_name="test",
    )

    def mock_run(messages, context, tools, handlers, max_turns):
        messages.append({
            "role": "assistant",
            "content": [{"type": "text", "text":
                'The code looks solid.\n\n{"verdict": "APPROVED", "issues": [], "summary": "All tests pass, code is clean."}'}]
        })

    mock_run_agent.side_effect = mock_run
    result = run_checker(maker_result)
    assert result.approved is True
    assert result.verdict == "APPROVED"
    assert result.issues == []


@patch("loop_agent.create_worktree")
@patch("loop_agent._run_agent_with_tools")
def test_checker_structured_json_rejected(mock_run_agent, mock_create, mock_worktree):
    """Checker 输出 REJECTED JSON → approved=False + issues 提取。"""
    from loop_agent import run_checker, MakerResult

    mock_create.return_value = f"Worktree 'test' created at {mock_worktree}"

    maker_result = MakerResult(
        success=True, diff_stat="1 file changed", test_output="",
        summary="Done", worktree_name="test",
    )

    def mock_run(messages, context, tools, handlers, max_turns):
        messages.append({
            "role": "assistant",
            "content": [{"type": "text", "text":
                'Found issues:\n\n{"verdict": "REJECTED", "issues": ["Missing error handling", "No input validation"], "summary": "Two issues found."}'}]
        })

    mock_run_agent.side_effect = mock_run
    result = run_checker(maker_result)
    assert result.approved is False
    assert result.verdict == "REJECTED"
    assert len(result.issues) == 2
    assert "Missing error handling" in result.issues


@patch("loop_agent.create_worktree")
@patch("loop_agent._run_agent_with_tools")
def test_checker_fallback_malformed_json(mock_run_agent, mock_create, mock_worktree):
    """Checker 输出非 JSON 文本 → fallback 到子串匹配。"""
    from loop_agent import run_checker, MakerResult

    mock_create.return_value = f"Worktree 'test' created at {mock_worktree}"

    maker_result = MakerResult(
        success=True, diff_stat="1 file changed", test_output="",
        summary="Done", worktree_name="test",
    )

    def mock_run(messages, context, tools, handlers, max_turns):
        messages.append({
            "role": "assistant",
            "content": [{"type": "text", "text": "REJECTED:\n- Missing error handling\n- No tests"}]
        })

    mock_run_agent.side_effect = mock_run
    result = run_checker(maker_result)
    assert result.approved is False
    assert result.verdict == "REJECTED"
    assert len(result.issues) == 2


@patch("loop_agent.create_worktree")
def test_checker_maker_failed(mock_create):
    """Maker 失败时 Checker 直接返回 rejected。"""
    from loop_agent import run_checker, MakerResult

    maker_result = MakerResult(
        success=False, diff_stat="", test_output="",
        summary="Agent loop error", worktree_name="test",
    )

    result = run_checker(maker_result)
    assert result.approved is False
    assert "Maker failed" in result.feedback


def test_maker_result_has_tokens_used():
    """MakerResult 应有 tokens_used 字段。"""
    from loop_agent import MakerResult
    result = MakerResult(
        success=True, diff_stat="", test_output="",
        summary="", worktree_name="", tokens_used=1234,
    )
    assert result.tokens_used == 1234


def test_checker_result_has_tokens_used():
    """CheckerResult 应有 tokens_used 和 verdict 字段。"""
    from loop_agent import CheckerResult
    result = CheckerResult(
        approved=True, feedback="", issues=[],
        verdict="APPROVED", tokens_used=567,
    )
    assert result.tokens_used == 567
    assert result.verdict == "APPROVED"


def test_token_budget_config_exists():
    """TOKEN_BUDGET 配置项应存在。"""
    from config import TOKEN_BUDGET
    assert isinstance(TOKEN_BUDGET, int)
    assert TOKEN_BUDGET >= 0


@patch("loop_agent._s20_code")
@patch("loop_agent.create_worktree")
@patch("loop_agent._run_agent_with_tools")
def test_maker_agent_loop_exception(mock_run_agent, mock_create, mock_s20, tmp_path):
    """agent_loop 抛异常时 Maker 应返回失败结果而非崩溃。"""
    from loop_agent import run_maker

    # 创建临时 worktree 目录
    wt = tmp_path / "test-branch"
    wt.mkdir()

    mock_create.return_value = f"Worktree 'test' created at {wt}"
    mock_s20.WORKTREES_DIR = tmp_path
    mock_run_agent.side_effect = RuntimeError("API connection failed")

    result = run_maker("test task", "test-branch")
    assert result.success is False
    assert "API connection failed" in result.summary
