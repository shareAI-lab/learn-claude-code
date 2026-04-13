from __future__ import annotations

from typing import Any, Iterable, Sequence, cast

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from pydantic import PrivateAttr

from coding_deepgent import app
from coding_deepgent.memory import MemoryContextMiddleware
from coding_deepgent.middleware import PlanContextMiddleware
from coding_deepgent.runtime import RuntimeState
from coding_deepgent.tool_system import ToolGuardMiddleware

EXPECTED_TOOL_NAMES = [
    "bash",
    "read_file",
    "write_file",
    "edit_file",
    "TodoWrite",
    "save_memory",
    "load_skill",
    "task_create",
    "task_get",
    "task_list",
    "task_update",
    "run_subagent",
]


class RecordingFakeModel(FakeMessagesListChatModel):
    _bound_tool_names: list[str] = PrivateAttr(default_factory=list)

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        del tool_choice, kwargs
        self._bound_tool_names = [
            getattr(tool, "name", type(tool).__name__) for tool in tools
        ]
        return self


class FakeAgent:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.payloads.append(payload)
        return {
            "messages": [
                *payload["messages"],
                {"role": "assistant", "content": "planned"},
            ],
            "todos": [
                {
                    "content": "Ship it",
                    "status": "in_progress",
                    "activeForm": "Shipping",
                }
            ],
            "rounds_since_update": 0,
        }


def test_build_agent_binds_todowrite_product_tools(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(app, "build_openai_model", lambda: object())
    monkeypatch.setattr(app, "create_agent", fake_create_agent)

    agent = app.build_agent()

    assert agent is not None
    assert captured["state_schema"] is RuntimeState
    middleware = cast(Sequence[object], captured["middleware"])
    assert len(middleware) == 3
    assert isinstance(middleware[0], PlanContextMiddleware)
    assert isinstance(middleware[1], MemoryContextMiddleware)
    assert isinstance(middleware[2], ToolGuardMiddleware)
    tool_names = [
        getattr(tool, "name", getattr(tool, "__name__", ""))
        for tool in cast(Iterable[object], captured["tools"])
    ]
    assert tool_names == EXPECTED_TOOL_NAMES
    system_prompt = str(captured["system_prompt"])
    assert "explicit progress tracking helps on multi-step work" in system_prompt
    assert "activeForm for every todo" in system_prompt
    assert "write_plan" not in system_prompt


def test_agent_loop_roundtrips_todo_state(monkeypatch) -> None:
    fake = FakeAgent()
    monkeypatch.setattr(app, "build_agent", lambda: fake)
    monkeypatch.setattr(
        app,
        "SESSION_STATE",
        {
            "todos": [
                {
                    "content": "Inspect",
                    "status": "completed",
                    "activeForm": "Inspecting",
                }
            ],
            "rounds_since_update": 2,
        },
    )

    history = [
        {"role": "user", "content": "hello"},
        {"role": "user", "content": "continue"},
    ]

    assert app.agent_loop(history) == "planned"
    assert fake.payloads[0]["messages"] == [
        {"role": "user", "content": "hello\n\ncontinue"}
    ]
    assert fake.payloads[0]["rounds_since_update"] == 2
    assert fake.payloads[0]["todos"] == [
        {"content": "Inspect", "status": "completed", "activeForm": "Inspecting"}
    ]
    assert history[-1] == {"role": "assistant", "content": "planned"}
    assert app.SESSION_STATE["todos"] == [
        {"content": "Ship it", "status": "in_progress", "activeForm": "Shipping"}
    ]


def test_free_agent_path_executes_todowrite_without_runtime_injection_error(
    monkeypatch,
) -> None:
    model = RecordingFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "TodoWrite",
                        "args": {
                            "todos": [
                                {
                                    "content": "Inspect repo",
                                    "status": "in_progress",
                                    "activeForm": "Inspecting",
                                },
                                {
                                    "content": "Summarize findings",
                                    "status": "pending",
                                    "activeForm": "Summarizing",
                                },
                            ]
                        },
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="planned"),
        ]
    )

    monkeypatch.setattr(app, "build_openai_model", lambda: model)
    monkeypatch.setattr(
        app,
        "SESSION_STATE",
        {
            "todos": [],
            "rounds_since_update": 0,
        },
    )

    history = [{"role": "user", "content": "plan this work"}]
    assert app.agent_loop(history) == "planned"
    assert model._bound_tool_names == EXPECTED_TOOL_NAMES
    assert app.SESSION_STATE["todos"] == [
        {
            "content": "Inspect repo",
            "status": "in_progress",
            "activeForm": "Inspecting",
        },
        {
            "content": "Summarize findings",
            "status": "pending",
            "activeForm": "Summarizing",
        },
    ]
