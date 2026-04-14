from __future__ import annotations

from typing import Any

from dependency_injector import containers, providers

from coding_deepgent.hooks import LocalHookRegistry
from coding_deepgent.runtime import (
    InMemoryEventSink,
    PlanningState,
    RuntimeContext,
    build_runtime_context,
    build_runtime_invocation,
    default_runtime_state,
    select_checkpointer,
    select_store,
)


class RuntimeContainer(containers.DeclarativeContainer):
    settings: Any = providers.Dependency()

    event_sink: Any = providers.Singleton(InMemoryEventSink)
    hook_registry: Any = providers.Singleton(LocalHookRegistry)
    state_schema: Any = providers.Object(PlanningState)
    context_schema: Any = providers.Object(RuntimeContext)
    default_state: Any = providers.Callable(default_runtime_state)
    context: Any = providers.Factory(
        build_runtime_context,
        settings=settings,
        event_sink=event_sink,
        hook_registry=hook_registry,
    )
    invocation: Any = providers.Factory(
        build_runtime_invocation,
        settings=settings,
        event_sink=event_sink,
        hook_registry=hook_registry,
    )
    checkpointer: Any = providers.Singleton(
        select_checkpointer,
        backend=settings.provided.checkpointer_backend,
    )
    store: Any = providers.Singleton(
        select_store,
        backend=settings.provided.store_backend,
    )
