from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from langchain.agents import create_agent

from coding_deepgent import agent_loop_service
from coding_deepgent import bootstrap
from coding_deepgent.containers import AppContainer
from coding_deepgent.settings import build_openai_model, load_settings
from coding_deepgent.runtime import RuntimeInvocation, default_runtime_state
from coding_deepgent.sessions.records import SessionContext


def build_container() -> AppContainer:
    container = bootstrap.build_container(
        settings_loader=load_settings,
        model_factory=build_openai_model,
        create_agent_factory=create_agent,
    )
    bootstrap.validate_container_startup(container=container)
    return container


def build_agent(*, container: AppContainer | None = None):
    active_container = container or build_container()
    return bootstrap.build_agent(container=active_container)


def build_runtime_invocation(
    *,
    container: AppContainer | None = None,
    session_id: str | None = None,
    session_context: SessionContext | None = None,
) -> RuntimeInvocation:
    active_container = container or build_container()
    return bootstrap.build_runtime_invocation(
        container=active_container,
        session_id=session_id,
        session_context=session_context,
    )


def agent_loop(
    messages: list[dict[str, Any]],
    *,
    container: AppContainer | None = None,
    session_state: MutableMapping[str, Any] | None = None,
    session_id: str | None = None,
    session_context: SessionContext | None = None,
) -> str:
    active_session_state = (
        session_state if session_state is not None else default_runtime_state()
    )
    return agent_loop_service.run_agent_loop(
        messages=messages,
        session_state=active_session_state,
        session_id=session_id,
        container=container,
        build_container=build_container,
        build_agent=build_agent,
        build_runtime_invocation=build_runtime_invocation,
        session_context=session_context,
    )
