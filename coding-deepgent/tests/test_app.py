from __future__ import annotations

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from pydantic import PrivateAttr

from coding_deepgent import app
from coding_deepgent.middleware import PlanContextMiddleware
from coding_deepgent.state import PlanningState


class RecordingFakeModel(FakeMessagesListChatModel):
    _bound_tool_names: list[str] = PrivateAttr(default_factory=list)

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        del tool_choice, kwargs
        self._bound_tool_names = [getattr(tool, "name", type(tool).__name__) for tool in tools]
        return self


def test_build_agent_binds_todowrite_product_tools(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(app, "build_openai_model", lambda: object())
    monkeypatch.setattr(app, "create_agent", fake_create_agent)

    agent = app.build_agent()

    assert agent is not None
    assert captured["state_schema"] is PlanningState
    assert len(captured["middleware"]) == 1
    assert isinstance(captured["middleware"][0], PlanContextMiddleware)
    tool_names = [getattr(tool, "name", getattr(tool, "__name__", "")) for tool in captured["tools"]]
    assert tool_names == ["bash", "read_file", "write_file", "edit_file", "TodoWrite"]
    assert "explicit progress tracking helps on multi-step work" in captured["system_prompt"]
    assert "activeForm for every todo" in captured["system_prompt"]
    assert "write_plan" not in captured["system_prompt"]


def test_agent_loop_roundtrips_todo_state(monkeypatch) -> None:
    class FakeAgent:
        def __init__(self) -> None:
            self.payloads = []

        def invoke(self, payload):
            self.payloads.append(payload)
            return {
                "messages": [*payload["messages"], {"role": "assistant", "content": "planned"}],
                "todos": [{"content": "Ship it", "status": "in_progress", "activeForm": "Shipping"}],
                "rounds_since_update": 0,
            }

    fake = FakeAgent()
    monkeypatch.setattr(app, "build_agent", lambda: fake)
    monkeypatch.setattr(
        app,
        "SESSION_STATE",
        {
            "todos": [{"content": "Inspect", "status": "completed", "activeForm": "Inspecting"}],
            "rounds_since_update": 2,
        },
    )

    history = [
        {"role": "user", "content": "hello"},
        {"role": "user", "content": "continue"},
    ]

    assert app.agent_loop(history) == "planned"
    assert fake.payloads[0]["messages"] == [{"role": "user", "content": "hello\n\ncontinue"}]
    assert fake.payloads[0]["rounds_since_update"] == 2
    assert fake.payloads[0]["todos"] == [
        {"content": "Inspect", "status": "completed", "activeForm": "Inspecting"}
    ]
    assert history[-1] == {"role": "assistant", "content": "planned"}
    assert app.SESSION_STATE["todos"] == [
        {"content": "Ship it", "status": "in_progress", "activeForm": "Shipping"}
    ]


def test_free_agent_path_executes_todowrite_without_runtime_injection_error(monkeypatch) -> None:
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
    assert model._bound_tool_names == ["bash", "read_file", "write_file", "edit_file", "TodoWrite"]
    assert app.SESSION_STATE["todos"] == [
        {"content": "Inspect repo", "status": "in_progress", "activeForm": "Inspecting"},
        {"content": "Summarize findings", "status": "pending", "activeForm": "Summarizing"},
    ]
