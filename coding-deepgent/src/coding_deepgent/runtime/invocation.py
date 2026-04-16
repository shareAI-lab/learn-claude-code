from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from coding_deepgent.hooks.registry import LocalHookRegistry
from coding_deepgent.runtime.context import RuntimeContext
from coding_deepgent.runtime.events import RuntimeEventSink
from coding_deepgent.settings import Settings

if TYPE_CHECKING:
    from coding_deepgent.sessions.records import SessionContext, TranscriptProjection

DEFAULT_SESSION_ID = "default"


def resolve_session_id(session_id: str | None = None) -> str:
    resolved = (session_id or DEFAULT_SESSION_ID).strip()
    return resolved or DEFAULT_SESSION_ID


def build_runnable_config(
    *, session_id: str | None = None
) -> dict[str, dict[str, str]]:
    resolved_session_id = resolve_session_id(session_id)
    return {"configurable": {"thread_id": resolved_session_id}}


def build_runtime_context(
    settings: Settings,
    event_sink: RuntimeEventSink,
    hook_registry: LocalHookRegistry,
    *,
    session_id: str | None = None,
    entrypoint: str | None = None,
    agent_name: str | None = None,
    session_context: SessionContext | None = None,
    transcript_projection: TranscriptProjection | None = None,
) -> RuntimeContext:
    resolved_session_id = resolve_session_id(session_id)
    return RuntimeContext(
        session_id=resolved_session_id,
        workdir=settings.workdir,
        trusted_workdirs=settings.trusted_workdirs,
        entrypoint=entrypoint or settings.entrypoint,
        agent_name=agent_name or settings.agent_name,
        skill_dir=settings.skill_dir,
        event_sink=event_sink,
        hook_registry=hook_registry,
        session_context=session_context,
        transcript_projection=transcript_projection,
        model_context_window_tokens=settings.model_context_window_tokens,
        subagent_spawn_guard_ratio=settings.subagent_spawn_guard_ratio,
    )


@dataclass(frozen=True, slots=True)
class RuntimeInvocation:
    context: RuntimeContext
    config: dict[str, dict[str, str]]

    @property
    def thread_id(self) -> str:
        return self.config["configurable"]["thread_id"]


def build_runtime_invocation(
    settings: Settings,
    event_sink: RuntimeEventSink,
    hook_registry: LocalHookRegistry,
    *,
    session_id: str | None = None,
    entrypoint: str | None = None,
    agent_name: str | None = None,
    session_context: SessionContext | None = None,
    transcript_projection: TranscriptProjection | None = None,
) -> RuntimeInvocation:
    resolved_session_id = resolve_session_id(session_id)
    return RuntimeInvocation(
        context=build_runtime_context(
            settings,
            event_sink,
            hook_registry,
            session_id=resolved_session_id,
            entrypoint=entrypoint,
            agent_name=agent_name,
            session_context=session_context,
            transcript_projection=transcript_projection,
        ),
        config=build_runnable_config(session_id=resolved_session_id),
    )
