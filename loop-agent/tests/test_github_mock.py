"""tests/test_github_mock.py — Mock API 返回值测试"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def github():
    """创建 GitHubMock 实例。"""
    from github_mock import GitHubMock
    return GitHubMock()


def test_list_open_issues(github):
    """应返回 3 个 open issues。"""
    issues = github.list_open_issues()
    assert len(issues) == 3
    assert all(i["state"] == "open" for i in issues)


def test_list_open_issues_filter_labels(github):
    """按 label 过滤。"""
    bugs = github.list_open_issues(labels=["bug"])
    assert len(bugs) == 1
    assert bugs[0]["number"] == 42

    features = github.list_open_issues(labels=["feature"])
    assert len(features) == 1
    assert features[0]["number"] == 43


def test_get_issue(github):
    """获取单个 issue。"""
    issue = github.get_issue(42)
    assert issue is not None
    assert issue["title"] == "Fix: login timeout on slow networks"


def test_get_issue_not_found(github):
    """不存在的 issue 应返回 None。"""
    issue = github.get_issue(999)
    assert issue is None


def test_get_failed_ci_runs(github):
    """应返回 2 个失败的 CI runs。"""
    runs = github.get_failed_ci_runs()
    assert len(runs) == 2
    assert all(r["conclusion"] == "failure" for r in runs)


def test_get_failed_ci_runs_since(github):
    """过滤已处理的 runs。"""
    runs = github.get_failed_ci_runs(since_run_id=789)
    assert len(runs) == 1
    assert runs[0]["run_id"] == 790


def test_create_pull_request(github):
    """创建 PR 应返回模板数据。"""
    pr = github.create_pull_request(
        title="Fix: test",
        body="Test body",
        head="wt/test",
    )
    assert "title" in pr
    assert pr["head"]["ref"] == "wt/test"


def test_get_ci_logs(github):
    """获取 CI 日志。"""
    logs = github.get_ci_logs(789)
    assert "FAILED" in logs
    assert "test_login_timeout" in logs


def test_get_ci_logs_not_found(github):
    """不存在的 run 应返回空字符串。"""
    logs = github.get_ci_logs(999)
    assert logs == ""
