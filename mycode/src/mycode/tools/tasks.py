"""持久化 Task 系统: .mycode/tasks/task_<id>.json。

对齐 TOOLS.md §3.2:
- subject / description / status(pending|in_progress|completed|deleted) / owner / blockedBy
- status=completed 时自动解除其他任务 blockedBy 中的本 id
- status=deleted 物理删除 json
字段命名约定:
- 工具参数名 snake_case (add_blocked_by / remove_blocked_by)
- 落盘 JSON 字段名 camelCase (blockedBy)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config.models import Config
from .registry import Tool, ToolRegistry


VALID_STATUS = {"pending", "in_progress", "completed", "deleted"}


@dataclass
class TaskStore:
    cfg: Config

    @property
    def dir(self) -> Path:
        d = self.cfg.workspace_root() / ".mycode" / "tasks"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _next_id(self) -> int:
        ids = [
            int(p.stem.split("_", 1)[1])
            for p in self.dir.glob("task_*.json")
            if p.stem.split("_", 1)[1].isdigit()
        ]
        return max(ids, default=0) + 1

    def _path(self, tid: int) -> Path:
        return self.dir / f"task_{tid}.json"

    def _load(self, tid: int) -> dict[str, Any]:
        p = self._path(tid)
        if not p.exists():
            raise FileNotFoundError(f"task {tid} not found")
        return json.loads(p.read_text(encoding="utf-8"))

    def _save(self, task: dict[str, Any]) -> None:
        self._path(task["id"]).write_text(
            json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _list_all(self) -> list[dict[str, Any]]:
        out = []
        for p in sorted(self.dir.glob("task_*.json")):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
        return out

    # ------- tools -------

    def create(self, subject: str, description: str = "", active_form: str = "") -> str:
        subject = (subject or "").strip()
        if not subject:
            return "Error: subject required"
        task = {
            "id": self._next_id(),
            "subject": subject,
            "description": (description or "").strip(),
            "activeForm": (active_form or "").strip() or subject,
            "status": "pending",
            "owner": None,
            "blockedBy": [],
        }
        self._save(task)
        return json.dumps(task, indent=2, ensure_ascii=False)

    def get(self, tid: int) -> str:
        try:
            return json.dumps(self._load(int(tid)), indent=2, ensure_ascii=False)
        except FileNotFoundError as e:
            return f"Error: {e}"

    def update(
        self,
        tid: int,
        status: str | None = None,
        owner: str | None = None,
        add_blocked_by: list[int] | None = None,
        remove_blocked_by: list[int] | None = None,
        subject: str | None = None,
        description: str | None = None,
    ) -> str:
        try:
            task = self._load(int(tid))
        except FileNotFoundError as e:
            return f"Error: {e}"
        if status is not None:
            if status not in VALID_STATUS:
                return f"Error: invalid status '{status}'"
            task["status"] = status
            if status == "completed":
                self._cascade_unblock(int(tid))
            if status == "deleted":
                self._path(int(tid)).unlink(missing_ok=True)
                return f"task {tid} deleted"
        if owner is not None:
            task["owner"] = owner or None
        if subject is not None:
            task["subject"] = subject.strip()
        if description is not None:
            task["description"] = description.strip()
        if add_blocked_by:
            blocked = set(task.get("blockedBy", []))
            blocked.update(int(x) for x in add_blocked_by)
            task["blockedBy"] = sorted(blocked)
        if remove_blocked_by:
            drop = {int(x) for x in remove_blocked_by}
            task["blockedBy"] = [x for x in task.get("blockedBy", []) if x not in drop]
        self._save(task)
        return json.dumps(task, indent=2, ensure_ascii=False)

    def _cascade_unblock(self, completed_id: int) -> None:
        for t in self._list_all():
            if completed_id in t.get("blockedBy", []):
                t["blockedBy"] = [x for x in t["blockedBy"] if x != completed_id]
                self._save(t)

    def list_all(self) -> str:
        tasks = self._list_all()
        if not tasks:
            return "(no tasks)"
        mark = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}
        lines = []
        for t in tasks:
            m = mark.get(t["status"], "[?]")
            owner = f" @{t['owner']}" if t.get("owner") else ""
            blocked = f" (blocked by: {t['blockedBy']})" if t.get("blockedBy") else ""
            lines.append(f"{m} #{t['id']}: {t['subject']}{owner}{blocked}")
        return "\n".join(lines)


def register_tasks(registry: ToolRegistry, store: TaskStore) -> None:
    registry.register(
        Tool(
            name="TaskCreate",
            description="Create a persistent task stored under .mycode/tasks/.",
            requires=["write"],
            input_schema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "description": {"type": "string"},
                    "activeForm": {"type": "string"},
                },
                "required": ["subject"],
            },
            handler=lambda **kw: store.create(
                kw["subject"], kw.get("description", ""), kw.get("activeForm", "")
            ),
        )
    )
    registry.register(
        Tool(
            name="TaskGet",
            description="Get a persistent task by id.",
            input_schema={
                "type": "object",
                "properties": {"task_id": {"type": "integer"}},
                "required": ["task_id"],
            },
            handler=lambda **kw: store.get(kw["task_id"]),
        )
    )
    registry.register(
        Tool(
            name="TaskUpdate",
            description="Update a persistent task status, owner, or blocked_by.",
            requires=["write"],
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "status": {"type": "string", "enum": sorted(VALID_STATUS)},
                    "owner": {"type": "string"},
                    "subject": {"type": "string"},
                    "description": {"type": "string"},
                    "add_blocked_by": {"type": "array", "items": {"type": "integer"}},
                    "remove_blocked_by": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["task_id"],
            },
            handler=lambda **kw: store.update(
                kw["task_id"],
                status=kw.get("status"),
                owner=kw.get("owner"),
                add_blocked_by=kw.get("add_blocked_by"),
                remove_blocked_by=kw.get("remove_blocked_by"),
                subject=kw.get("subject"),
                description=kw.get("description"),
            ),
        )
    )
    registry.register(
        Tool(
            name="TaskList",
            description="List all persistent tasks.",
            input_schema={"type": "object", "properties": {}},
            handler=lambda **kw: store.list_all(),
        )
    )
