from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from langchain.agents import create_agent as langchain_create_agent

from coding_deepgent.runtime.roles import RuntimeAgentRole


@dataclass(frozen=True, slots=True)
class RuntimeAgentBuildRequest:
    role: RuntimeAgentRole
    name: str
    model: Any
    tools: Sequence[object]
    system_prompt: str
    middleware: Sequence[object] = ()
    context_schema: type[Any] | None = None
    state_schema: type[Any] | None = None
    checkpointer: Any = None
    store: Any = None


class RuntimeAgentFactory(Protocol):
    def __call__(
        self,
        request: RuntimeAgentBuildRequest,
        *,
        create_agent_factory: Callable[..., Any] | None = None,
    ) -> Any: ...


def create_runtime_agent(
    request: RuntimeAgentBuildRequest,
    *,
    create_agent_factory: Callable[..., Any] | None = None,
) -> Any:
    factory = create_agent_factory or langchain_create_agent
    kwargs: dict[str, Any] = {
        "model": request.model,
        "tools": list(request.tools),
        "system_prompt": request.system_prompt,
        "middleware": list(request.middleware),
        "name": request.name,
    }
    if request.context_schema is not None:
        kwargs["context_schema"] = request.context_schema
    if request.state_schema is not None:
        kwargs["state_schema"] = request.state_schema
    if request.checkpointer is not None:
        kwargs["checkpointer"] = request.checkpointer
    if request.store is not None:
        kwargs["store"] = request.store
    return factory(**kwargs)
