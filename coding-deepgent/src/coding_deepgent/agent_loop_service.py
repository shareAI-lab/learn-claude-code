from __future__ import annotations

from collections.abc import Callable, MutableMapping
from typing import Any

from coding_deepgent.agent_runtime_service import (
    invoke_agent,
    resolve_compiled_agent,
    session_payload,
    update_session_state,
)
from coding_deepgent.containers import AppContainer
from coding_deepgent.hooks.dispatcher import dispatch_runtime_hook
from coding_deepgent.rendering import latest_assistant_text, normalize_messages
from coding_deepgent.runtime import RuntimeInvocation
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
    normalized = normalize_messages(messages)
    invocation = build_runtime_invocation(
        container=active_container,
        session_id=session_id,
        session_context=session_context,
        transcript_projection=transcript_projection,
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

    result = invoke_agent(
        resolve_compiled_agent(active_container, build_agent),
        {"messages": normalized, **session_payload(session_state)},
        invocation,
    )
    update_session_state(session_state, result)
    final_text = latest_assistant_text(result)
    if final_text:
        messages.append({"role": "assistant", "content": final_text})
    return final_text
