from __future__ import annotations

from coding_deepgent.runtime.events import RuntimeEvent
from coding_deepgent.sessions.records import SessionContext
from coding_deepgent.sessions.store_jsonl import JsonlSessionStore

RUNTIME_EVIDENCE_KINDS = frozenset({"hook_blocked", "permission_denied"})


def append_runtime_event_evidence(
    *,
    context: object,
    event: RuntimeEvent,
) -> bool:
    if event.kind not in RUNTIME_EVIDENCE_KINDS:
        return False
    session_context = getattr(context, "session_context", None)
    if not isinstance(session_context, SessionContext):
        return False

    metadata = _safe_metadata(event)
    JsonlSessionStore(session_context.store_dir).append_evidence(
        session_context,
        kind="runtime_event",
        summary=_summary(event, metadata),
        status=_status(event),
        subject=_subject(metadata),
        metadata=metadata,
    )
    return True


def _safe_metadata(event: RuntimeEvent) -> dict[str, object]:
    source = event.metadata.get("source")
    metadata: dict[str, object] = {
        "event_kind": event.kind,
        "source": source if isinstance(source, str) else "runtime",
    }
    for key in ("hook_event", "tool", "policy_code", "permission_behavior"):
        value = event.metadata.get(key)
        if isinstance(value, str) and value:
            metadata[key] = value
    blocked = event.metadata.get("blocked")
    if isinstance(blocked, bool):
        metadata["blocked"] = blocked
    return metadata


def _summary(event: RuntimeEvent, metadata: dict[str, object]) -> str:
    if event.kind == "hook_blocked":
        hook_event = metadata.get("hook_event", "unknown")
        return f"Hook {hook_event} blocked execution."
    if event.kind == "permission_denied":
        tool = metadata.get("tool", "unknown")
        policy_code = metadata.get("policy_code", "permission_denied")
        return f"Tool {tool} denied by {policy_code}."
    return event.message


def _status(event: RuntimeEvent) -> str:
    if event.kind == "hook_blocked":
        return "blocked"
    if event.kind == "permission_denied":
        return "denied"
    return "recorded"


def _subject(metadata: dict[str, object]) -> str | None:
    for key in ("tool", "hook_event"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return None
