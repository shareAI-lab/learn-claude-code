"""后台任务 BackgroundRun / BackgroundCheck / BackgroundKill。

对齐 TOOLS.md §2.2:
- BackgroundRun(command, timeout, description) → 返回 task_id,不阻塞
- BackgroundCheck(task_id?) → 查单个或列全部
- BackgroundKill(task_id) → 终止正在跑的任务(M4-2)
- Loop 每轮开头调 BackgroundManager.drain(),把新完成的结果注入
  为一条 <background-results> user 消息

线程安全靠 Queue + 锁保护的 dict。
"""
from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Any

from ..config.models import Config
from .registry import Tool, ToolRegistry


@dataclass
class BackgroundTask:
    id: str
    command: str
    description: str
    status: str = "running"  # running | completed | error | timeout | killed
    result: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    pid: int | None = None  # M4-2: Popen pid,用于 kill


class BackgroundManager:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._tasks: dict[str, BackgroundTask] = {}
        self._notifications: Queue = Queue()
        self._lock = threading.Lock()

    def run(self, command: str, timeout: int = 3600, description: str = "") -> str:
        task = BackgroundTask(
            id=uuid.uuid4().hex[:8],
            command=command,
            description=description or command[:40],
        )
        with self._lock:
            self._tasks[task.id] = task
        threading.Thread(
            target=self._exec, args=(task, timeout), daemon=True
        ).start()
        return f"Background task {task.id} started: {task.description}"

    def _exec(self, task: BackgroundTask, timeout: int) -> None:
        t = min(max(int(timeout), 1), 3600)
        try:
            # 用 Popen 而非 run,拿到 pid 支持 kill;创建新进程组便于整组终止
            popen_kwargs: dict[str, Any] = {
                "shell": True,
                "cwd": self.cfg.workspace_root(),
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
            }
            if os.name == "posix":
                popen_kwargs["preexec_fn"] = os.setsid  # 新 session+进程组
            proc = subprocess.Popen(task.command, **popen_kwargs)
            with self._lock:
                task.pid = proc.pid
            try:
                stdout, stderr = proc.communicate(timeout=t)
            except subprocess.TimeoutExpired:
                self._force_kill(proc)
                stdout, stderr = proc.communicate()
                with self._lock:
                    task.status = "timeout"
                    task.result = f"Timeout ({t}s)"
                    task.finished_at = time.time()
                self._notifications.put(task.id)
                return

            out = (stdout or "") + (stderr or "")
            if proc.returncode != 0:
                out += f"\n[exit code: {proc.returncode}]"
            with self._lock:
                # killed 由 kill() 方法预先标记,不要被覆盖
                if task.status != "killed":
                    task.status = "completed"
                task.result = out.rstrip("\n") or "(no output)"
                task.finished_at = time.time()
        except Exception as e:
            with self._lock:
                if task.status != "killed":
                    task.status = "error"
                task.result = f"{type(e).__name__}: {e}"
                task.finished_at = time.time()
        # 放入通知队列,loop 下轮 drain
        self._notifications.put(task.id)

    def check(self, task_id: str | None = None) -> str:
        with self._lock:
            if task_id:
                t = self._tasks.get(task_id)
                if not t:
                    return f"Error: unknown task_id '{task_id}'"
                preview = t.result[:300] if t.result else "(running)"
                return f"[{t.status}] {t.description}\n{preview}"
            if not self._tasks:
                return "(no background tasks)"
            lines = []
            for t in self._tasks.values():
                lines.append(f"{t.id}  [{t.status:<9}] {t.description}")
            return "\n".join(lines)

    def kill(self, task_id: str) -> str:
        """终止一个正在跑的后台任务。已完成/已终止的任务返回 Error。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return f"Error: unknown task_id '{task_id}'"
            if task.status != "running":
                return f"Error: task '{task_id}' is {task.status}, cannot kill"
            if task.pid is None:
                return f"Error: task '{task_id}' has no pid yet"
            task.status = "killed"  # 预先标记,防 _exec 收尾时覆盖
            pid = task.pid
        # 释放锁后才 kill,避免持锁调用阻塞的系统调用
        try:
            if os.name == "posix":
                # 杀整个进程组(shell=True 下子孙进程常见)
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
            else:
                # Windows: 尽力而为
                try:
                    os.kill(pid, signal.SIGTERM)
                except (OSError, ProcessLookupError):
                    pass
        except Exception as e:
            return f"Error: kill failed: {type(e).__name__}: {e}"
        return f"Killed task {task_id}"

    def _force_kill(self, proc: subprocess.Popen) -> None:
        """timeout 时强制终止进程组。"""
        try:
            if os.name == "posix":
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            else:
                try:
                    proc.kill()
                except OSError:
                    pass
        except Exception:
            pass

    def drain(self) -> list[BackgroundTask]:
        """返回自上次 drain 以来新完成的任务。"""
        finished: list[BackgroundTask] = []
        while True:
            try:
                tid = self._notifications.get_nowait()
            except Empty:
                break
            with self._lock:
                t = self._tasks.get(tid)
                if t:
                    finished.append(t)
        return finished


def register_background(registry: ToolRegistry, manager: BackgroundManager) -> None:
    registry.register(
        Tool(
            name="BackgroundRun",
            description=(
                "Run a shell command in the background. Returns a task_id "
                "immediately; completion results will be delivered to a later turn "
                "via <background-results>. Use for long-running builds/tests."
            ),
            requires=["exec"],
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "default": 3600, "maximum": 3600},
                    "description": {"type": "string"},
                },
                "required": ["command"],
            },
            handler=lambda **kw: manager.run(
                kw["command"], kw.get("timeout", 3600), kw.get("description", "")
            ),
        )
    )
    registry.register(
        Tool(
            name="BackgroundCheck",
            description="Check status of a background task by id, or list all.",
            input_schema={
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
            },
            handler=lambda **kw: manager.check(kw.get("task_id")),
        )
    )
    registry.register(
        Tool(
            name="BackgroundKill",
            description=(
                "Terminate a running background task by id. Only works while the "
                "task is still running; returns Error if already completed."
            ),
            requires=["exec"],
            input_schema={
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
            },
            handler=lambda **kw: manager.kill(kw["task_id"]),
        )
    )
