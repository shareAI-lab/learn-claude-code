from __future__ import annotations

from dataclasses import dataclass

from coding_deepgent.runtime.context import RuntimeContext
from coding_deepgent.runtime.events import RuntimeEventSink
from coding_deepgent.settings import Settings

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
    *,
    session_id: str | None = None,
    entrypoint: str | None = None,
    agent_name: str | None = None,
) -> RuntimeContext:
    resolved_session_id = resolve_session_id(session_id)
    return RuntimeContext(
        session_id=resolved_session_id,
        workdir=settings.workdir,
        entrypoint=entrypoint or settings.entrypoint,
        agent_name=agent_name or settings.agent_name,
        skill_dir=settings.skill_dir,
        event_sink=event_sink,
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
    *,
    session_id: str | None = None,
    entrypoint: str | None = None,
    agent_name: str | None = None,
) -> RuntimeInvocation:
    resolved_session_id = resolve_session_id(session_id)
    return RuntimeInvocation(
        context=build_runtime_context(
            settings,
            event_sink,
            session_id=resolved_session_id,
            entrypoint=entrypoint,
            agent_name=agent_name,
        ),
        config=build_runnable_config(session_id=resolved_session_id),
    )
