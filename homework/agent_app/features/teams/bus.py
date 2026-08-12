"""A path-safe, consume-once JSONL mailbox transport."""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path


AGENT_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
ALLOWED_MESSAGE_TYPES = {
    "message",
    "result",
    "permission_request",
    "permission_response",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_request",
    "plan_approval_response",
}


def validate_agent_name(name: str, *, allow_lead: bool = True) -> str:
    if not isinstance(name, str):
        raise TypeError("Agent name must be a string")
    if not AGENT_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"Invalid agent name: {name!r}")
    if not allow_lead and name == "lead":
        raise ValueError("'lead' is a reversed agent name")
    return name


@dataclass(slots=True)
class MessageBus:
    root: Path
    lock: threading.RLock = field(default_factory=threading.RLock)

    def mailbox_path(self, agent: str) -> Path:
        validate_agent_name(agent)
        root = self.root.resolve()
        path = (root / f"{agent}.jsonl").resolve()
        if not path.is_relative_to(root):
            raise ValueError("Mailbox path escapes mailbox directory")
        return path

    def bootstrap(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def send(
        self,
        from_agent: str,
        to_agent: str,
        content: object,
        msg_type: str = "message",
        metadata: dict | None = None,
    ) -> None:
        validate_agent_name(from_agent)
        validate_agent_name(to_agent)
        if msg_type not in ALLOWED_MESSAGE_TYPES:
            raise ValueError(f"Invalid message type: {msg_type}")
        message = {
            "from": from_agent,
            "to": to_agent,
            "content": content,
            "type": msg_type,
            "ts": time.time(),
            "metadata": metadata or {},
        }
        with self.lock:
            self.bootstrap()
            with self.mailbox_path(to_agent).open("a", encoding="utf-8") as mailbox:
                mailbox.write(json.dumps(message, ensure_ascii=False) + "\n")
                mailbox.flush()

    def read_inbox(self, agent: str) -> list[dict]:
        path = self.mailbox_path(agent)
        with self.lock:
            if not path.exists():
                return []
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text("", encoding="utf-8")
        messages = []
        for line in lines:
            if not line.strip():
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"[mailbox warning] ignored corrupt line: {exc}")
        return messages
