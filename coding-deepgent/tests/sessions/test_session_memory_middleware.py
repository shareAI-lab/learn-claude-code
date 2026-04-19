from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from langchain.agents.middleware import ModelRequest
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from pydantic import PrivateAttr

from coding_deepgent.sessions.session_memory import SESSION_MEMORY_STATE_KEY
from coding_deepgent.sessions.session_memory_middleware import (
    SessionMemoryContextMiddleware,
)


class RecordingFakeModel(FakeMessagesListChatModel):
    _bound_tool_names: list[str] = PrivateAttr(default_factory=list)

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        del tools, tool_choice, kwargs
        return self


def test_session_memory_context_middleware_injects_current_session_memory() -> None:
    captured: dict[str, object] = {}

    def handler(request: ModelRequest):
        captured["system_message"] = request.system_message
        return SimpleNamespace(result="ok")

    middleware = SessionMemoryContextMiddleware()
    request = ModelRequest(
        model=RecordingFakeModel(responses=[]),
        messages=[HumanMessage(content="continue")],
        system_message=SystemMessage(content="Base"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state=cast(
            Any,
            {
            "messages": [],
            SESSION_MEMORY_STATE_KEY: {
                "content": "Current repo focus is deterministic assist.",
                "source": "manual",
                "message_count": 1,
                "updated_at": "2026-04-18T00:00:00Z",
            },
            },
        ),
        runtime=SimpleNamespace(store=None),  # type: ignore[arg-type]
        model_settings={},
    )

    middleware.wrap_model_call(request, handler)

    system_message = captured["system_message"]
    assert isinstance(system_message, SystemMessage)
    text = str(system_message.content)
    assert "Current-session memory:" in text
    assert "Current repo focus is deterministic assist." in text


def test_session_memory_context_middleware_marks_stale_when_token_pressure_exceeds_threshold() -> None:
    captured: dict[str, object] = {}

    def handler(request: ModelRequest):
        captured["system_message"] = request.system_message
        return SimpleNamespace(result="ok")

    middleware = SessionMemoryContextMiddleware()
    request = ModelRequest(
        model=RecordingFakeModel(responses=[]),
        messages=[HumanMessage(content="x" * 24000)],
        system_message=SystemMessage(content="Base"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state=cast(
            Any,
            {
                "messages": [],
                SESSION_MEMORY_STATE_KEY: {
                    "content": "Current repo focus is deterministic assist.",
                    "source": "manual",
                    "message_count": 1,
                    "token_count": 10,
                    "tool_call_count": 0,
                    "updated_at": "2026-04-18T00:00:00Z",
                },
            },
        ),
        runtime=SimpleNamespace(store=None),  # type: ignore[arg-type]
        model_settings={},
    )

    middleware.wrap_model_call(request, handler)

    system_message = captured["system_message"]
    assert isinstance(system_message, SystemMessage)
    text = str(system_message.content)
    assert "Current-session memory:" in text
    assert "[stale]" in text
