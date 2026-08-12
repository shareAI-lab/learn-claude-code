import types

from homework.agent_app.config import AppConfig
from homework.agent_app.features.subagents import spawn_subagent
from homework.agent_app.tools.hooks import HookRegistry


class FakeAdapter:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.responses)


def text_response(text):
    return types.SimpleNamespace(
        stop_reason="end_turn",
        content=[types.SimpleNamespace(type="text", text=text)],
    )


def test_subagent_uses_fresh_history(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")
    config = AppConfig.from_env(tmp_path)
    fake_adapter = FakeAdapter([text_response("done")])

    result = spawn_subagent(
        description="inspect parser",
        llm=fake_adapter,
        config=config,
        system="subagent system",
        tools=[],
        handlers={},
        hooks=HookRegistry(),
    )

    assert result == "done"
    assert fake_adapter.calls[0]["messages"] == [
        {"role": "user", "content": "inspect parser"}
    ]
