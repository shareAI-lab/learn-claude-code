from __future__ import annotations

from collections.abc import Callable, Sequence
from inspect import Parameter, signature
from typing import Any

from coding_deepgent.compact import (
    compact_record_from_messages,
    is_compact_artifact_message,
)
from coding_deepgent.runtime import default_runtime_state
from coding_deepgent.settings import Settings
from coding_deepgent.sessions.records import LoadedSession, SessionSummary
from coding_deepgent.sessions.resume import is_resume_context_message
from coding_deepgent.sessions.store_jsonl import JsonlSessionStore


def recorded_session_store(settings: Settings) -> JsonlSessionStore:
    return JsonlSessionStore(settings.session_dir)


def list_recorded_sessions(settings: Settings) -> Sequence[SessionSummary]:
    return recorded_session_store(settings).list_sessions(workdir=settings.workdir)


def load_recorded_session(settings: Settings, session_id: str) -> LoadedSession:
    return recorded_session_store(settings).load_session(
        session_id=session_id,
        workdir=settings.workdir,
    )


def _recorded_message_count(history: Sequence[dict[str, Any]]) -> int:
    compact_record = compact_record_from_messages(list(history))
    if compact_record is not None:
        return int(compact_record["original_message_count"])
    return sum(
        1
        for message in history
        if not is_resume_context_message(message)
        and not is_compact_artifact_message(message)
    )


def _supports_keyword_argument(callback: Callable[..., Any], keyword: str) -> bool:
    try:
        parameters = signature(callback).parameters.values()
    except (TypeError, ValueError):
        return True

    return any(
        parameter.kind == Parameter.VAR_KEYWORD or parameter.name == keyword
        for parameter in parameters
    )


def run_prompt_with_recording(
    *,
    settings: Settings,
    prompt: str,
    run_agent: Callable[..., str],
    history: list[dict[str, Any]] | None = None,
    session_state: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> str:
    store = recorded_session_store(settings)
    context = None
    active_session_id = session_id
    active_state = session_state if session_state is not None else default_runtime_state()
    transcript = history if history is not None else []
    recorded_message_count = _recorded_message_count(transcript)

    if session_id is not None:
        context = store.create_session(
            workdir=settings.workdir,
            session_id=session_id,
            entrypoint=settings.entrypoint,
        )
    elif history is None:
        context = store.create_session(
            workdir=settings.workdir,
            session_id=session_id,
            entrypoint=settings.entrypoint,
        )
        active_session_id = context.session_id

    if context is not None:
        compact_record = compact_record_from_messages(transcript)
        if compact_record is not None:
            store.append_compact(context, **compact_record)
        store.append_message(
            context,
            role="user",
            content=prompt,
            message_index=recorded_message_count,
        )

    transcript.append({"role": "user", "content": prompt})
    run_agent_kwargs: dict[str, Any] = {
        "session_state": active_state,
        "session_id": active_session_id,
    }
    if context is not None and _supports_keyword_argument(
        run_agent, "session_context"
    ):
        run_agent_kwargs["session_context"] = context
    result = run_agent(transcript, **run_agent_kwargs)

    if context is not None:
        store.append_message(
            context,
            role="assistant",
            content=result,
            message_index=recorded_message_count + 1,
        )
        store.append_state_snapshot(context, state=active_state)
        store.append_evidence(
            context,
            kind="runtime",
            summary="Prompt completed through coding-deepgent CLI continuation path."
            if history is not None
            else "Prompt completed through coding-deepgent CLI run path.",
            status="completed",
            subject="cli.run_once.resume" if history is not None else "cli.run_once",
        )

    return result
