from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Callable

from coding_deepgent.prompting import build_prompt_context
from coding_deepgent.runtime import RuntimeAgentBuildRequest, RuntimeAgentRole
from coding_deepgent.runtime.agent_factory import create_runtime_agent
from coding_deepgent.settings import Settings
from coding_deepgent.startup import StartupContractStatus


def build_system_prompt(settings: Settings) -> str:
    return build_prompt_context(
        workdir=settings.workdir,
        agent_name=settings.agent_name,
        session_id="default",
        entrypoint=settings.entrypoint,
        custom_system_prompt=settings.custom_system_prompt,
        append_system_prompt=settings.append_system_prompt,
    ).system_prompt


def singleton_list(item: object) -> list[object]:
    return [item]


def combine_middleware(*groups: Sequence[object]) -> list[object]:
    combined: list[object] = []
    for group in groups:
        combined.extend(group)
    return combined


def create_compiled_agent(
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
) -> Any:
    return create_runtime_agent(
        RuntimeAgentBuildRequest(
            role=RuntimeAgentRole.MAIN,
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            middleware=middleware,
            state_schema=state_schema,
            context_schema=context_schema,
            checkpointer=checkpointer,
            store=store,
            name="coding-deepgent",
        ),
        create_agent_factory=create_agent_factory,
    )


def create_compiled_agent_after_startup_validation(
    *,
    startup_contract: StartupContractStatus,
    create_agent_factory: Callable[..., Any],
    model: Any,
    tools: Sequence[object],
    system_prompt: str,
    middleware: Sequence[object],
    state_schema: type[Any],
    context_schema: type[Any],
    checkpointer: Any,
    store: Any,
) -> Any:
    del startup_contract
    return create_compiled_agent(
        create_agent_factory,
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
        state_schema=state_schema,
        context_schema=context_schema,
        checkpointer=checkpointer,
        store=store,
    )
