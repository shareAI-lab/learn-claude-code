"""Explicit request matching and team protocol operations."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Callable

from .bus import MessageBus


@dataclass(slots=True)
class ProtocolState:
    request_id: str
    type: str
    sender: str
    target: str
    status: str
    payload: str
    created_at: float = field(default_factory=time.time)


@dataclass(slots=True)
class ProtocolStore:
    pending: dict[str, ProtocolState] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)


EXPECTED_RESPONSE_TYPES = {
    "shutdown": "shutdown_response",
    "plan_approval": "plan_approval_response",
}


def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex}"


def match_response(
    store: ProtocolStore, response_type: str, request_id: str, approve: bool
) -> bool:
    with store.lock:
        state = store.pending.get(request_id)
        if not state:
            print(f"  \033[31m[protocol] unknown request_id: {request_id}\033[0m")
            return False
        expected_type = EXPECTED_RESPONSE_TYPES.get(state.type)
        if response_type != expected_type:
            print(
                f"  \033[31m[protocol] type mismatch: "
                f"(expected {expected_type}), got {response_type}\033[0m"
            )
            return False
        if state.status != "pending":
            print(
                f"  \033[33m[protocol] {request_id} already {state.status}, "
                f"ignoring duplicate\033[0m"
            )
            return False
        state.status = "approved" if approve else "rejected"
    icon = "✓" if approve else "✗"
    color = "32" if approve else "31"
    print(
        f"  \033[{color}m[protocol] {state.type} {icon} "
        f"({request_id}: {state.status})\033[0m"
    )
    return True


def wait_for_permission_response(
    bus: MessageBus,
    agent: str,
    request_id: str,
    deferred_inbox: list[dict],
    *,
    clock: Callable[[], float],
    sleep: Callable[[float], None],
    poll_interval: float,
    timeout: float,
) -> dict:
    deadline = clock() + timeout
    while clock() < deadline:
        matched = None
        for message in bus.read_inbox(agent):
            content = message.get("content", {})
            if (
                message.get("type") == "permission_response"
                and message.get("from") == "lead"
                and isinstance(content, dict)
                and content.get("request_id") == request_id
            ):
                matched = content
            else:
                deferred_inbox.append(message)
        if matched:
            return matched
        sleep(poll_interval)
    return {
        "request_id": request_id,
        "approved": False,
        "reason": "Permission request timed out",
    }


def process_permission_request(
    bus: MessageBus,
    store: ProtocolStore,
    message: dict,
    *,
    hook: Callable,
    cwd_resolver: Callable,
    guarded_tools: set[str],
    clock: Callable[[], float],
    sleep: Callable[[float], None],
) -> None:
    del store, clock, sleep
    requester = message.get("from")
    request = message.get("content", {})
    cwd_valid = True
    tool_cwd = None
    try:
        tool_cwd = cwd_resolver(request.get("cwd"))
    except (TypeError, ValueError):
        cwd_valid = False
    if isinstance(request, dict):
        request_id = request.get("request_id")
        tool_name = request.get("tool_name")
        tool_input = request.get("tool_input")
    else:
        request_id = tool_name = tool_input = None
    valid = (
        isinstance(request_id, str)
        and tool_name in guarded_tools
        and isinstance(tool_input, dict)
        and cwd_valid
    )
    if not valid:
        bus.send(
            "lead", requester,
            {"request_id": request_id, "approved": False,
             "reason": "Invalid permission request"},
            msg_type="permission_response",
        )
        return
    block = SimpleNamespace(
        id=request.get("tool_use_id"), name=tool_name, input=tool_input,
        agent=requester, cwd=tool_cwd,
    )
    denied_reason = hook("PreToolUse", block)
    bus.send(
        "lead", requester,
        {"request_id": request_id, "approved": denied_reason is None,
         "reason": "" if denied_reason is None else str(denied_reason)},
        msg_type="permission_response",
    )


def collect_lead_inbox(
    bus: MessageBus,
    store: ProtocolStore,
    *,
    hook: Callable,
    cwd_resolver: Callable,
    guarded_tools: set[str],
    clock: Callable[[], float],
    sleep: Callable[[float], None],
) -> list[dict]:
    ordinary_messages = []
    for message in bus.read_inbox("lead"):
        message_type = message.get("type", "")
        if message_type == "permission_request":
            process_permission_request(
                bus, store, message, hook=hook, cwd_resolver=cwd_resolver,
                guarded_tools=guarded_tools, clock=clock, sleep=sleep,
            )
            continue
        if message_type in {"shutdown_response", "plan_approval_response"}:
            metadata = message.get("metadata", {})
            request_id = metadata.get("request_id", "")
            if request_id:
                match_response(
                    store, message_type, request_id,
                    bool(metadata.get("approve", False)),
                )
            else:
                print(f"  [protocol] {message_type} missing request_id")
        ordinary_messages.append(message)
    return ordinary_messages


def submit_plan(
    bus: MessageBus, store: ProtocolStore, from_name: str, plan: str
) -> str:
    request_id = new_request_id()
    with store.lock:
        store.pending[request_id] = ProtocolState(
            request_id=request_id, type="plan_approval", sender=from_name,
            target="lead", status="pending", payload=plan,
        )
    bus.send(
        from_name, "lead", plan, "plan_approval_request",
        {"request_id": request_id},
    )
    return f"Plan submitted ({request_id}). Waiting for approval..."


def request_shutdown(bus: MessageBus, store: ProtocolStore, teammate: str) -> str:
    request_id = new_request_id()
    with store.lock:
        store.pending[request_id] = ProtocolState(
            request_id=request_id, type="shutdown", sender="lead",
            target=teammate, status="pending", payload="",
        )
    bus.send(
        "lead", teammate, "Please shut down gracefully.", "shutdown_request",
        {"request_id": request_id},
    )
    print(f"  \033[35m[protocol] shutdown_request → {teammate} ({request_id})\033[0m")
    return f"Shutdown request sent to {teammate} (req: {request_id})"


def review_plan(
    bus: MessageBus, store: ProtocolStore, request_id: str, approve: bool,
    feedback: str = "",
) -> str:
    with store.lock:
        state = store.pending.get(request_id)
        if not state:
            return f"Request {request_id} not found"
        state.status = "approved" if approve else "rejected"
    bus.send(
        "lead", state.sender, feedback or ("Approved" if approve else "Rejected"),
        "plan_approval_response", {"request_id": request_id, "approve": approve},
    )
    icon = "✓" if approve else "✗"
    print(f"  \033[32m[protocol] plan {icon} ({request_id})\033[0m")
    return f"Plan {'approved' if approve else 'rejected'} ({request_id})"
