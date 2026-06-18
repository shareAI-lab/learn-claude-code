"""
task_discovery.py — 任务发现

将触发事件转换为具体任务项，过滤已处理项。
"""

import hashlib
import time
from dataclasses import dataclass, field

from triggers import TriggerEvent
from state import LoopState


# ── 数据结构 ──────────────────────────────────────────────

@dataclass
class TaskItem:
    id: str              # "issue_42" | "ci_run_789" | "manual_001"
    source: str          # 来源类型
    title: str
    description: str
    branch_hint: str     # 建议的 worktree 分支名
    files_hint: list[str] = field(default_factory=list)  # 可能涉及的文件


# ── 任务发现 ──────────────────────────────────────────────

def discover_from_trigger(event: TriggerEvent) -> TaskItem:
    """将 TriggerEvent 转换为 TaskItem。"""
    if event.source == "ci_failure":
        run_id = event.metadata.get("run_id", 0)
        return TaskItem(
            id=f"ci_run_{run_id}",
            source="ci_failure",
            title=f"Fix CI failure #{run_id}",
            description=event.prompt,
            branch_hint=f"fix-ci-{run_id}",
        )

    if event.source == "goal":
        content_hash = hashlib.md5(event.prompt.encode()).hexdigest()[:8]
        return TaskItem(
            id=f"goal_{content_hash}",
            source="goal",
            title=f"Goal: {event.prompt[:60]}",
            description=event.prompt,
            branch_hint=f"goal-{content_hash}",
        )

    if event.source == "cron":
        job_id = event.metadata.get("job_id", "cron")
        ts_suffix = int(time.time()) % 100000
        return TaskItem(
            id=f"cron_{job_id}_{ts_suffix}",
            source="cron",
            title=f"Cron task: {job_id}",
            description=event.prompt,
            branch_hint=f"cron-{job_id}-{ts_suffix}",
        )

    # manual — 使用内容哈希确保相同 prompt 生成相同 ID
    content_hash = hashlib.md5(event.prompt.encode()).hexdigest()[:8]
    ts_suffix = int(time.time()) % 100000
    return TaskItem(
        id=f"manual_{content_hash}",
        source="manual",
        title=event.prompt[:80],
        description=event.prompt,
        branch_hint=f"manual-{content_hash}-{ts_suffix}",
    )


def filter_already_processed(items: list[TaskItem], state: LoopState) -> list[TaskItem]:
    """过滤已处理的任务项。"""
    return [item for item in items if item.id not in state.processed_items]
