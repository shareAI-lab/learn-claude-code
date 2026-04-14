from __future__ import annotations

from collections.abc import Callable
from typing import Any

from dependency_injector import providers

from coding_deepgent.containers import AppContainer
from coding_deepgent.sessions.records import SessionContext


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
):
    return container.runtime.invocation(
        session_id=session_id,
        session_context=session_context,
    )
