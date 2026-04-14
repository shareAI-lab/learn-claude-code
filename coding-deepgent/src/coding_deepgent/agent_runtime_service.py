from __future__ import annotations

from collections.abc import Callable, MutableMapping
from inspect import Parameter, signature
from typing import Any

from coding_deepgent.containers import AppContainer
from coding_deepgent.runtime import RuntimeInvocation


def supports_keyword_argument(callback: Callable[..., Any], keyword: str) -> bool:
    try:
        parameters = signature(callback).parameters.values()
    except (TypeError, ValueError):
        return True

    return any(
        parameter.kind == Parameter.VAR_KEYWORD or parameter.name == keyword
        for parameter in parameters
    )


def resolve_compiled_agent(active_container: AppContainer, build_agent: Callable[..., Any]):
    if supports_keyword_argument(build_agent, "container"):
        return build_agent(container=active_container)
    return build_agent()


def invoke_agent(
    compiled_agent: Any,
    payload: dict[str, Any],
    invocation: RuntimeInvocation,
) -> dict[str, Any]:
    invoke = compiled_agent.invoke
    if supports_keyword_argument(invoke, "context") or supports_keyword_argument(
        invoke, "config"
    ):
        return invoke(payload, context=invocation.context, config=invocation.config)
    return invoke(payload)


def session_payload(session_state: MutableMapping[str, Any]) -> dict[str, Any]:
    return {
        "todos": session_state.get("todos", []),
        "rounds_since_update": session_state.get("rounds_since_update", 0),
    }


def update_session_state(
    session_state: MutableMapping[str, Any],
    result: dict[str, Any],
) -> None:
    session_state.update(
        {
            "todos": result.get("todos", []),
            "rounds_since_update": result.get("rounds_since_update", 0),
        }
    )
