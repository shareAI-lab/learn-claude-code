from __future__ import annotations

from collections.abc import Callable, MutableMapping
from inspect import Parameter, signature
from typing import Any

from dependency_injector import providers
from langchain.agents import create_agent

from coding_deepgent.config import build_openai_model, load_settings
from coding_deepgent.containers import AppContainer
from coding_deepgent.runtime import RuntimeInvocation, default_runtime_state
from coding_deepgent.rendering import latest_assistant_text, normalize_messages

SESSION_STATE: dict[str, Any] = default_runtime_state()


def build_container() -> AppContainer:
    container = AppContainer(
        settings=providers.Singleton(load_settings),
        model=providers.Factory(build_openai_model),
        create_agent_factory=providers.Object(create_agent),
    )
    container.check_dependencies()
    return container


def build_agent(*, container: AppContainer | None = None):
    active_container = container or build_container()
    return active_container.agent()


def build_runtime_invocation(
    *,
    container: AppContainer | None = None,
    session_id: str | None = None,
) -> RuntimeInvocation:
    active_container = container or build_container()
    return active_container.runtime.invocation(session_id=session_id)


def _supports_keyword_argument(callback: Callable[..., Any], keyword: str) -> bool:
    try:
        parameters = signature(callback).parameters.values()
    except (TypeError, ValueError):
        return True

    return any(
        parameter.kind == Parameter.VAR_KEYWORD or parameter.name == keyword
        for parameter in parameters
    )


def _resolve_compiled_agent(active_container: AppContainer):
    if _supports_keyword_argument(build_agent, "container"):
        return build_agent(container=active_container)
    return build_agent()


def _invoke_agent(
    compiled_agent: Any,
    payload: dict[str, Any],
    invocation: RuntimeInvocation,
) -> dict[str, Any]:
    invoke = compiled_agent.invoke
    if _supports_keyword_argument(invoke, "context") or _supports_keyword_argument(
        invoke, "config"
    ):
        return invoke(payload, context=invocation.context, config=invocation.config)
    return invoke(payload)


def _session_payload(session_state: MutableMapping[str, Any]) -> dict[str, Any]:
    return {
        "todos": session_state.get("todos", []),
        "rounds_since_update": session_state.get("rounds_since_update", 0),
    }


def _update_session_state(
    session_state: MutableMapping[str, Any],
    result: dict[str, Any],
) -> None:
    session_state.update(
        {
            "todos": result.get("todos", []),
            "rounds_since_update": result.get("rounds_since_update", 0),
        }
    )


def agent_loop(
    messages: list[dict[str, Any]],
    *,
    container: AppContainer | None = None,
    session_state: MutableMapping[str, Any] | None = None,
    session_id: str | None = None,
) -> str:
    active_container = container or build_container()
    active_session_state = session_state if session_state is not None else SESSION_STATE
    normalized = normalize_messages(messages)
    invocation = build_runtime_invocation(
        container=active_container, session_id=session_id
    )
    result = _invoke_agent(
        _resolve_compiled_agent(active_container),
        {"messages": normalized, **_session_payload(active_session_state)},
        invocation,
    )
    _update_session_state(active_session_state, result)
    final_text = latest_assistant_text(result)
    if final_text:
        messages.append({"role": "assistant", "content": final_text})
    return final_text
