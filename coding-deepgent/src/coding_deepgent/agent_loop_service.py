from __future__ import annotations

from collections.abc import Callable, MutableMapping
from typing import Any, cast

from coding_deepgent.agent_runtime_service import (
    invoke_agent,
    resolve_compiled_agent,
    session_payload,
    update_session_state,
)
from coding_deepgent.compact import project_messages_with_stats
from coding_deepgent.containers import AppContainer
from coding_deepgent.hooks.dispatcher import dispatch_runtime_hook
from coding_deepgent.memory import (
    build_long_term_memory_snapshot,
    runtime_memory_service,
    write_long_term_memory_snapshot,
)
from coding_deepgent.memory.store import MemoryStore
from coding_deepgent.rendering import latest_assistant_text
from coding_deepgent.runtime import RuntimeEvent, RuntimeInvocation
from coding_deepgent.sessions.evidence_events import append_runtime_event_evidence
from coding_deepgent.sessions.records import SessionContext, TranscriptProjection


def is_new_session(
    normalized_messages: list[dict[str, Any]],
    session_state: MutableMapping[str, Any],
) -> bool:
    return (
        len(normalized_messages) == 1
        and not session_state.get("todos")
        and session_state.get("rounds_since_update", 0) == 0
    )


def run_agent_loop(
    *,
    messages: list[dict[str, Any]],
    session_state: MutableMapping[str, Any],
    session_id: str | None,
    container: AppContainer | None,
    build_container: Callable[[], AppContainer],
    build_agent: Callable[..., Any],
    build_runtime_invocation: Callable[..., RuntimeInvocation],
    session_context: SessionContext | None = None,
    transcript_projection: TranscriptProjection | None = None,
) -> str:
    active_container = container or build_container()
    invocation = build_runtime_invocation(
        container=active_container,
        session_id=session_id,
        session_context=session_context,
        transcript_projection=transcript_projection,
    )
    projection_result = project_messages_with_stats(messages)
    normalized = projection_result.messages
    if projection_result.repair_stats.orphan_tombstoned:
        _emit_agent_event(
            invocation,
            kind="orphan_tombstoned",
            message="Projection repair tombstoned orphaned tool result material.",
            metadata={
                "source": "message_projection",
                "reason": projection_result.repair_stats.reason or "unknown",
                "tombstoned_count": projection_result.repair_stats.orphan_tombstoned,
                "message_count": len(normalized),
            },
        )

    if is_new_session(normalized, session_state):
        dispatch_runtime_hook(
            invocation,
            event="SessionStart",
            data={
                "session_id": invocation.context.session_id,
                "entrypoint": invocation.context.entrypoint,
                "workdir": str(invocation.context.workdir),
            },
        )

    prompt_submit = dispatch_runtime_hook(
        invocation,
        event="UserPromptSubmit",
        data={
            "session_id": invocation.context.session_id,
            "message_count": len(normalized),
            "latest_user_message": normalized[-1]["content"] if normalized else "",
        },
    )
    if prompt_submit.blocked:
        final_text = prompt_submit.reason or "UserPromptSubmit hook blocked execution."
        messages.append({"role": "assistant", "content": final_text})
        return final_text

    try:
        result = invoke_agent(
            resolve_compiled_agent(active_container, build_agent),
            {"messages": normalized, **session_payload(session_state)},
            invocation,
        )
    except Exception as exc:
        _emit_agent_event(
            invocation,
            kind="query_error",
            message="Agent query failed during invoke.",
            metadata={
                "source": "agent_loop",
                "phase": "agent_invoke",
                "error_class": type(exc).__name__,
                "retry_count": 0,
            },
        )
        raise
    update_session_state(session_state, result)
    memory_service = runtime_memory_service(invocation)
    final_text = latest_assistant_text(result)
    if memory_service is not None and final_text:
        latest_user = normalized[-1]["content"] if normalized else ""
        memory_service.enqueue_extraction(
            project_scope=str(invocation.context.workdir),
            agent_scope=invocation.context.agent_name,
            source="agent_loop",
            text=f"User: {latest_user}\n\nAssistant: {final_text}",
        )
    write_long_term_memory_snapshot(
        session_state,
        build_long_term_memory_snapshot(_runtime_store(active_container)),
    )
    if final_text:
        messages.append({"role": "assistant", "content": final_text})
    return final_text


def _emit_agent_event(
    invocation: RuntimeInvocation,
    *,
    kind: str,
    message: str,
    metadata: dict[str, object],
) -> None:
    event = RuntimeEvent(
        kind=kind,
        message=message,
        session_id=invocation.context.session_id,
        metadata=metadata,
    )
    invocation.context.event_sink.emit(event)
    append_runtime_event_evidence(context=invocation.context, event=event)


def _runtime_store(active_container: object) -> MemoryStore | None:
    runtime = getattr(active_container, "runtime", None)
    if runtime is None:
        return None
    store_provider = getattr(runtime, "store", None)
    if callable(store_provider):
        return cast(MemoryStore | None, store_provider())
    return None
