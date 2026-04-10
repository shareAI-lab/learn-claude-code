from __future__ import annotations

import importlib


def test_s02_normalize_messages_merges_consecutive_roles() -> None:
    s02 = importlib.import_module('agents_deepagents.s02_tool_use')

    messages = [
        {'role': 'user', 'content': 'first'},
        {'role': 'user', 'content': 'second'},
        {'role': 'assistant', 'content': 'third'},
        {'role': 'assistant', 'content': 'fourth'},
    ]

    assert s02.normalize_messages(messages) == [
        {'role': 'user', 'content': 'first\n\nsecond'},
        {'role': 'assistant', 'content': 'third\n\nfourth'},
    ]


def test_s02_agent_loop_appends_one_final_answer(monkeypatch) -> None:
    s02 = importlib.import_module('agents_deepagents.s02_tool_use')

    class FakeAgent:
        def __init__(self) -> None:
            self.calls: list[list[dict[str, str]]] = []

        def invoke(self, payload):
            self.calls.append(payload['messages'])
            return {'messages': [*payload['messages'], {'role': 'assistant', 'content': 'done'}]}

    fake = FakeAgent()
    monkeypatch.setattr(s02, 'build_agent', lambda: fake)

    history = [
        {'role': 'user', 'content': 'hello'},
        {'role': 'user', 'content': 'again'},
    ]

    assert s02.agent_loop(history) == 'done'
    assert history == [
        {'role': 'user', 'content': 'hello'},
        {'role': 'user', 'content': 'again'},
        {'role': 'assistant', 'content': 'done'},
    ]
    assert fake.calls == [[{'role': 'user', 'content': 'hello\n\nagain'}]]


def test_s02_build_agent_uses_middleware_without_custom_state(monkeypatch) -> None:
    s02 = importlib.import_module('agents_deepagents.s02_tool_use')
    captured: dict[str, object] = {}

    def fake_create_agent(*, model, tools, system_prompt, middleware):
        captured['model'] = model
        captured['tools'] = tools
        captured['system_prompt'] = system_prompt
        captured['middleware'] = middleware
        return object()

    monkeypatch.setattr(s02, 'build_openai_model', lambda: object())
    monkeypatch.setattr(s02, 'create_agent', fake_create_agent)

    agent = s02.build_agent()

    assert agent is not None
    middleware = captured['middleware']
    assert len(middleware) == 1
    assert middleware[0].__class__.__name__ == 'ToolUseMiddleware'
    assert not hasattr(s02, 'ToolUseState')
    assert captured['tools'] == s02.TOOLS
