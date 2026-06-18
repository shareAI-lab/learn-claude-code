"""tests/test_github_client.py — GitHub API 客户端测试（mock HTTP）"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def _mock_response(json_data, status_code=200):
    """创建 mock requests.Response。"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


class TestGitHubClientListIssues:
    """list_open_issues 测试。"""

    @patch("github_client.requests.get")
    def test_list_open_issues(self, mock_get):
        from github_client import GitHubClient
        client = GitHubClient(token="test-token", repo="owner/repo")

        mock_get.return_value = _mock_response([
            {"number": 1, "title": "Bug", "state": "open",
             "body": "desc", "labels": [{"name": "bug"}]},
            {"number": 2, "title": "PR", "state": "open",
             "body": "", "labels": [],
             "pull_request": {"url": "..."}},  # 应被排除
        ])

        issues = client.list_open_issues()
        assert len(issues) == 1
        assert issues[0]["number"] == 1
        assert issues[0]["labels"] == ["bug"]

    @patch("github_client.requests.get")
    def test_list_open_issues_with_labels(self, mock_get):
        from github_client import GitHubClient
        client = GitHubClient(token="test-token", repo="owner/repo")

        mock_get.return_value = _mock_response([
            {"number": 1, "title": "Bug", "state": "open",
             "body": "", "labels": [{"name": "bug"}]},
        ])

        issues = client.list_open_issues(labels=["bug"])
        # 验证传了 labels 参数
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["params"]["labels"] == "bug"


class TestGitHubClientGetIssue:
    """get_issue 测试。"""

    @patch("github_client.requests.get")
    def test_get_issue_found(self, mock_get):
        from github_client import GitHubClient
        client = GitHubClient(token="test-token", repo="owner/repo")

        mock_get.return_value = _mock_response(
            {"number": 42, "title": "Test", "state": "open",
             "body": "hello", "labels": []})

        issue = client.get_issue(42)
        assert issue is not None
        assert issue["number"] == 42

    @patch("github_client.requests.get")
    def test_get_issue_not_found(self, mock_get):
        from github_client import GitHubClient
        client = GitHubClient(token="test-token", repo="owner/repo")

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        http_error = requests.HTTPError(response=mock_resp)
        mock_get.return_value = mock_resp
        mock_get.return_value.raise_for_status.side_effect = http_error

        issue = client.get_issue(999)
        assert issue is None


class TestGitHubClientCIRuns:
    """get_failed_ci_runs 测试。"""

    @patch("github_client.requests.get")
    def test_get_failed_runs(self, mock_get):
        from github_client import GitHubClient
        client = GitHubClient(token="test-token", repo="owner/repo")

        mock_get.return_value = _mock_response({
            "workflow_runs": [
                {"id": 100, "conclusion": "failure", "name": "CI",
                 "head_branch": "main", "created_at": "2024-01-01"},
                {"id": 99, "conclusion": "success", "name": "CI",
                 "head_branch": "main", "created_at": "2024-01-01"},
            ]
        })

        runs = client.get_failed_ci_runs()
        assert len(runs) == 1
        assert runs[0]["run_id"] == 100

    @patch("github_client.requests.get")
    def test_get_failed_runs_since(self, mock_get):
        from github_client import GitHubClient
        client = GitHubClient(token="test-token", repo="owner/repo")

        mock_get.return_value = _mock_response({
            "workflow_runs": [
                {"id": 100, "conclusion": "failure", "name": "CI",
                 "head_branch": "main", "created_at": "2024-01-01"},
            ]
        })

        runs = client.get_failed_ci_runs(since_run_id=100)
        assert len(runs) == 0  # id 100 <= since_run_id 100


class TestGitHubClientAuth:
    """认证测试。"""

    def test_token_in_headers(self):
        from github_client import GitHubClient
        client = GitHubClient(token="my-token", repo="owner/repo")
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer my-token"

    def test_no_token(self):
        from github_client import GitHubClient
        client = GitHubClient(token="", repo="owner/repo")
        assert "Authorization" not in client.headers


# 需要 import requests 用于构造 HTTPError
import requests
