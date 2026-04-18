from __future__ import annotations

from typing import Any

from dependency_injector import containers, providers
from langchain.agents import create_agent as langchain_create_agent

from coding_deepgent import agent_service
from coding_deepgent.compact import RuntimePressureMiddleware
from coding_deepgent import extensions_service
from coding_deepgent.memory import MemoryContextMiddleware
from coding_deepgent.sessions.session_memory_middleware import (
    SessionMemoryContextMiddleware,
)
from coding_deepgent.settings import build_openai_model, load_settings
from coding_deepgent.startup import require_startup_contract, validate_startup_contract

from .filesystem import FilesystemContainer
from .memory_backend import MemoryBackendContainer
from .runtime import RuntimeContainer
from .sessions import SessionsContainer
from .todo import TodoContainer
from .tool_system import ToolSystemContainer

class AppContainer(containers.DeclarativeContainer):
    settings: Any = providers.Dependency(default=providers.Singleton(load_settings))
    model: Any = providers.Dependency(default=providers.Factory(build_openai_model))
    create_agent_factory: Any = providers.Dependency(
        default=providers.Object(langchain_create_agent)
    )
    extension_capabilities: Any = providers.Dependency(default=providers.Object([]))

    runtime: Any = providers.Container(RuntimeContainer, settings=settings)
    memory_backend: Any = providers.Container(MemoryBackendContainer, settings=settings)
    todo: Any = providers.Container(TodoContainer)
    filesystem: Any = providers.Container(FilesystemContainer)
    sessions: Any = providers.Container(SessionsContainer)
    mcp_runtime_load_result: Any = providers.Callable(
        extensions_service.mcp_runtime_load_result,
        settings,
    )
    mcp_capabilities: Any = providers.Callable(
        extensions_service.mcp_capabilities,
        mcp_runtime_load_result,
    )
    all_extension_capabilities: Any = providers.Callable(
        extensions_service.combine_extension_capabilities,
        extension_capabilities,
        mcp_capabilities,
    )
    tool_system: Any = providers.Container(
        ToolSystemContainer,
        filesystem_tools=filesystem.tools,
        todo_tools=todo.tools,
        extension_capabilities=all_extension_capabilities,
        permission_mode=settings.provided.permission_mode,
        permission_allow_rules=settings.provided.permission_allow_rules,
        permission_ask_rules=settings.provided.permission_ask_rules,
        permission_deny_rules=settings.provided.permission_deny_rules,
        workdir=settings.provided.workdir,
        trusted_workdirs=settings.provided.trusted_workdirs,
        event_sink=runtime.event_sink,
    )

    plugin_registry: Any = providers.Callable(extensions_service.plugin_registry, settings)
    validated_plugin_registry: Any = providers.Callable(
        extensions_service.validate_plugin_registry,
        plugin_registry,
        settings,
        tool_system.capability_registry,
    )
    startup_contract: Any = providers.Callable(
        validate_startup_contract,
        validated_plugin_registry=validated_plugin_registry,
        mcp_runtime_load_result=mcp_runtime_load_result,
    )
    validated_startup_contract: Any = providers.Callable(
        require_startup_contract,
        startup_contract,
    )
    system_prompt: Any = providers.Callable(agent_service.build_system_prompt, settings)
    memory_middleware: Any = providers.Factory(MemoryContextMiddleware)
    memory_middleware_list: Any = providers.Callable(
        agent_service.singleton_list, memory_middleware
    )
    session_memory_middleware: Any = providers.Factory(SessionMemoryContextMiddleware)
    session_memory_middleware_list: Any = providers.Callable(
        agent_service.singleton_list, session_memory_middleware
    )
    runtime_pressure_middleware: Any = providers.Factory(
        RuntimePressureMiddleware,
        registry=tool_system.capability_registry,
        keep_recent_tool_results=settings.provided.keep_recent_tool_results,
        microcompact_time_gap_minutes=settings.provided.microcompact_time_gap_minutes,
        microcompact_min_saved_tokens=settings.provided.microcompact_min_saved_tokens,
        microcompact_protect_recent_tokens=(
            settings.provided.microcompact_protect_recent_tokens
        ),
        microcompact_min_prune_saved_tokens=(
            settings.provided.microcompact_min_prune_saved_tokens
        ),
        main_entrypoint=settings.provided.entrypoint,
        main_agent_name=settings.provided.agent_name,
        snip_threshold_tokens=settings.provided.snip_threshold_tokens,
        keep_recent_messages_after_snip=(
            settings.provided.keep_recent_messages_after_snip
        ),
        collapse_threshold_tokens=settings.provided.collapse_threshold_tokens,
        keep_recent_messages_after_collapse=(
            settings.provided.keep_recent_messages_after_collapse
        ),
        model_context_window_tokens=settings.provided.model_context_window_tokens,
        collapse_trigger_ratio=settings.provided.collapse_trigger_ratio,
        auto_compact_threshold_tokens=settings.provided.auto_compact_threshold_tokens,
        auto_compact_max_failures=settings.provided.auto_compact_max_failures,
        auto_compact_ptl_retry_limit=settings.provided.auto_compact_ptl_retry_limit,
        keep_recent_messages=settings.provided.keep_recent_messages_after_compact,
    )
    runtime_pressure_middleware_list: Any = providers.Callable(
        agent_service.singleton_list, runtime_pressure_middleware
    )
    middleware: Any = providers.Callable(
        agent_service.combine_middleware,
        todo.middleware_list,
        memory_middleware_list,
        session_memory_middleware_list,
        runtime_pressure_middleware_list,
        tool_system.middleware_list,
    )
    agent: Any = providers.Factory(
        agent_service.create_compiled_agent_after_startup_validation,
        startup_contract=validated_startup_contract,
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
