"""Session 持久化: .oaic/sessions/<id>.jsonl 每条消息一行 JSON。

行为:
- 启动时创建新 session,id = YYYYMMDD-HHMMSS-<4hex>
- 每轮 loop 结束后 flush 新消息(只追加没写过的条目)
- --resume <id> / --resume latest 从磁盘加载 state.messages
- 写盘前对 content 脱敏

落盘 JSON 字段命名与 messages 原结构一致,方便 resume 时直接复用。
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config.models import Config
from ..tools.safety import redact


SESSION_ID_RE_TMPL = r"^\d{8}-\d{6}-[0-9a-f]{4}$"


def _gen_session_id() -> str:
    ts = time.strftime("%Y%m%d-%H%M%S")
    suffix = hashlib.sha256(f"{time.time_ns()}".encode()).hexdigest()[:4]
    return f"{ts}-{suffix}"


def _redact_message(msg: dict[str, Any]) -> dict[str, Any]:
    """对 content 字符串做脱敏,其它字段原样保留。"""
    out = dict(msg)
    content = out.get("content")
    if isinstance(content, str):
        out["content"] = redact(content)
    return out


@dataclass
class SessionStore:
    cfg: Config
    session_id: str = ""
    _flushed_count: int = 0

    @property
    def dir(self) -> Path:
        d = self.cfg.workspace_root() / self.cfg.session.dir
        d.mkdir(parents=True, exist_ok=True)
        return d

    def path(self, sid: str | None = None) -> Path:
        return self.dir / f"{sid or self.session_id}.jsonl"

    def new_session(self) -> str:
        self.session_id = _gen_session_id()
        self._flushed_count = 0
        # 创建空文件占位,方便 /sessions 扫描看到
        self.path().touch()
        return self.session_id

    def append_new_messages(self, messages: list[dict[str, Any]]) -> int:
        """把尚未写入磁盘的尾部消息追加到 jsonl。返回新写入条数。"""
        if not self.cfg.session.auto_save or not self.session_id:
            return 0
        new = messages[self._flushed_count:]
        if not new:
            return 0
        with self.path().open("a", encoding="utf-8") as f:
            for m in new:
                f.write(json.dumps(_redact_message(m), default=str, ensure_ascii=False) + "\n")
        self._flushed_count = len(messages)
        return len(new)

    def load(self, sid: str) -> list[dict[str, Any]]:
        p = self.path(sid)
        if not p.exists():
            raise FileNotFoundError(f"session '{sid}' not found at {p}")
        messages: list[dict[str, Any]] = []
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        self.session_id = sid
        self._flushed_count = len(messages)
        return messages

    def list_ids(self) -> list[str]:
        """按修改时间倒序列出 session id。"""
        files = list(self.dir.glob("*.jsonl"))
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [p.stem for p in files]

    def latest_id(self) -> str | None:
        ids = self.list_ids()
        return ids[0] if ids else None

    def summary(self, sid: str) -> dict[str, Any]:
        """统计一个 session: 消息数、首条 user 输入、最后修改时间。"""
        p = self.path(sid)
        if not p.exists():
            return {"id": sid, "exists": False}
        msgs = self.load(sid)
        # load 改了状态,恢复
        self.session_id = ""
        self._flushed_count = 0
        first_user = ""
        for m in msgs:
            if m.get("role") == "user":
                c = m.get("content", "")
                if isinstance(c, str) and c and not c.startswith("<"):
                    first_user = c[:80]
                    break
        return {
            "id": sid,
            "exists": True,
            "messages": len(msgs),
            "mtime": p.stat().st_mtime,
            "first_user": first_user,
        }
