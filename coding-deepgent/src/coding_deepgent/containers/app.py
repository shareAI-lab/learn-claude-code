from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from dependency_injector import containers, providers
from langchain.agents import create_agent as langchain_create_agent

from coding_deepgent.settings import Settings, build_openai_model, load_settings

from .filesystem import FilesystemContainer
from .runtime import RuntimeContainer
from .sessions import SessionsContainer
from .todo import TodoContainer
from .tool_system import ToolSystemContainer


def build_system_prompt(settings: Settings) -> str:
    return (
        "You are coding-deepgent, an independent cumulative LangChain cc product. "
        f"Current workspace: {settings.workdir}. "
        "Use the TodoWrite tool when explicit progress tracking helps on multi-step work, "
        "preserve exactly one in-progress todo, include activeForm for every todo, "
        "and prefer tools over prose."
    )


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
    )

    system_prompt: Any = providers.Callable(build_system_prompt, settings)
    middleware: Any = providers.Callable(list, todo.middleware_list)
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
