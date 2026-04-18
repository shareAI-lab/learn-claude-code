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
        "post_autocompact_turn",
        "orphan_tombstoned",
        "query_error",
        "reactive_compact",
        "subagent_spawn_guard",
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
        "outcome",
        "phase",
        "error_class",
        "reason",
        "strategy",
        "trigger",
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
        "tools_cleared",
        "tools_kept",
        "tokens_saved_estimate",
        "keep_recent",
        "protected_recent_tokens",
        "gap_minutes",
        "failure_count",
        "max_failures",
        "collapsed_messages",
        "restored_path_count",
        "estimated_token_count",
        "context_window_tokens",
        "estimated_token_ratio_percent",
        "drained_summaries",
        "pre_compact_total",
        "post_compact_total",
        "new_turn_input",
        "new_turn_output",
        "input_token_estimate",
        "output_token_estimate",
        "total_token_estimate",
        "response_message_count",
        "message_count",
        "tombstoned_count",
        "retry_count",
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
        if metadata.get("outcome") == "attempted":
            return "Live auto-compact attempt started."
        if metadata.get("trigger") == "failure_circuit_breaker":
            return "Live auto-compact skipped after repeated failures."
        return "Live auto-compact summarized history."
    if event.kind == "post_autocompact_turn":
        return "Post-auto-compact turn completed with bounded canary metrics."
    if event.kind == "orphan_tombstoned":
        count = metadata.get("tombstoned_count", 0)
        return f"Projection repair tombstoned {count} orphaned tool blocks."
    if event.kind == "query_error":
        phase = metadata.get("phase", "unknown")
        error_class = metadata.get("error_class", "Exception")
        return f"Agent query failed during {phase}: {error_class}."
    if event.kind == "reactive_compact":
        return "Reactive compact retried after prompt-too-long."
    if event.kind == "subagent_spawn_guard":
        return "Subagent spawn blocked by context pressure guard."
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
        "post_autocompact_turn",
        "orphan_tombstoned",
        "reactive_compact",
        "subagent_spawn_guard",
    }:
        if event.kind == "auto_compact" and event.metadata.get("outcome") == "attempted":
            return "recorded"
        return "completed"
    if event.kind == "query_error":
        return "failed"
    return "recorded"


def _subject(metadata: dict[str, object]) -> str | None:
    for key in ("tool", "hook_event", "strategy", "phase", "reason"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return None
