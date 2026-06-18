"""
github_client.py — 真实 GitHub REST API 只读客户端

方法签名与 GitHubMock 兼容，便于无缝切换。
仅实现只读操作（不创建 PR、不写入数据）。
"""

import requests
from config import GITHUB_TOKEN, GITHUB_REPO


class GitHubClient:
    """真实 GitHub API 只读客户端。"""

    def __init__(self, token: str = "", repo: str = ""):
        self.token = token or GITHUB_TOKEN
        self.repo = repo or GITHUB_REPO  # 格式: "owner/repo"
        self.base_url = f"https://api.github.com/repos/{self.repo}"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def _get(self, endpoint: str, params: dict | None = None) -> dict | list:
        """发送 GET 请求，返回 JSON 响应。"""
        url = f"{self.base_url}{endpoint}"
        resp = requests.get(url, headers=self.headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def list_open_issues(self, labels: list[str] | None = None) -> list[dict]:
        """获取 open issues，可选按 label 过滤。"""
        params = {"state": "open", "per_page": 100}
        if labels:
            params["labels"] = ",".join(labels)
        data = self._get("/issues", params)
        # 标准化为与 GitHubMock 兼容的格式
        return [
            {
                "number": issue["number"],
                "title": issue["title"],
                "body": issue.get("body", ""),
                "state": issue["state"],
                "labels": [l["name"] for l in issue.get("labels", [])],
            }
            for issue in data
            if not issue.get("pull_request")  # 排除 PR
        ]

    def get_issue(self, number: int) -> dict | None:
        """获取单个 issue。"""
        try:
            data = self._get(f"/issues/{number}")
            return {
                "number": data["number"],
                "title": data["title"],
                "body": data.get("body", ""),
                "state": data["state"],
                "labels": [l["name"] for l in data.get("labels", [])],
            }
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def get_failed_ci_runs(self, since_run_id: int = 0) -> list[dict]:
        """获取失败的 CI workflow runs。"""
        params = {"status": "failure", "per_page": 10}
        data = self._get("/actions/runs", params)
        runs = data.get("workflow_runs", [])
        result = []
        for run in runs:
            if run.get("conclusion") != "failure":
                continue
            run_id = run["id"]
            if run_id <= since_run_id:
                continue
            result.append({
                "run_id": run_id,
                "conclusion": run.get("conclusion", ""),
                "name": run.get("name", ""),
                "head_branch": run.get("head_branch", ""),
                "created_at": run.get("created_at", ""),
            })
        return result

    def get_ci_logs(self, run_id: int) -> str:
        """获取 CI 日志（返回 URL，因为日志需要认证下载）。"""
        try:
            # GitHub API 返回 302 重定向到日志下载 URL
            url = f"{self.base_url}/actions/runs/{run_id}/logs"
            resp = requests.get(url, headers=self.headers, timeout=30, allow_redirects=False)
            if resp.status_code == 302:
                return f"[Logs available at: {resp.headers.get('Location', url)}]"
            resp.raise_for_status()
            return resp.text[:5000]
        except Exception as e:
            return f"[Failed to fetch logs: {e}]"
