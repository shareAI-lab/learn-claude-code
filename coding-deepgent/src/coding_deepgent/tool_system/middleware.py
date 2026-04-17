from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command

from coding_deepgent.compact import maybe_persist_large_tool_result
from coding_deepgent.hooks.dispatcher import dispatch_context_hook
from coding_deepgent.hooks.events import HookEventName
from coding_deepgent.memory import evaluate_feedback_enforcement
from coding_deepgent.runtime import RuntimeEvent
from coding_deepgent.sessions.evidence_events import append_runtime_event_evidence

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
        feedback_decision = evaluate_feedback_enforcement(
            store=getattr(request.runtime, "store", None),
            tool_name=str(request.tool_call["name"]),
            args=dict(request.tool_call.get("args", {})),
        )
        if feedback_decision.blocked:
            feedback_result = ToolMessage(
                content=feedback_decision.message,
                tool_call_id=str(request.tool_call.get("id") or ""),
                status="error",
            )
            feedback_policy = ToolPolicyDecision(
                allowed=False,
                code=ToolPolicyCode.PERMISSION_DENIED,
                message=feedback_decision.message,
                behavior="deny",
            )
            self._emit(
                request=request,
                phase="feedback_blocked",
                decision=feedback_policy,
                result=feedback_result,
            )
            self._dispatch_hook(
                request=request,
                event="PermissionDenied",
                data={
                    "tool": str(request.tool_call["name"]),
                    "policy_code": "feedback_blocked",
                    "message": feedback_decision.message,
                    "matched_rule": feedback_decision.matched_rule or "",
                },
            )
            return feedback_result

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
        try:
            result = handler(request)
        except Exception as exc:
            failure = ToolMessage(
                content=_bounded_tool_failure_message(exc),
                tool_call_id=str(tool_call_id or ""),
                status="error",
            )
            self._emit(
                request=request,
                phase="failed",
                decision=decision,
                result=failure,
            )
            return failure
        result = self._process_tool_result(request=request, result=result)
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
        runtime_event = _send_event(sink, event, session_id=_session_id(request.runtime))
        if runtime_event is not None:
            append_runtime_event_evidence(
                context=getattr(request.runtime, "context", None),
                event=runtime_event,
            )

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

    def _process_tool_result(
        self,
        *,
        request: ToolCallRequest,
        result: ToolMessage | Command[Any],
    ) -> ToolMessage | Command[Any]:
        if not isinstance(result, ToolMessage):
            return result
        capability = self.registry.get(str(request.tool_call["name"]))
        if capability is None or not capability.persist_large_output:
            return result
        context = getattr(request.runtime, "context", None)
        if context is None:
            return result
        try:
            return maybe_persist_large_tool_result(
                result,
                runtime_context=context,
                max_inline_chars=capability.max_inline_result_chars,
            )
        except OSError:
            return result


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


def _send_event(
    sink: object, event: dict[str, object], *, session_id: str
) -> RuntimeEvent | None:
    emit = getattr(sink, "emit", None)
    if callable(emit):
        runtime_event = RuntimeEvent(
            kind=str(event["phase"]),
            message=f"Tool guard {event['phase']} for {event['tool']}",
            session_id=session_id,
            metadata=event,
        )
        emit(runtime_event)
        return runtime_event

    if callable(sink):
        sink(event)
        return None

    for method_name in ("record", "append"):
        method = getattr(sink, method_name, None)
        if callable(method):
            method(event)
            return None
    return None


def _bounded_tool_failure_message(error: Exception) -> str:
    detail = " ".join(str(error).split()).strip()
    if detail:
        detail = detail[:240]
        return f"Error: {type(error).__name__}: {detail}"
    return f"Error: {type(error).__name__}"
