from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command

from coding_deepgent.hooks.dispatcher import dispatch_context_hook
from coding_deepgent.hooks.events import HookEventName
from coding_deepgent.runtime import RuntimeEvent

from .capabilities import CapabilityRegistry
from .policy import ToolPolicy, ToolPolicyCode, ToolPolicyDecision


class ToolGuardMiddleware(AgentMiddleware):
    """Apply shared tool policy before execution and emit local event evidence."""

    def __init__(
        self,
        *,
        registry: CapabilityRegistry,
        policy: ToolPolicy | None = None,
        event_sink: object | None = None,
    ) -> None:
        super().__init__()
        self.registry = registry
        self.policy = policy or ToolPolicy(registry=registry)
        self.event_sink = event_sink

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        decision = self.policy.evaluate(request.tool_call)
        tool_call_id = request.tool_call.get("id")

        if not decision.allowed:
            phase = (
                "permission_ask"
                if decision.code == ToolPolicyCode.PERMISSION_REQUIRED
                else "permission_denied"
            )
            self._emit(request=request, phase=phase, decision=decision)
            self._dispatch_hook(
                request=request,
                event="PermissionDenied",
                data={
                    "tool": str(request.tool_call["name"]),
                    "policy_code": decision.code.value,
                    "message": decision.message,
                },
            )
            return ToolMessage(
                content=decision.message,
                tool_call_id=str(tool_call_id or ""),
                status="error",
            )

        hook_outcome = self._dispatch_hook(
            request=request,
            event="PreToolUse",
            data={
                "tool": str(request.tool_call["name"]),
                "args": dict(request.tool_call.get("args", {})),
            },
        )
        if hook_outcome is not None and hook_outcome.blocked:
            return ToolMessage(
                content=hook_outcome.reason or "PreToolUse hook blocked execution.",
                tool_call_id=str(tool_call_id or ""),
                status="error",
            )

        self._emit(request=request, phase="allowed", decision=decision)
        result = handler(request)
        self._emit(
            request=request,
            phase="completed",
            decision=decision,
            result=result,
        )
        self._dispatch_hook(
            request=request,
            event="PostToolUse",
            data={
                "tool": str(request.tool_call["name"]),
                "args": dict(request.tool_call.get("args", {})),
                "result_type": type(result).__name__,
            },
        )
        return result

    def _emit(
        self,
        *,
        request: ToolCallRequest,
        phase: str,
        decision: ToolPolicyDecision,
        result: ToolMessage | Command[Any] | None = None,
    ) -> None:
        sink = self.event_sink or _runtime_event_sink(request.runtime)
        if sink is None:
            return

        event: dict[str, object] = {
            "source": "tool_guard",
            "phase": phase,
            "tool": str(request.tool_call["name"]),
            "tool_call_id": request.tool_call.get("id"),
            "policy_code": decision.code.value,
            "permission_behavior": decision.behavior,
            "result_type": type(result).__name__ if result is not None else None,
        }
        _send_event(sink, event, session_id=_session_id(request.runtime))

    def _dispatch_hook(
        self,
        *,
        request: ToolCallRequest,
        event: HookEventName,
        data: dict[str, object],
    ):
        return dispatch_context_hook(
            context=getattr(request.runtime, "context", None),
            session_id=_session_id(request.runtime),
            event=event,
            data=data,
        )


def _runtime_event_sink(runtime: object) -> object | None:
    context = getattr(runtime, "context", None)
    if context is None:
        return None

    if isinstance(context, dict):
        return context.get("event_sink")

    return getattr(context, "event_sink", None)


def _session_id(runtime: object) -> str:
    context = getattr(runtime, "context", None)
    if isinstance(context, dict):
        return str(context.get("session_id", "unknown"))
    return str(getattr(context, "session_id", "unknown"))


def _send_event(sink: object, event: dict[str, object], *, session_id: str) -> None:
    emit = getattr(sink, "emit", None)
    if callable(emit):
        emit(
            RuntimeEvent(
                kind=str(event["phase"]),
                message=f"Tool guard {event['phase']} for {event['tool']}",
                session_id=session_id,
                metadata=event,
            )
        )
        return

    if callable(sink):
        sink(event)
        return

    for method_name in ("record", "append"):
        method = getattr(sink, method_name, None)
        if callable(method):
            method(event)
            return
