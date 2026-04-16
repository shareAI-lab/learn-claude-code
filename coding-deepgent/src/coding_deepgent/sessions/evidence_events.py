from __future__ import annotations

from coding_deepgent.runtime.events import RuntimeEvent
from coding_deepgent.sessions.records import SessionContext
from coding_deepgent.sessions.store_jsonl import JsonlSessionStore

RUNTIME_EVIDENCE_KINDS = frozenset(
    {
        "hook_blocked",
        "permission_denied",
        "snip",
        "microcompact",
        "context_collapse",
        "auto_compact",
        "reactive_compact",
    }
)


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
    for key in (
        "hook_event",
        "tool",
        "policy_code",
        "permission_behavior",
        "strategy",
    ):
        value = event.metadata.get(key)
        if isinstance(value, str) and value:
            metadata[key] = value
    blocked = event.metadata.get("blocked")
    if isinstance(blocked, bool):
        metadata["blocked"] = blocked
    for key in (
        "hidden_messages",
        "cleared_tool_results",
        "collapsed_messages",
        "restored_path_count",
    ):
        value = event.metadata.get(key)
        if isinstance(value, int) and value >= 0:
            metadata[key] = value
    used_session_memory_assist = event.metadata.get("used_session_memory_assist")
    if isinstance(used_session_memory_assist, bool):
        metadata["used_session_memory_assist"] = used_session_memory_assist
    return metadata


def _summary(event: RuntimeEvent, metadata: dict[str, object]) -> str:
    if event.kind == "hook_blocked":
        hook_event = metadata.get("hook_event", "unknown")
        return f"Hook {hook_event} blocked execution."
    if event.kind == "permission_denied":
        tool = metadata.get("tool", "unknown")
        policy_code = metadata.get("policy_code", "permission_denied")
        return f"Tool {tool} denied by {policy_code}."
    if event.kind == "snip":
        hidden = metadata.get("hidden_messages", 0)
        return f"Live snip hid {hidden} older messages from the model call."
    if event.kind == "microcompact":
        cleared = metadata.get("cleared_tool_results", 0)
        return f"Live microcompact cleared {cleared} older tool results."
    if event.kind == "context_collapse":
        collapsed = metadata.get("collapsed_messages", 0)
        return f"Live context collapse summarized {collapsed} older messages."
    if event.kind == "auto_compact":
        return "Live auto-compact summarized history."
    if event.kind == "reactive_compact":
        return "Reactive compact retried after prompt-too-long."
    return event.message


def _status(event: RuntimeEvent) -> str:
    if event.kind == "hook_blocked":
        return "blocked"
    if event.kind == "permission_denied":
        return "denied"
    if event.kind in {
        "snip",
        "microcompact",
        "context_collapse",
        "auto_compact",
        "reactive_compact",
    }:
        return "completed"
    return "recorded"


def _subject(metadata: dict[str, object]) -> str | None:
    for key in ("tool", "hook_event", "strategy"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return None
