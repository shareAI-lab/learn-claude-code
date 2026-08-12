from types import SimpleNamespace

import pytest

from homework.agent_app.adapters.anthropic import AnthropicAdapter
from homework.agent_app.core.recovery import PartialStreamError


def test_adapter_forwards_non_streaming_request_body():
    final_message = object()
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return final_message

    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    adapter = AnthropicAdapter(client)

    result = adapter.create(
        system="system",
        messages=[{"role": "user", "content": "hello"}],
        model="model",
        max_tokens=100,
        tools=[{"name": "echo"}],
    )

    assert result is final_message
    assert captured == {
        "model": "model",
        "system": "system",
        "messages": [{"role": "user", "content": "hello"}],
        "tools": [{"name": "echo"}],
        "max_tokens": 100,
    }


def test_streaming_adapter_wraps_failure_after_visible_text(capsys):
    cause = RuntimeError("lost")

    class FailingStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        @property
        def text_stream(self):
            def chunks():
                yield "visible"
                raise cause

            return chunks()

        def get_final_message(self):
            raise AssertionError("failed stream has no final message")

    client = SimpleNamespace(
        messages=SimpleNamespace(
            stream=lambda **_kwargs: FailingStream(),
        )
    )
    adapter = AnthropicAdapter(client)

    with pytest.raises(PartialStreamError) as caught:
        adapter.create_streaming(
            system="system",
            messages=[],
            model="model",
            max_tokens=100,
            tools=[],
        )

    assert caught.value.partial_text == "visible"
    assert caught.value.cause is cause
    assert capsys.readouterr().out == "visible\n"


def test_streaming_adapter_returns_final_message_after_printing_chunks(capsys):
    final_message = object()
    captured = {}

    class SuccessfulStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        @property
        def text_stream(self):
            return iter(["visible", " text"])

        def get_final_message(self):
            return final_message

    def stream(**kwargs):
        captured.update(kwargs)
        return SuccessfulStream()

    client = SimpleNamespace(messages=SimpleNamespace(stream=stream))
    adapter = AnthropicAdapter(client)

    result = adapter.create_streaming(
        system="system",
        messages=[],
        model="model",
        max_tokens=100,
        tools=[],
    )

    assert result is final_message
    assert captured == {
        "model": "model",
        "system": "system",
        "messages": [],
        "tools": [],
        "max_tokens": 100,
    }
    assert capsys.readouterr().out == "visible text\n"
