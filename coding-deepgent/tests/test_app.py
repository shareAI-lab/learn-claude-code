from __future__ import annotations

from coding_deepgent import app
from coding_deepgent.middleware import PlanningMiddleware
from coding_deepgent.state import PlanningState


def test_build_agent_wires_cumulative_s03_components(monkeypatch) -> None:
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
    assert isinstance(captured["middleware"][0], PlanningMiddleware)
    tool_names = [tool.__name__ for tool in captured["tools"]]
    assert tool_names == ["bash", "read_file", "write_file", "edit_file", "todo"]
    assert "todo tool" in captured["system_prompt"]


def test_agent_loop_roundtrips_runtime_state(monkeypatch) -> None:
    class FakeAgent:
        def __init__(self) -> None:
            self.payloads = []

        def invoke(self, payload):
            self.payloads.append(payload)
            return {
                "messages": [*payload["messages"], {"role": "assistant", "content": "planned"}],
                "plan_items": [{"content": "Ship it", "status": "in_progress", "active_form": "Shipping"}],
                "rounds_since_update": 0,
                "updated_this_turn": False,
            }

    fake = FakeAgent()
    monkeypatch.setattr(app, "build_agent", lambda: fake)
    monkeypatch.setattr(
        app,
        "SESSION_STATE",
        {
            "plan_items": [{"content": "Inspect", "status": "completed", "active_form": ""}],
            "rounds_since_update": 2,
            "updated_this_turn": False,
        },
    )

    history = [
        {"role": "user", "content": "hello"},
        {"role": "user", "content": "continue"},
    ]

    assert app.agent_loop(history) == "planned"
    assert fake.payloads[0]["messages"] == [{"role": "user", "content": "hello\n\ncontinue"}]
    assert fake.payloads[0]["rounds_since_update"] == 2
    assert fake.payloads[0]["plan_items"] == [
        {"content": "Inspect", "status": "completed", "active_form": ""}
    ]
    assert history[-1] == {"role": "assistant", "content": "planned"}
    assert app.SESSION_STATE["plan_items"] == [
        {"content": "Ship it", "status": "in_progress", "active_form": "Shipping"}
    ]
