"""
mechanisms/messagebus.py — MessageBus mechanism, sourced from s15 (the origin).

First-appearance rule: s15 introduces MessageBus inline (send + read_inbox +
peek, no metadata). s16 adds the ``metadata`` parameter to ``send`` (s16's
teaching focus is ProtocolState, not the metadata param itself — it's a
side enhancement). s17-s20 reuse s16's variant verbatim.

This module carries the s16 variant (``send`` with optional ``metadata``).
``peek`` is kept (s15 uses it; s16-s20 don't, but it's harmless). s15 keeps
its own inline version (the origin); s16-s20 import from here.

Design — ``init_messagebus(workdir)`` binds ``MAILBOX_DIR`` (mirrors
``init_tasks``). ``MessageBus`` methods late-bind ``MAILBOX_DIR`` at call time.
"""

import json
import time
from pathlib import Path

MAILBOX_DIR: Path | None = None  # bound by init_messagebus()


def init_messagebus(workdir: Path) -> Path:
    """Bind ``MAILBOX_DIR`` to *workdir* / .mailboxes (idempotent). Call at startup."""
    global MAILBOX_DIR
    MAILBOX_DIR = workdir / ".mailboxes"
    MAILBOX_DIR.mkdir(exist_ok=True)
    return MAILBOX_DIR


class MessageBus:
    """File-based message bus. Each agent has a .jsonl inbox.

    Read is destructive: read_text + unlink (consumes messages).
    Teaching version: no file locking; real CC uses proper-lockfile.
    """

    def send(self, from_agent: str, to_agent: str, content: str,
             msg_type: str = "message", metadata: dict = None):
        msg = {"from": from_agent, "to": to_agent,
               "content": content, "type": msg_type,
               "ts": time.time(), "metadata": metadata or {}}
        inbox = MAILBOX_DIR / f"{to_agent}.jsonl"
        with open(inbox, "a") as f:
            f.write(json.dumps(msg) + "\n")
        print(f"  \033[33m[bus] {from_agent} → {to_agent}: "
              f"({msg_type}) {content[:50]}\033[0m")

    def read_inbox(self, agent: str) -> list[dict]:
        inbox = MAILBOX_DIR / f"{agent}.jsonl"
        if not inbox.exists():
            return []
        msgs = [json.loads(line) for line in inbox.read_text().splitlines()
                if line.strip()]
        inbox.unlink()  # consume: read + delete
        return msgs

    def peek(self, agent: str) -> bool:
        """Non-destructive: True if the agent has unread inbox messages.

        The Lead's inbox poller uses this to decide whether to wake a turn
        without consuming the mailbox.
        """
        inbox = MAILBOX_DIR / f"{agent}.jsonl"
        return inbox.exists() and inbox.stat().st_size > 0
