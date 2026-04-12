from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command

from .capabilities import CapabilityRegistry
from .policy import ToolPolicy, ToolPolicyDecision


class ToolGuardMiddleware(AgentMiddleware):
    """Apply shared tool policy before execution and emit local event evidence."""

    def __init__(
        self,
        *,
        registry: CapabilityRegistry,
        policy: ToolPolicy | None = None,
        event_sink: Callable[[dict[str, object]], None] | None = None,
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
            self._emit(
                request=request,
                phase="blocked",
                decision=decision,
            )
            return ToolMessage(
                content=decision.message,
                tool_call_id=str(tool_call_id or ""),
                status="error",
            )

        self._emit(
            request=request,
            phase="allowed",
            decision=decision,
        )
        result = handler(request)
        self._emit(
            request=request,
            phase="completed",
            decision=decision,
            result=result,
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
            "result_type": type(result).__name__ if result is not None else None,
        }
        _send_event(sink, event)


def _runtime_event_sink(runtime: object) -> object | None:
    context = getattr(runtime, "context", None)
    if context is None:
        return None

    if isinstance(context, dict):
        return context.get("event_sink")

    return getattr(context, "event_sink", None)


def _send_event(sink: object, event: dict[str, object]) -> None:
    if callable(sink):
        sink(event)
        return

    for method_name in ("record", "emit", "append"):
        method = getattr(sink, method_name, None)
        if callable(method):
            method(event)
            return
