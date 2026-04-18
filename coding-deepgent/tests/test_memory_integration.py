from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Sequence, cast

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langgraph.store.memory import InMemoryStore
from pydantic import PrivateAttr

from coding_deepgent.context_payloads import ContextPayload, merge_system_message_content
from coding_deepgent.containers import AppContainer
from coding_deepgent.memory import (
    LONG_TERM_MEMORY_STATE_KEY,
    MemoryContextMiddleware,
    MemoryRecord,
    delete_memory,
    list_memory,
    memory_namespace,
    save_memory,
    save_memory_record,
)
from coding_deepgent.settings import Settings
from coding_deepgent.todo.middleware import PlanContextMiddleware


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
                        "args": {
                            "type": "feedback",
                            "rule": "Run lint before commit",
                            "why": "The repo requires clean validation before code submission",
                            "how_to_apply": "Before any commit-like completion step, run lint first",
                        },
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
    assert any(
        "Saved feedback memory" in str(message.content) for message in result["messages"]
    )
    records = store.search(memory_namespace("feedback"))
    assert [item.value["rule"] for item in records] == ["Run lint before commit"]


def test_save_memory_tool_rejects_transient_memory_via_create_agent_runtime() -> None:
    store = InMemoryStore()
    model = RecordingFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "save_memory",
                        "args": {
                            "type": "project",
                            "fact_or_decision": "Currently working on Stage 12D",
                            "why": "It is the active task right now",
                            "how_to_apply": "Continue the task in this session",
                        },
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


def test_list_memory_tool_renders_keys_and_type_filtered_entries() -> None:
    store = InMemoryStore()
    entry_key = save_memory_record(
        store,
        MemoryRecord(
            type="feedback",
            rule="Run lint before commit",
            why="The repo requires clean validation before code submission",
            how_to_apply="Before any commit-like completion step, run lint first",
        ),
    )
    model = RecordingFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "list_memory",
                        "args": {"type": "feedback"},
                        "id": "mem1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )

    agent = create_agent(model=model, tools=[list_memory], store=store)
    result = agent.invoke({"messages": [{"role": "user", "content": "list"}]})

    assert any("Long-term memory entries:" in str(message.content) for message in result["messages"])
    assert any(entry_key in str(message.content) for message in result["messages"])
    assert any("Run lint before commit" in str(message.content) for message in result["messages"])


def test_delete_memory_tool_removes_entry_via_create_agent_runtime() -> None:
    store = InMemoryStore()
    entry_key = save_memory_record(
        store,
        MemoryRecord(
            type="feedback",
            rule="Run lint before commit",
            why="The repo requires clean validation before code submission",
            how_to_apply="Before any commit-like completion step, run lint first",
        ),
    )
    model = RecordingFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "delete_memory",
                        "args": {"type": "feedback", "key": entry_key},
                        "id": "mem1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )

    agent = create_agent(model=model, tools=[delete_memory], store=store)
    result = agent.invoke({"messages": [{"role": "user", "content": "delete"}]})

    assert any(
        f"Deleted feedback memory {entry_key}." in str(message.content)
        for message in result["messages"]
    )
    assert store.search(memory_namespace("feedback")) == []


def test_memory_context_middleware_injects_store_backed_memory() -> None:
    store = InMemoryStore()
    save_memory_record(
        store,
        MemoryRecord(
            type="feedback",
            rule="Run lint before commit",
            why="The repo requires clean validation before code submission",
            how_to_apply="Before any commit-like completion step, run lint first",
        ),
    )
    runtime = SimpleNamespace(store=store)
    captured: dict[str, object] = {}

    def handler(request: ModelRequest):
        captured["system_message"] = request.system_message
        captured["state"] = request.state
        return SimpleNamespace(result="ok")

    middleware = MemoryContextMiddleware()
    request = ModelRequest(
        model=RecordingFakeModel(responses=[]),
        messages=[HumanMessage(content="lint memory question")],
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
    assert "Feedback memory:" in str(system_message.content)
    assert "Run lint before commit" in str(system_message.content)
    assert LONG_TERM_MEMORY_STATE_KEY in cast(dict[str, object], captured["state"])


def test_memory_context_payload_renderer_path_is_shared() -> None:
    payload_text = (
        "Relevant long-term memory:\n"
        "Feedback memory:\n"
        "- Rule: Run lint before commit\n"
        "  Why: The repo requires clean validation before code submission\n"
        "  How to apply: Before any commit-like completion step, run lint first"
    )
    blocks = merge_system_message_content(
        [{"type": "text", "text": "Base"}],
        [
            ContextPayload(
                kind="memory",
                text=payload_text,
                source="memory.long_term",
                priority=200,
            )
        ],
    )

    assert blocks == [
        {"type": "text", "text": "Base"},
        {"type": "text", "text": payload_text},
    ]


def test_memory_context_middleware_respects_type_scope() -> None:
    store = InMemoryStore()
    save_memory_record(
        store,
        MemoryRecord(
            type="project",
            fact_or_decision="Use JWT for auth",
            why="Mobile clients need stateless authentication",
            how_to_apply="Prefer JWT-compatible auth changes",
        ),
    )
    save_memory_record(
        store,
        MemoryRecord(
            type="user",
            profile="User prefers concise answers by default",
            why_it_matters="Summaries should stay brief unless depth is requested",
            how_to_apply="Default to concise status updates and closers",
        ),
    )
    runtime = SimpleNamespace(store=store)
    captured: dict[str, object] = {}

    def handler(request: ModelRequest):
        captured["system_message"] = request.system_message
        return SimpleNamespace(result="ok")

    middleware = MemoryContextMiddleware(memory_type="user")
    request = ModelRequest(
        model=RecordingFakeModel(responses=[]),
        messages=[HumanMessage(content="concise user memory question")],
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
    text = str(system_message.content)
    assert "User memory:" in text
    assert "User prefers concise answers by default" in text
    assert "Use JWT for auth" not in text


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
        "SessionMemoryContextMiddleware",
        "RuntimePressureMiddleware",
        "ToolGuardMiddleware",
    ]
    assert captured["store"] is not None


def test_resume_todo_and_memory_context_compose_without_duplication() -> None:
    store = InMemoryStore()
    save_memory_record(
        store,
        MemoryRecord(
            type="project",
            fact_or_decision="Use LangChain store for long-term memory",
            why="Cross-session continuity should not depend on transcript replay alone",
            how_to_apply="Prefer store-backed memory for durable reusable knowledge",
        ),
    )
    runtime = SimpleNamespace(store=store)
    captured: dict[str, object] = {}

    def final_handler(request: ModelRequest):
        captured["messages"] = request.messages
        captured["system_message"] = request.system_message
        return SimpleNamespace(result="ok")

    request = ModelRequest(
        model=RecordingFakeModel(responses=[]),
        messages=[
            SystemMessage(content="Resumed session context. Use this brief as continuation context."),
            HumanMessage(content="continue the work"),
        ],
        system_message=SystemMessage(content="Base"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state=cast(
            Any,
            {
                "messages": [],
                "todos": [
                    {
                        "content": "Close Stage 22",
                        "status": "in_progress",
                        "activeForm": "Closing Stage 22",
                    }
                ],
                "rounds_since_update": 1,
            },
        ),
        runtime=runtime,  # type: ignore[arg-type]
        model_settings={},
    )

    memory_middleware = MemoryContextMiddleware()
    planning_middleware = PlanContextMiddleware()

    planning_middleware.wrap_model_call(
        request,
        lambda planned_request: memory_middleware.wrap_model_call(
            planned_request, final_handler
        ),
    )

    system_message = captured["system_message"]
    assert isinstance(system_message, SystemMessage)
    text = str(system_message.content)
    assert "Base" in text
    assert "Current session todos:" in text
    assert "Relevant long-term memory" in text
    assert "Project memory:" in text
    assert text.index("Current session todos:") < text.index("Relevant long-term memory")
    assert text.count("Resumed session context.") == 0
    messages = cast(Sequence[object], captured["messages"])
    assert any("Resumed session context." in str(getattr(message, "content", "")) for message in messages)
