"""
github_mock.py — Mock GitHub API

方法签名兼容真实 GitHub REST API，用于本地开发和测试。
真实部署时替换为 httpx/requests 调用即可。
"""

import json
from pathlib import Path

from config import MOCK_DATA_DIR


class GitHubMock:
    """Mock GitHub API 客户端。"""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or MOCK_DATA_DIR
        self._issues = self._load_json("issues.json")
        self._ci_results = self._load_json("ci_results.json")
        self._pr_template = self._load_json("pr_template.json")

    def _load_json(self, filename: str) -> list | dict:
        path = self.data_dir / filename
        if not path.exists():
            return [] if filename.endswith("s.json") else {}
        return json.loads(path.read_text(encoding="utf-8"))

    def list_open_issues(self, labels: list[str] | None = None) -> list[dict]:
        """获取 open issues，可选按 label 过滤。"""
        results = [i for i in self._issues if i.get("state") == "open"]
        if labels:
            results = [
                i for i in results
                if any(l in i.get("labels", []) for l in labels)
            ]
        return results

    def get_issue(self, number: int) -> dict | None:
        """获取单个 issue。"""
        for issue in self._issues:
            if issue.get("number") == number:
                return issue
        return None

    def get_failed_ci_runs(self, since_run_id: int = 0) -> list[dict]:
        """获取失败的 CI runs（过滤已处理的）。"""
        return [
            r for r in self._ci_results
            if r.get("conclusion") == "failure" and r.get("run_id", 0) > since_run_id
        ]

    def create_pull_request(self, title: str, body: str, head: str, base: str = "main") -> dict:
        """模拟创建 PR。"""
        pr = dict(self._pr_template) if isinstance(self._pr_template, dict) else {}
        pr.update({
            "title": title,
            "body": body,
            "head": {"ref": head, "sha": "mock_sha"},
            "base": {"ref": base},
        })
        return pr

    def get_ci_logs(self, run_id: int) -> str:
        """获取 CI 日志。"""
        for run in self._ci_results:
            if run.get("run_id") == run_id:
                return run.get("logs", "")
        return ""
