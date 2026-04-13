from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from dependency_injector import containers, providers
from langchain.agents import create_agent as langchain_create_agent

from coding_deepgent.memory import MemoryContextMiddleware
from coding_deepgent.prompting import build_prompt_context
from coding_deepgent.settings import Settings, build_openai_model, load_settings

from .filesystem import FilesystemContainer
from .runtime import RuntimeContainer
from .sessions import SessionsContainer
from .todo import TodoContainer
from .tool_system import ToolSystemContainer


def build_system_prompt(settings: Settings) -> str:
    return build_prompt_context(
        workdir=settings.workdir,
        agent_name=settings.agent_name,
        session_id="default",
        entrypoint=settings.entrypoint,
        custom_system_prompt=settings.custom_system_prompt,
        append_system_prompt=settings.append_system_prompt,
    ).system_prompt


def _singleton_list(item: object) -> list[object]:
    return [item]


def _combine_middleware(*groups: Sequence[object]) -> list[object]:
    combined: list[object] = []
    for group in groups:
        combined.extend(group)
    return combined


def _create_compiled_agent(
    create_agent_factory: Callable[..., Any],
    *,
    model: Any,
    tools: Sequence[object],
    system_prompt: str,
    middleware: Sequence[object],
    state_schema: type[Any],
    context_schema: type[Any],
    checkpointer: Any,
    store: Any,
):
    return create_agent_factory(
        model=model,
        tools=list(tools),
        system_prompt=system_prompt,
        middleware=list(middleware),
        state_schema=state_schema,
        context_schema=context_schema,
        checkpointer=checkpointer,
        store=store,
        name="coding-deepgent",
    )


class AppContainer(containers.DeclarativeContainer):
    settings: Any = providers.Dependency(default=providers.Singleton(load_settings))
    model: Any = providers.Dependency(default=providers.Factory(build_openai_model))
    create_agent_factory: Any = providers.Dependency(
        default=providers.Object(langchain_create_agent)
    )

    runtime: Any = providers.Container(RuntimeContainer, settings=settings)
    todo: Any = providers.Container(TodoContainer)
    filesystem: Any = providers.Container(FilesystemContainer)
    sessions: Any = providers.Container(SessionsContainer)
    tool_system: Any = providers.Container(
        ToolSystemContainer,
        filesystem_tools=filesystem.tools,
        todo_tools=todo.tools,
        permission_mode=settings.provided.permission_mode,
        event_sink=runtime.event_sink,
    )

    system_prompt: Any = providers.Callable(build_system_prompt, settings)
    memory_middleware: Any = providers.Factory(MemoryContextMiddleware)
    memory_middleware_list: Any = providers.Callable(_singleton_list, memory_middleware)
    middleware: Any = providers.Callable(
        _combine_middleware,
        todo.middleware_list,
        memory_middleware_list,
        tool_system.middleware_list,
    )
    agent: Any = providers.Factory(
        _create_compiled_agent,
        create_agent_factory=create_agent_factory,
        model=model,
        tools=tool_system.tools,
        system_prompt=system_prompt,
        middleware=middleware,
        state_schema=runtime.state_schema,
        context_schema=runtime.context_schema,
        checkpointer=runtime.checkpointer,
        store=runtime.store,
    )

    capability_registry: Any = tool_system.capability_registry
    session_store: Any = sessions.session_store
