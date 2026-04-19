from __future__ import annotations

import pytest
from pydantic import ValidationError

from coding_deepgent.frontend.protocol import (
    AssistantMessageEvent,
    ContextSnapshotEvent,
    RunBackgroundSubagentControlInput,
    SubmitPromptInput,
    parse_frontend_event,
    parse_frontend_input,
    serialize_frontend_event,
)


def test_frontend_event_serializes_as_jsonl_payload() -> None:
    payload = serialize_frontend_event(
        AssistantMessageEvent(message_id="assistant-1", text="hello")
    )

    assert payload == (
        '{"type":"assistant_message","message_id":"assistant-1","text":"hello"}'
    )
    parsed = parse_frontend_event(payload)
    assert isinstance(parsed, AssistantMessageEvent)
    assert parsed.text == "hello"


def test_frontend_input_rejects_unknown_extra_fields() -> None:
    with pytest.raises(ValidationError):
        parse_frontend_input(
            {"type": "submit_prompt", "text": "hello", "unexpected": True}
        )


def test_frontend_input_parses_submit_prompt() -> None:
    parsed = parse_frontend_input('{"type":"submit_prompt","text":"ship it"}')

    assert isinstance(parsed, SubmitPromptInput)
    assert parsed.text == "ship it"


def test_frontend_input_parses_background_subagent_control() -> None:
    parsed = parse_frontend_input(
        '{"type":"run_background_subagent","task":"inspect repo","agent_type":"general","max_turns":5}'
    )

    assert isinstance(parsed, RunBackgroundSubagentControlInput)
    assert parsed.task == "inspect repo"
    assert parsed.max_turns == 5


def test_frontend_context_snapshot_event_validates_payload() -> None:
    payload = serialize_frontend_event(
        ContextSnapshotEvent(
            projection_mode="collapse",
            history_messages=6,
            model_messages=3,
            visible_messages=2,
            hidden_messages=4,
            compact_count=1,
            collapse_count=1,
            session_memory_status="stale",
            latest_event="collapse",
        )
    )

    parsed = parse_frontend_event(payload)

    assert isinstance(parsed, ContextSnapshotEvent)
    assert parsed.projection_mode == "collapse"
    assert parsed.hidden_messages == 4
    assert parsed.session_memory_status == "stale"


def test_frontend_context_snapshot_rejects_negative_counts() -> None:
    with pytest.raises(ValidationError):
        parse_frontend_event(
            {
                "type": "context_snapshot",
                "projection_mode": "raw",
                "history_messages": -1,
                "model_messages": 0,
                "visible_messages": 0,
                "hidden_messages": 0,
                "compact_count": 0,
                "collapse_count": 0,
                "session_memory_status": "missing",
            }
        )


def test_frontend_protocol_rejects_non_object_json() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        parse_frontend_input("[]")
