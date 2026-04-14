from __future__ import annotations

from types import SimpleNamespace
from typing import Sequence, cast

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.messages import AIMessage
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from pydantic import PrivateAttr
from langgraph.store.memory import InMemoryStore

from coding_deepgent.memory import (
    MemoryContextMiddleware,
    MemoryRecord,
    memory_namespace,
    save_memory,
    save_memory_record,
)
from coding_deepgent.context_payloads import ContextPayload, merge_system_message_content
from coding_deepgent.containers import AppContainer
from coding_deepgent.settings import Settings


class RecordingFakeModel(FakeMessagesListChatModel):
    _bound_tool_names: list[str] = PrivateAttr(default_factory=list)

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        del tool_choice, kwargs
        self._bound_tool_names = [
            getattr(tool, "name", type(tool).__name__) for tool in tools
        ]
        return self


def test_save_memory_tool_writes_to_langgraph_store_via_create_agent_runtime() -> None:
    store = InMemoryStore()
    model = RecordingFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "save_memory",
                        "args": {"content": "Remember LangChain stores"},
                        "id": "mem1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )

    agent = create_agent(model=model, tools=[save_memory], store=store)
    result = agent.invoke({"messages": [{"role": "user", "content": "save"}]})

    assert model._bound_tool_names == ["save_memory"]
    assert any("Saved memory" in str(message.content) for message in result["messages"])
    records = store.search(memory_namespace("project"))
    assert [item.value["content"] for item in records] == ["Remember LangChain stores"]


def test_save_memory_tool_rejects_transient_memory_via_create_agent_runtime() -> None:
    store = InMemoryStore()
    model = RecordingFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "save_memory",
                        "args": {"content": "Currently working on Stage 12D"},
                        "id": "mem1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )

    agent = create_agent(model=model, tools=[save_memory], store=store)
    result = agent.invoke({"messages": [{"role": "user", "content": "save"}]})

    assert any(
        "Memory not saved: memory looks like transient task/session state."
        in str(message.content)
        for message in result["messages"]
    )
    assert store.search(memory_namespace("project")) == []


def test_memory_context_middleware_injects_store_backed_memory() -> None:
    store = InMemoryStore()
    save_memory_record(
        store, MemoryRecord(content="Prefer LangChain stores for memory")
    )
    runtime = SimpleNamespace(store=store)
    captured: dict[str, object] = {}

    def handler(request: ModelRequest):
        captured["system_message"] = request.system_message
        return SimpleNamespace(result="ok")

    middleware = MemoryContextMiddleware()
    request = ModelRequest(
        model=RecordingFakeModel(responses=[]),
        messages=[HumanMessage(content="LangChain memory question")],
        system_message=SystemMessage(content="Base"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"messages": []},
        runtime=runtime,  # type: ignore[arg-type]
        model_settings={},
    )

    middleware.wrap_model_call(request, handler)

    system_message = captured["system_message"]
    assert isinstance(system_message, SystemMessage)
    assert "Relevant long-term memory" in str(system_message.content)
    assert "Prefer LangChain stores for memory" in str(system_message.content)


def test_memory_context_payload_renderer_path_is_shared() -> None:
    blocks = merge_system_message_content(
        [{"type": "text", "text": "Base"}],
        [
            ContextPayload(
                kind="memory",
                text="Relevant long-term memory:\n- [project] Prefer LangChain stores for memory",
                source="memory.project",
                priority=200,
            )
        ],
    )

    assert blocks == [
        {"type": "text", "text": "Base"},
        {
            "type": "text",
            "text": "Relevant long-term memory:\n- [project] Prefer LangChain stores for memory",
        },
    ]


def test_app_container_wires_memory_middleware_and_store() -> None:
    captured: dict[str, object] = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return object()

    container = AppContainer(
        settings=Settings(store_backend="memory"),
        model=object,
        create_agent_factory=fake_create_agent,
    )

    assert container.agent() is not None
    middleware_names = [
        type(item).__name__ for item in cast(Sequence[object], captured["middleware"])
    ]
    assert middleware_names == [
        "PlanContextMiddleware",
        "MemoryContextMiddleware",
        "ToolGuardMiddleware",
    ]
    assert captured["store"] is not None
