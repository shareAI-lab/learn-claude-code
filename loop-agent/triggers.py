"""
triggers.py — 四种触发源

TriggerEvent 数据类 + check_manual / check_goal / check_cron / check_ci_failure
"""

import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue, Empty

from config import REPO_ROOT, CRON_CHECK_INTERVAL, GITHUB_TOKEN
from github_mock import GitHubMock


# ── 数据结构 ──────────────────────────────────────────────

@dataclass
class TriggerEvent:
    source: str        # "manual" | "goal" | "cron" | "ci_failure"
    prompt: str        # 任务描述
    goal_condition: str | None = None   # Goal 模式的验证命令
    metadata: dict = field(default_factory=dict)


# ── 手动触发 ──────────────────────────────────────────────

_manual_queue: Queue = Queue()


def enqueue_manual(prompt: str) -> None:
    """REPL 线程写入手动触发。"""
    _manual_queue.put(TriggerEvent(source="manual", prompt=prompt))


def check_manual() -> TriggerEvent | None:
    """检查手动触发队列。"""
    try:
        return _manual_queue.get_nowait()
    except Empty:
        return None


# ── Goal 触发 ─────────────────────────────────────────────

import re as _re


def _is_shell_command(text: str) -> bool:
    """判断文本是否是 shell 命令（vs 自然语言）。"""
    shell_prefixes = [
        "python", "pip", "npm", "node", "pytest", "make", "cargo",
        "go ", "git ", "docker", "curl", "wget", "ls", "cat", "dir",
        "echo", "test ", "./", "bash", "sh ", "powershell", "cmd",
    ]
    text_stripped = text.strip()
    text_lower = text_stripped.lower()

    # 包含 shell 操作符 → 命令
    if any(op in text for op in ["&&", "||", "|", ">", ">>", "$("]):
        return True
    # 包含路径分隔符 + 文件扩展名（1-4字母，后跟非字母或行尾）→ 命令
    # 排除目录名中的点（如 loop-agent、.worktrees）
    if _re.search(r'[/\\]\S+\.\w{1,4}(?![a-zA-Z_-])', text):
        return True

    # 自然语言特征检测：如果包含冠词、介词等，大概率是自然语言
    _nl_words = {" the ", " a ", " an ", " to ", " is ", " are ", " all ",
                 " and ", " or ", " but ", " not ", " can ", " will ",
                 " should ", " how ", " what ", " why ", " when ", " make ",
                 " fix ", " add ", " remove ", " update ", " the "}
    text_with_spaces = f" {text_lower} "
    if " " in text_lower and any(w in text_with_spaces for w in _nl_words):
        return False

    # 匹配 shell 前缀 → 命令
    if any(text_lower.startswith(p) for p in shell_prefixes):
        return True
    return False


def check_goal(verify_command: str) -> TriggerEvent | None:
    """
    Goal 模式：运行验证命令，非零退出 = 仍需工作。
    Osmani 的 "keep working until condition met"。

    如果 verify_command 不是 shell 命令（自然语言），直接返回
    TriggerEvent 让 Maker 处理。
    """
    # 自然语言目标：直接作为任务交给 Maker
    if not _is_shell_command(verify_command):
        return TriggerEvent(
            source="goal",
            prompt=verify_command,
            goal_condition=verify_command,
        )

    # Shell 命令目标：执行并检查退出码
    try:
        r = subprocess.run(
            verify_command, shell=True,
            cwd=REPO_ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
        output = r.stdout + r.stderr

        # 非零退出 = 需要继续工作
        if r.returncode != 0:
            return TriggerEvent(
                source="goal",
                prompt=f"Goal not yet met. Verification output:\n{output}",
                goal_condition=verify_command,
            )

        # pytest 特殊处理：没有收集到测试也视为失败
        if "no tests collected" in output.lower() or "no test ran" in output.lower():
            return TriggerEvent(
                source="goal",
                prompt=f"Goal not yet met: no tests found.\n{output}",
                goal_condition=verify_command,
            )

    except subprocess.TimeoutExpired:
        return TriggerEvent(
            source="goal",
            prompt=f"Goal check timed out: {verify_command}",
            goal_condition=verify_command,
        )
    except Exception as e:
        return TriggerEvent(
            source="goal",
            prompt=f"Goal check error: {e}",
            goal_condition=verify_command,
        )


# ── Cron 触发 ─────────────────────────────────────────────

def _cron_field_matches(field: str, value: int) -> bool:
    """单个 cron 字段匹配。"""
    if field == "*":
        return True
    if field.startswith("*/"):
        step = int(field[2:])
        return step > 0 and value % step == 0
    if "," in field:
        return any(_cron_field_matches(f.strip(), value) for f in field.split(","))
    if "-" in field:
        lo, hi = field.split("-", 1)
        return int(lo) <= value <= int(hi)
    return value == int(field)


def cron_matches(cron_expr: str, dt: datetime) -> bool:
    """5 字段 cron 表达式匹配。"""
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return False
    minute, hour, dom, month, dow = fields
    dow_val = (dt.weekday() + 1) % 7  # Python Monday=0 → cron Sunday=0

    m = _cron_field_matches(minute, dt.minute)
    h = _cron_field_matches(hour, dt.hour)
    dom_ok = _cron_field_matches(dom, dt.day)
    month_ok = _cron_field_matches(month, dt.month)
    dow_ok = _cron_field_matches(dow, dow_val)

    if not (m and h and month_ok):
        return False

    dom_unconstrained = dom == "*"
    dow_unconstrained = dow == "*"
    if dom_unconstrained and dow_unconstrained:
        return True
    if dom_unconstrained:
        return dow_ok
    if dow_unconstrained:
        return dom_ok
    return dom_ok or dow_ok


_cron_queue: Queue = Queue()
_cron_jobs: list[dict] = [
    {"cron": "0 */6 * * *", "prompt": "Run CI failure check and fix any issues.", "id": "ci_check"},
]


def check_cron() -> TriggerEvent | None:
    """检查 cron 队列。"""
    try:
        return _cron_queue.get_nowait()
    except Empty:
        return None


def _cron_scheduler_loop() -> None:
    """守护线程：每分钟检查 cron 表达式。"""
    while True:
        now = datetime.now()
        for job in _cron_jobs:
            if cron_matches(job["cron"], now):
                _cron_queue.put(TriggerEvent(
                    source="cron",
                    prompt=job["prompt"],
                    metadata={"cron": job["cron"], "job_id": job.get("id", "")},
                ))
        time.sleep(CRON_CHECK_INTERVAL)


def start_cron_daemon() -> None:
    """启动 cron 守护线程。"""
    t = threading.Thread(target=_cron_scheduler_loop, daemon=True)
    t.start()


def add_cron_job(cron: str, prompt: str, job_id: str = "") -> None:
    """添加 cron 任务。"""
    _cron_jobs.append({"cron": cron, "prompt": prompt, "id": job_id or f"job_{len(_cron_jobs)}"})


# ── CI 失败触发 ───────────────────────────────────────────

# 有 GITHUB_TOKEN 时使用真实 API，否则用 mock
if GITHUB_TOKEN:
    from github_client import GitHubClient
    _github = GitHubClient()
else:
    _github = GitHubMock()
_last_ci_run_id: int = 0


def check_ci_failure() -> TriggerEvent | None:
    """检查 CI 失败（使用 mock GitHub API）。"""
    global _last_ci_run_id
    failed_runs = _github.get_failed_ci_runs(since_run_id=_last_ci_run_id)
    if not failed_runs:
        return None

    run = failed_runs[0]
    _last_ci_run_id = run["run_id"]

    return TriggerEvent(
        source="ci_failure",
        prompt=(
            f"CI run #{run['run_id']} failed on commit {run['commit_sha']}.\n"
            f"Failed tests: {', '.join(run.get('failed_tests', []))}\n"
            f"Logs:\n{run.get('logs', '')}\n\n"
            "Please fix the failing tests."
        ),
        metadata={"run_id": run["run_id"], "commit_sha": run.get("commit_sha", "")},
    )


# ── 聚合检查 ─────────────────────────────────────────────

def check_all_triggers() -> TriggerEvent | None:
    """按优先级检查所有触发源。"""
    # 1. 手动触发（最高优先级）
    event = check_manual()
    if event:
        return event

    # 2. CI 失败
    event = check_ci_failure()
    if event:
        return event

    # 3. Cron
    event = check_cron()
    if event:
        return event

    return None
