"""
state.py — 持久化状态文件管理

实现 LoopState 数据结构和原子写入。
状态文件路径: state/.loop-state.json
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from config import STATE_FILE


# ── 数据结构 ──────────────────────────────────────────────

@dataclass
class CycleRecord:
    cycle_id: int
    task_id: str
    status: str           # "approved" | "rejected" | "needs_human"
    ts: float
    feedback: str = ""


@dataclass
class LoopState:
    version: int = 1
    last_run_ts: float = 0.0
    active_goals: list[str] = field(default_factory=list)
    processed_items: list[str] = field(default_factory=list)
    active_worktrees: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    cron_jobs: list[dict] = field(default_factory=list)
    error_log: list[dict] = field(default_factory=list)


# ── 加载与保存 ────────────────────────────────────────────

def load_state() -> LoopState:
    """从磁盘加载状态，不存在则返回空状态。"""
    if not STATE_FILE.exists():
        return LoopState()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return LoopState(
            version=data.get("version", 1),
            last_run_ts=data.get("last_run_ts", 0.0),
            active_goals=data.get("active_goals", []),
            processed_items=data.get("processed_items", []),
            active_worktrees=data.get("active_worktrees", []),
            history=data.get("history", []),
            cron_jobs=data.get("cron_jobs", []),
            error_log=data.get("error_log", []),
        )
    except (json.JSONDecodeError, KeyError) as e:
        print(f"\033[33m[Warning] State file corrupted, starting fresh: {e}\033[0m")
        return LoopState()


def save_state(state: LoopState) -> None:
    """原子写入状态文件。"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    data = {
        "version": state.version,
        "last_run_ts": state.last_run_ts,
        "active_goals": state.active_goals,
        "processed_items": state.processed_items,
        "active_worktrees": state.active_worktrees,
        "history": state.history,
        "cron_jobs": state.cron_jobs,
        "error_log": state.error_log,
    }
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_FILE)


# ── 状态操作 ──────────────────────────────────────────────

def record_cycle(state: LoopState, task_id: str, status: str, feedback: str = "", _save: bool = True) -> None:
    """记录一次 cycle 到历史。"""
    record = CycleRecord(
        cycle_id=len(state.history) + 1,
        task_id=task_id,
        status=status,
        ts=time.time(),
        feedback=feedback,
    )
    state.history.append({
        "cycle_id": record.cycle_id,
        "task_id": record.task_id,
        "status": record.status,
        "ts": record.ts,
        "feedback": record.feedback,
    })
    state.last_run_ts = record.ts
    if _save:
        save_state(state)


def mark_processed(state: LoopState, item_id: str, _save: bool = True) -> None:
    """标记任务项为已处理。"""
    if item_id not in state.processed_items:
        state.processed_items.append(item_id)
        if _save:
            save_state(state)


def add_worktree(state: LoopState, name: str) -> None:
    """记录活跃 worktree。"""
    if name not in state.active_worktrees:
        state.active_worktrees.append(name)
        save_state(state)


def remove_worktree(state: LoopState, name: str, _save: bool = True) -> None:
    """移除 worktree 记录。"""
    if name in state.active_worktrees:
        state.active_worktrees.remove(name)
        if _save:
            save_state(state)


def add_error(state: LoopState, task_id: str, error: str, _save: bool = True) -> None:
    """记录错误。"""
    state.error_log.append({
        "task_id": task_id,
        "error": error,
        "ts": time.time(),
    })
    if _save:
        save_state(state)
