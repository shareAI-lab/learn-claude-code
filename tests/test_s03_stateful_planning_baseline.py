from __future__ import annotations

import importlib

from langchain_core.messages import AIMessage
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain.messages import ToolMessage
from pydantic import ValidationError
import pytest
from langgraph.types import Command


def test_s03_todo_updates_custom_state_via_command() -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')

    command = s03.todo(
        [
            {'content': 'Inspect repo', 'status': 'completed'},
            {'content': 'Implement change', 'status': 'in_progress', 'activeForm': 'Implementing'},
        ],
        tool_call_id='call-1',
    )

    assert isinstance(command, Command)
    assert command.update['items'] == [
        {'content': 'Inspect repo', 'status': 'completed'},
        {'content': 'Implement change', 'status': 'in_progress', 'activeForm': 'Implementing'},
    ]
    assert command.update['rounds_since_update'] == 0
    assert isinstance(command.update['messages'][0], ToolMessage)


def test_s03_todo_schema_requires_structured_items() -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')

    schema = s03.todo_tool.tool_call_schema.model_json_schema()
    item_schema = schema['$defs']['TodoPlanItemInput']

    assert schema['required'] == ['items']
    assert item_schema['required'] == ['content', 'status']
    assert item_schema['additionalProperties'] is False
    assert item_schema['properties']['status']['enum'] == [
        'pending',
        'in_progress',
        'completed',
    ]
    assert 'tool_call_id' not in schema['properties']


def test_s03_todo_prompts_include_complexity_guidance() -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')

    assert 'complex multi-step work' in s03.SYSTEM
    assert 'Skip the todo tool for simple' in s03.SYSTEM
    assert 'Never call todo multiple times in parallel' in s03.SYSTEM
    assert 'skip it for simple one-step or purely conversational requests' in (
        s03.todo_tool.description
    )


def test_s03_todo_rejects_mismatched_json_without_fallback() -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')

    with pytest.raises(ValidationError):
        s03.todo([{}], tool_call_id='call-1')

    with pytest.raises(ValidationError):
        s03.todo(
            [{'task': 'Inspect README files', 'status': 'done'}],
            tool_call_id='call-1',
        )

    with pytest.raises(ValueError, match='tool_call_id is required'):
        s03.todo(
            [{'content': 'Inspect README files', 'status': 'pending'}],
        )


class RecordingFakeModel(FakeMessagesListChatModel):
    bound_tool_names: list[str] = []

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        del tool_choice, kwargs
        self.bound_tool_names = [getattr(tool, 'name', type(tool).__name__) for tool in tools]
        return self


def test_s03_after_model_rejects_parallel_todo_calls() -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')
    middleware = s03.PlanningMiddleware()

    state = {
        'messages': [
            AIMessage(
                content='',
                tool_calls=[
                    {
                        'name': 'todo',
                        'args': {
                            'items': [{'content': 'Inspect repo', 'status': 'in_progress'}]
                        },
                        'id': 'call_1',
                        'type': 'tool_call',
                    },
                    {
                        'name': 'todo',
                        'args': {
                            'items': [{'content': 'Summarize findings', 'status': 'pending'}]
                        },
                        'id': 'call_2',
                        'type': 'tool_call',
                    },
                ],
            )
        ]
    }

    update = middleware.after_model(state, runtime=None)

    assert update is not None
    assert len(update['messages']) == 2
    assert all(isinstance(message, ToolMessage) for message in update['messages'])
    assert all(getattr(message, 'status', None) == 'error' for message in update['messages'])
    assert 'should never be called multiple times in parallel' in update['messages'][0].content


def test_s03_middleware_tracks_stale_rounds() -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')
    middleware = s03.PlanningMiddleware()

    middleware._updated_this_turn = False
    assert middleware.after_agent(
        {
            'messages': [],
            'items': [{'content': 'Keep going', 'status': 'pending'}],
            'rounds_since_update': 2,
        },
        runtime=None,
    ) == {'rounds_since_update': 3}

    middleware._updated_this_turn = True
    assert middleware.after_agent(
        {
            'messages': [],
            'items': [{'content': 'Keep going', 'status': 'pending'}],
            'rounds_since_update': 0,
        },
        runtime=None,
    ) is None


def test_s03_agent_loop_roundtrips_runtime_state(monkeypatch) -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')

    class FakeAgent:
        def __init__(self) -> None:
            self.payloads = []

        def invoke(self, payload):
            self.payloads.append(payload)
            return {
                'messages': [*payload['messages'], {'role': 'assistant', 'content': 'planned'}],
                'items': [{'content': 'Ship it', 'status': 'in_progress', 'activeForm': 'Shipping'}],
                'rounds_since_update': 0,
            }

    fake = FakeAgent()
    monkeypatch.setattr(s03, 'build_agent', lambda: fake)
    monkeypatch.setattr(
        s03,
        'SESSION_STATE',
        {
            'items': [{'content': 'Inspect', 'status': 'completed'}],
            'rounds_since_update': 2,
        },
    )

    history = [{'role': 'user', 'content': 'continue'}]
    assert s03.agent_loop(history) == 'planned'
    assert fake.payloads[0]['rounds_since_update'] == 2
    assert fake.payloads[0]['items'] == [
        {'content': 'Inspect', 'status': 'completed'}
    ]
    assert history[-1] == {'role': 'assistant', 'content': 'planned'}
    assert s03.SESSION_STATE['items'] == [
        {'content': 'Ship it', 'status': 'in_progress', 'activeForm': 'Shipping'}
    ]


def test_s03_free_agent_path_executes_todo_without_runtime_injection_error(monkeypatch) -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')

    model = RecordingFakeModel(
        responses=[
            AIMessage(
                content='',
                tool_calls=[
                    {
                        'name': 'todo',
                        'args': {
                            'items': [
                                {
                                    'content': 'Inspect repo',
                                    'status': 'in_progress',
                                    'activeForm': 'Inspecting',
                                },
                                {'content': 'Summarize findings', 'status': 'pending'},
                            ]
                        },
                        'id': 'call_1',
                        'type': 'tool_call',
                    }
                ],
            ),
            AIMessage(content='planned'),
        ]
    )

    monkeypatch.setattr(s03, 'build_openai_model', lambda: model)
    monkeypatch.setattr(
        s03,
        'SESSION_STATE',
        {
            'items': [],
            'rounds_since_update': 0,
        },
    )

    history = [{'role': 'user', 'content': 'plan this work'}]
    assert s03.agent_loop(history) == 'planned'
    assert 'todo' in model.bound_tool_names
    assert s03.SESSION_STATE['items'] == [
        {'content': 'Inspect repo', 'status': 'in_progress', 'activeForm': 'Inspecting'},
        {'content': 'Summarize findings', 'status': 'pending'},
    ]
    assert s03.current_plan_text() == (
        '[>] Inspect repo (Inspecting)\n'
        '[ ] Summarize findings\n'
        '\n'
        '(0/2 completed)'
    )


def test_s03_current_plan_text_renders_session_state(monkeypatch) -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')
    monkeypatch.setattr(
        s03,
        'SESSION_STATE',
        {
            'items': [{'content': 'Ship it', 'status': 'in_progress'}],
            'rounds_since_update': 0,
        },
    )

    assert s03.current_plan_text() == '[>] Ship it\n\n(0/1 completed)'


def test_s03_terminal_plan_renderer_golden_output() -> None:
    s03 = importlib.import_module('agents_deepagents.s03_todo_write')

    items = [
        {'content': 'Inspect repo', 'status': 'completed'},
        {
            'content': 'Implement renderer seam',
            'status': 'in_progress',
            'activeForm': 'Implementing',
        },
        {'content': 'Verify behavior', 'status': 'pending'},
    ]

    assert s03.render_plan_items(items) == (
        '[x] Inspect repo\n'
        '[>] Implement renderer seam (Implementing)\n'
        '[ ] Verify behavior\n'
        '\n'
        '(1/3 completed)'
    )
    assert s03.render_plan_items([]) == 'No session plan yet.'
    assert s03.reminder_text([], 99) is None
    assert s03.reminder_text(items, 2) is None
    assert s03.reminder_text(items, 3) == (
        '<reminder>Refresh your current plan before continuing.</reminder>'
    )
