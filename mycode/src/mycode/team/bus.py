"""消息总线: 基于 .team/inbox/<name>.jsonl 的文件邮箱。

- send: 追加写一行 JSON 到 <to>.jsonl
- read_inbox: 读全部然后清空(drain-on-read)
- broadcast: 批量 send

对齐 DESIGN §9 M3 团队协议设计(s09)。
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from ..config.models import Config


VALID_MSG_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_request",
    "plan_approval_response",
}


class MessageBus:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._lock = threading.Lock()

    @property
    def inbox_dir(self) -> Path:
        d = self.cfg.workspace_root() / ".team" / "inbox"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _inbox_path(self, name: str) -> Path:
        safe = "".join(c for c in name if c.isalnum() or c in "-_.")
        if not safe or safe != name:
            raise ValueError(f"invalid teammate name: {name!r}")
        return self.inbox_dir / f"{safe}.jsonl"

    def send(
        self,
        sender: str,
        to: str,
        content: str,
        msg_type: str = "message",
        extra: dict[str, Any] | None = None,
    ) -> str:
        if msg_type not in VALID_MSG_TYPES:
            return f"Error: invalid msg_type '{msg_type}'"
        if sender == to:
            return f"Error: cannot send to self ('{to}')"
        try:
            path = self._inbox_path(to)
        except ValueError as e:
            return f"Error: {e}"
        msg = {
            "from": sender,
            "to": to,
            "type": msg_type,
            "content": content,
            "timestamp": time.time(),
        }
        if extra:
            msg.update(extra)
        with self._lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        return f"Sent {msg_type} to {to}"

    def read_inbox(self, name: str) -> list[dict[str, Any]]:
        """读取并清空指定收件箱。"""
        try:
            path = self._inbox_path(name)
        except ValueError:
            return []
        if not path.exists():
            return []
        with self._lock:
            raw = path.read_text(encoding="utf-8")
            path.write_text("", encoding="utf-8")
        out: list[dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def broadcast(
        self,
        sender: str,
        content: str,
        recipients: list[str],
    ) -> str:
        count = 0
        for name in recipients:
            if name == sender:
                continue
            r = self.send(sender, name, content, msg_type="broadcast")
            if not r.startswith("Error"):
                count += 1
        return f"Broadcast to {count} recipients"
