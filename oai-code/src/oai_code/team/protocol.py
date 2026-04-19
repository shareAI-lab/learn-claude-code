"""团队协议: shutdown + plan_approval。两者同构: 一方发请求带 req_id,另一方响应引用同 req_id。

状态机:
  [pending] --approve--> [approved]
  [pending] --reject--->  [rejected]
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from .bus import MessageBus


@dataclass
class ProtocolTracker:
    """跟踪进行中的请求。两种协议共用一个 tracker 但 namespace 区分。"""

    _lock: threading.Lock = field(default_factory=threading.Lock)
    shutdown_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    plan_requests: dict[str, dict[str, Any]] = field(default_factory=dict)

    # ---------- shutdown (lead 发起) ----------

    def send_shutdown(
        self, bus: MessageBus, sender: str, target: str
    ) -> str:
        """lead 向某个 teammate 发起关停请求。"""
        req_id = uuid.uuid4().hex[:8]
        with self._lock:
            self.shutdown_requests[req_id] = {
                "target": target,
                "status": "pending",
                "sender": sender,
            }
        r = bus.send(
            sender,
            target,
            "Please shut down gracefully.",
            msg_type="shutdown_request",
            extra={"request_id": req_id},
        )
        if r.startswith("Error"):
            with self._lock:
                self.shutdown_requests.pop(req_id, None)
            return r
        return f"Shutdown request {req_id} sent to '{target}' (pending)"

    def record_shutdown_response(
        self, req_id: str, approve: bool, feedback: str = ""
    ) -> str:
        with self._lock:
            entry = self.shutdown_requests.get(req_id)
            if not entry:
                return f"Error: unknown shutdown request_id '{req_id}'"
            entry["status"] = "approved" if approve else "rejected"
            entry["feedback"] = feedback
        return f"Shutdown {req_id}: {entry['status']}"

    # ---------- plan_approval (teammate 发起,lead 审) ----------

    def submit_plan(
        self, bus: MessageBus, sender: str, lead: str, plan: str
    ) -> str:
        req_id = uuid.uuid4().hex[:8]
        with self._lock:
            self.plan_requests[req_id] = {
                "from": sender,
                "plan": plan,
                "status": "pending",
            }
        r = bus.send(
            sender,
            lead,
            plan,
            msg_type="plan_approval_request",
            extra={"request_id": req_id},
        )
        if r.startswith("Error"):
            with self._lock:
                self.plan_requests.pop(req_id, None)
            return r
        return f"Plan {req_id} submitted to '{lead}' (pending)"

    def review_plan(
        self,
        bus: MessageBus,
        reviewer: str,
        req_id: str,
        approve: bool,
        feedback: str = "",
    ) -> str:
        with self._lock:
            entry = self.plan_requests.get(req_id)
            if not entry:
                return f"Error: unknown plan request_id '{req_id}'"
            entry["status"] = "approved" if approve else "rejected"
            entry["feedback"] = feedback
        r = bus.send(
            reviewer,
            entry["from"],
            feedback,
            msg_type="plan_approval_response",
            extra={"request_id": req_id, "approve": approve},
        )
        if r.startswith("Error"):
            return r
        return f"Plan {req_id}: {entry['status']}"

    # ---------- query ----------

    def get_shutdown(self, req_id: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self.shutdown_requests.get(req_id)
            return dict(entry) if entry else None

    def get_plan(self, req_id: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self.plan_requests.get(req_id)
            return dict(entry) if entry else None
