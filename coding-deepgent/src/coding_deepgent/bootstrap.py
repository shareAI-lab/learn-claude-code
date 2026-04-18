from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from dependency_injector import providers

from coding_deepgent.containers import AppContainer
from coding_deepgent.sessions.records import SessionContext, TranscriptProjection


def build_container(
    *,
    settings_loader: Callable[[], Any],
    model_factory: Callable[..., Any],
    create_agent_factory: Any,
) -> AppContainer:
    container = AppContainer(
        settings=providers.Singleton(settings_loader),
        model=providers.Factory(model_factory),
        create_agent_factory=providers.Object(create_agent_factory),
    )
    container.check_dependencies()
    return container


def validate_container_startup(*, container: AppContainer) -> Any:
    return container.startup_contract()


def build_agent(*, container: AppContainer) -> Any:
    return container.agent()


def build_runtime_invocation(
    *,
    container: AppContainer,
    session_id: str | None = None,
    session_context: SessionContext | None = None,
    transcript_projection: TranscriptProjection | None = None,
):
    invocation = container.runtime.invocation(
        session_id=session_id,
        session_context=session_context,
        transcript_projection=transcript_projection,
    )
    system_prompt = container.system_prompt()
    visible_tool_projection = container.tool_system.capability_registry().project("main")
    tool_policy = container.tool_system.policy()
    return replace(
        invocation,
        context=replace(
            invocation.context,
            rendered_system_prompt=system_prompt,
            visible_tool_projection=visible_tool_projection,
            tool_policy=tool_policy,
        ),
    )
