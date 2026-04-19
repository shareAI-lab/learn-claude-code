from __future__ import annotations

import pytest
from pydantic import ValidationError

from coding_deepgent.frontend.protocol import (
    AssistantMessageEvent,
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


def test_frontend_protocol_rejects_non_object_json() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        parse_frontend_input("[]")

