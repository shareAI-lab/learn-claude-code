"""TeammateManager: 名册 + 队友生命周期。

M3-3 只做骨架:
- .team/config.json 记 roster
- spawn() 创建队友元数据(实际 agent loop 线程在 M3-4/M3-6 接入)
- list/find/status 切换

状态机:
  spawn -> working -> idle -> working -> shutdown
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config.models import Config


VALID_STATUS = {"working", "idle", "shutdown"}


@dataclass
class TeammateManager:
    cfg: Config
    # spawn 时把线程句柄存这里
    _threads: dict[str, threading.Thread] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def dir(self) -> Path:
        d = self.cfg.workspace_root() / ".team"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def config_path(self) -> Path:
        return self.dir / "config.json"

    def _load(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {"team_name": "default", "members": []}
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"team_name": "default", "members": []}

    def _save(self, data: dict[str, Any]) -> None:
        self.config_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ---------- public API ----------

    def members(self) -> list[dict[str, Any]]:
        return self._load().get("members", [])

    def find(self, name: str) -> dict[str, Any] | None:
        for m in self.members():
            if m["name"] == name:
                return m
        return None

    def register(self, name: str, role: str) -> dict[str, Any]:
        """加入/更新名册。返回 member dict。调用方负责 thread 启动。"""
        with self._lock:
            data = self._load()
            existing = None
            for m in data["members"]:
                if m["name"] == name:
                    existing = m
                    break
            if existing:
                existing["role"] = role
                existing["status"] = "working"
            else:
                data["members"].append({"name": name, "role": role, "status": "working"})
            self._save(data)
        return self.find(name)

    def set_status(self, name: str, status: str) -> str:
        if status not in VALID_STATUS:
            return f"Error: invalid status '{status}'"
        with self._lock:
            data = self._load()
            for m in data["members"]:
                if m["name"] == name:
                    m["status"] = status
                    self._save(data)
                    return f"{name} → {status}"
        return f"Error: unknown teammate '{name}'"

    def remove(self, name: str) -> str:
        with self._lock:
            data = self._load()
            before = len(data["members"])
            data["members"] = [m for m in data["members"] if m["name"] != name]
            if len(data["members"]) == before:
                return f"Error: unknown teammate '{name}'"
            self._save(data)
        return f"Removed {name}"

    def render(self) -> str:
        mbrs = self.members()
        if not mbrs:
            return "(empty team)"
        lines = [f"Team: {self._load().get('team_name', 'default')}"]
        for m in mbrs:
            lines.append(f"  {m['name']:<15} {m['role']:<20} [{m['status']}]")
        return "\n".join(lines)

    def names(self) -> list[str]:
        return [m["name"] for m in self.members()]

    # ---------- thread 句柄簿记(实际 loop 在 M3-4 注入) ----------

    def register_thread(self, name: str, thread: threading.Thread) -> None:
        self._threads[name] = thread

    def get_thread(self, name: str) -> threading.Thread | None:
        return self._threads.get(name)
