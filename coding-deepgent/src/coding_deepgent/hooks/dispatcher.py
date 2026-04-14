from __future__ import annotations

from typing import Any

from coding_deepgent.hooks.events import HookEventName, HookPayload
from coding_deepgent.hooks.registry import HookDispatchOutcome, LocalHookRegistry
from coding_deepgent.runtime.events import RuntimeEvent
from coding_deepgent.runtime.invocation import RuntimeInvocation
from coding_deepgent.sessions.evidence_events import append_runtime_event_evidence


def emit_hook_runtime_event(
    invocation: RuntimeInvocation,
    *,
    phase: str,
    event: HookEventName,
    blocked: bool = False,
    reason: str | None = None,
) -> None:
    runtime_event = RuntimeEvent(
        kind=phase,
        message=f"Hook {phase} for {event}",
        session_id=invocation.context.session_id,
        metadata={
            "source": "hooks",
            "hook_event": event,
            "blocked": blocked,
            "reason": reason,
        },
    )
    invocation.context.event_sink.emit(runtime_event)
    append_runtime_event_evidence(context=invocation.context, event=runtime_event)


def dispatch_runtime_hook(
    invocation: RuntimeInvocation,
    *,
    event: HookEventName,
    data: dict[str, object],
) -> HookDispatchOutcome:
    registry: LocalHookRegistry = invocation.context.hook_registry
    if not registry.has_hooks(event):
        return HookDispatchOutcome(results=(), blocked=False)
    payload = HookPayload(event=event, data=data)
    emit_hook_runtime_event(invocation, phase="hook_start", event=event)
    outcome = registry.dispatch(payload)
    emit_hook_runtime_event(
        invocation,
        phase="hook_blocked" if outcome.blocked else "hook_complete",
        event=event,
        blocked=outcome.blocked,
        reason=outcome.reason,
    )
    return outcome


def dispatch_context_hook(
    *,
    context: Any,
    session_id: str,
    event: HookEventName,
    data: dict[str, object],
) -> HookDispatchOutcome | None:
    registry = getattr(context, "hook_registry", None)
    sink = getattr(context, "event_sink", None)
    if registry is None or sink is None or not registry.has_hooks(event):
        return None
    payload = HookPayload(event=event, data=data)
    start_event = RuntimeEvent(
        kind="hook_start",
        message=f"Hook hook_start for {event}",
        session_id=session_id,
        metadata={"source": "hooks", "hook_event": event, "blocked": False},
    )
    sink.emit(start_event)
    append_runtime_event_evidence(context=context, event=start_event)
    outcome = registry.dispatch(payload)
    terminal_event = RuntimeEvent(
        kind="hook_blocked" if outcome.blocked else "hook_complete",
        message=f"Hook {'hook_blocked' if outcome.blocked else 'hook_complete'} for {event}",
        session_id=session_id,
        metadata={
            "source": "hooks",
            "hook_event": event,
            "blocked": outcome.blocked,
            "reason": outcome.reason,
        },
    )
    sink.emit(terminal_event)
    append_runtime_event_evidence(context=context, event=terminal_event)
    return outcome
