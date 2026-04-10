from __future__ import annotations

import importlib
from types import SimpleNamespace

from langchain.messages import ToolMessage
from langgraph.types import Command


def test_s03_todo_updates_custom_state_via_command() -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')

    command = s03.todo(
        [
            {'content': 'Inspect repo', 'status': 'completed'},
            {'content': 'Implement change', 'status': 'in_progress', 'activeForm': 'Implementing'},
        ],
        runtime=SimpleNamespace(tool_call_id='call-1'),
    )

    assert isinstance(command, Command)
    assert command.update['plan_items'] == [
        {'content': 'Inspect repo', 'status': 'completed', 'active_form': ''},
        {'content': 'Implement change', 'status': 'in_progress', 'active_form': 'Implementing'},
    ]
    assert command.update['rounds_since_update'] == 0
    assert command.update['updated_this_turn'] is True
    assert isinstance(command.update['messages'][0], ToolMessage)


def test_s03_middleware_tracks_stale_rounds() -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')
    middleware = s03.PlanningMiddleware()

    assert middleware.after_agent(
        {
            'messages': [],
            'plan_items': [{'content': 'Keep going', 'status': 'pending', 'active_form': ''}],
            'rounds_since_update': 2,
            'updated_this_turn': False,
        },
        runtime=None,
    ) == {'rounds_since_update': 3}

    assert middleware.after_agent(
        {
            'messages': [],
            'plan_items': [{'content': 'Keep going', 'status': 'pending', 'active_form': ''}],
            'rounds_since_update': 0,
            'updated_this_turn': True,
        },
        runtime=None,
    ) == {'updated_this_turn': False}


def test_s03_agent_loop_roundtrips_runtime_state(monkeypatch) -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')

    class FakeAgent:
        def __init__(self) -> None:
            self.payloads = []

        def invoke(self, payload):
            self.payloads.append(payload)
            return {
                'messages': [*payload['messages'], {'role': 'assistant', 'content': 'planned'}],
                'plan_items': [{'content': 'Ship it', 'status': 'in_progress', 'active_form': 'Shipping'}],
                'rounds_since_update': 0,
                'updated_this_turn': False,
            }

    fake = FakeAgent()
    monkeypatch.setattr(s03, 'build_agent', lambda: fake)
    monkeypatch.setattr(
        s03,
        'SESSION_STATE',
        {
            'plan_items': [{'content': 'Inspect', 'status': 'completed', 'active_form': ''}],
            'rounds_since_update': 2,
            'updated_this_turn': False,
        },
    )

    history = [{'role': 'user', 'content': 'continue'}]
    assert s03.agent_loop(history) == 'planned'
    assert fake.payloads[0]['rounds_since_update'] == 2
    assert fake.payloads[0]['plan_items'] == [
        {'content': 'Inspect', 'status': 'completed', 'active_form': ''}
    ]
    assert history[-1] == {'role': 'assistant', 'content': 'planned'}
    assert s03.SESSION_STATE['plan_items'] == [
        {'content': 'Ship it', 'status': 'in_progress', 'active_form': 'Shipping'}
    ]
