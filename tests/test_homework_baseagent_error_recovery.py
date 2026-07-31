import runpy
import sys
import types
from pathlib import Path

import pytest


BASE_AGENT = (
    Path(__file__).resolve().parents[1]
    / "homework"
    / "BaseAgent.py"
)


@pytest.fixture
def baseagent(monkeypatch):
    """Load BaseAgent without creating a real Anthropic client."""
    fake_anthropic = types.ModuleType("anthropic")
    fake_dotenv = types.ModuleType("dotenv")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(
                create=None,
                stream=None,
            )

    fake_anthropic.Anthropic = FakeAnthropic
    fake_dotenv.load_dotenv = lambda override=True: None

    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)
    monkeypatch.setenv("MODEL_ID", "primary-model")
    monkeypatch.setenv("FALLBACK_MODEL_ID", "fallback-model")

    namespace = runpy.run_path(
        str(BASE_AGENT),
        run_name="not_main",
    )
    return namespace["agent_loop"].__globals__


class FakeAPIError(Exception):
    def __init__(
        self,
        status_code,
        message,
        retry_after=None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = types.SimpleNamespace(
            status_code=status_code,
            headers=(
                {"retry-after": str(retry_after)}
                if retry_after is not None
                else {}
            ),
        )


def fake_response(stop_reason="end_turn", text="done"):
    return types.SimpleNamespace(
        stop_reason=stop_reason,
        content=[
            types.SimpleNamespace(
                type="text",
                text=text,
            )
        ],
    )


def disable_real_waiting(baseagent, monkeypatch):
    monkeypatch.setattr(
        baseagent["time"],
        "sleep",
        lambda _delay: None,
    )
    monkeypatch.setattr(
        baseagent["random"],
        "uniform",
        lambda _start, _end: 0,
    )


def isolate_agent_loop(baseagent, monkeypatch):
    """Replace unrelated s01-s10 systems with deterministic no-ops."""
    def fake_update_context(context, messages, tools=None):
        return context

    monkeypatch.setitem(
        baseagent,
        "tool_result_budget",
        lambda messages: messages,
    )
    monkeypatch.setitem(
        baseagent,
        "snip_compact",
        lambda messages: messages,
    )
    monkeypatch.setitem(
        baseagent,
        "micro_compact",
        lambda messages: messages,
    )
    monkeypatch.setitem(
        baseagent,
        "estimate_size",
        lambda messages: 0,
    )
    monkeypatch.setitem(
        baseagent,
        "update_context",
        fake_update_context,
    )
    monkeypatch.setitem(
        baseagent,
        "get_system_prompt",
        lambda context: "test-system",
    )
    monkeypatch.setitem(
        baseagent,
        "build_request_messages_with_memories",
        lambda messages: list(messages),
    )
    monkeypatch.setitem(
        baseagent,
        "trigger_hook",
        lambda *args: None,
    )
    monkeypatch.setitem(
        baseagent,
        "extract_memories",
        lambda messages: None,
    )
    monkeypatch.setitem(
        baseagent,
        "consolidate_memories",
        lambda: None,
    )
    monkeypatch.setitem(baseagent, "rounds_since_todo", 0)
    disable_real_waiting(baseagent, monkeypatch)


def assistant_texts(messages):
    texts = []
    for message in messages:
        if message.get("role") != "assistant":
            continue

        content = message.get("content")
        if isinstance(content, str):
            texts.append(content)
            continue

        if not isinstance(content, list):
            continue

        for block in content:
            text = getattr(block, "text", None)
            if text:
                texts.append(text)
            elif isinstance(block, dict) and block.get("type") == "text":
                texts.append(str(block.get("text", "")))
    return texts


def test_retry_delay_grows_exponentially_and_caps_at_32_seconds(
    baseagent,
    monkeypatch,
):
    monkeypatch.setattr(
        baseagent["random"],
        "uniform",
        lambda _start, _end: 0,
    )

    assert baseagent["retry_delay"](0) == 0.5
    assert baseagent["retry_delay"](1) == 1.0
    assert baseagent["retry_delay"](2) == 2.0
    assert baseagent["retry_delay"](20) == 32.0


def test_retry_delay_prefers_retry_after(baseagent):
    assert baseagent["retry_delay"](10, retry_after=7) == 7


def test_429_retries_twice_then_returns_success(
    baseagent,
    monkeypatch,
):
    disable_real_waiting(baseagent, monkeypatch)
    attempts = 0

    def call():
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise FakeAPIError(429, "rate limit")
        return fake_response()

    result = baseagent["with_retry"](
        call,
        baseagent["RecoveryState"](),
    )

    assert result.stop_reason == "end_turn"
    assert attempts == 3


def test_429_uses_retry_after_header(baseagent, monkeypatch):
    sleeps = []
    attempts = 0

    monkeypatch.setattr(
        baseagent["time"],
        "sleep",
        sleeps.append,
    )
    monkeypatch.setattr(
        baseagent["random"],
        "uniform",
        lambda _start, _end: 0,
    )

    def call():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise FakeAPIError(
                429,
                "rate limit",
                retry_after=6,
            )
        return fake_response()

    baseagent["with_retry"](
        call,
        baseagent["RecoveryState"](),
    )

    assert sleeps == [6.0]


def test_transient_retry_count_is_bounded(
    baseagent,
    monkeypatch,
):
    disable_real_waiting(baseagent, monkeypatch)
    monkeypatch.setitem(baseagent, "MAX_TRANSIENT_RETRIES", 3)
    attempts = 0

    def call():
        nonlocal attempts
        attempts += 1
        raise FakeAPIError(429, "rate limit")

    with pytest.raises(FakeAPIError):
        baseagent["with_retry"](
            call,
            baseagent["RecoveryState"](),
        )

    assert attempts == 3


def test_529_switches_model_before_the_next_real_request(
    baseagent,
    monkeypatch,
):
    disable_real_waiting(baseagent, monkeypatch)
    state = baseagent["RecoveryState"]()
    requested_models = []

    def call():
        requested_models.append(state.current_model)
        if len(requested_models) <= 3:
            raise FakeAPIError(529, "overloaded")
        return fake_response()

    result = baseagent["with_retry"](call, state)

    assert result.stop_reason == "end_turn"
    assert requested_models == [
        "primary-model",
        "primary-model",
        "primary-model",
        "fallback-model",
    ]
    assert state.consecutive_529 == 0


def test_non_transient_error_is_not_retried(
    baseagent,
    monkeypatch,
):
    disable_real_waiting(baseagent, monkeypatch)
    attempts = 0

    def call():
        nonlocal attempts
        attempts += 1
        raise ValueError("invalid request")

    with pytest.raises(ValueError):
        baseagent["with_retry"](
            call,
            baseagent["RecoveryState"](),
        )

    assert attempts == 1


@pytest.mark.parametrize(
    "message",
    [
        "prompt_is_too_long",
        "context_length_exceeded",
        "max_context_window exceeded",
        "prompt is too long for this model",
    ],
)
def test_prompt_too_long_recognizes_specific_markers(
    baseagent,
    message,
):
    assert baseagent["is_prompt_too_long_error"](
        ValueError(message)
    )


def test_prompt_too_long_does_not_match_unrelated_token_error(
    baseagent,
):
    assert not baseagent["is_prompt_too_long_error"](
        ValueError("invalid billing token")
    )


def test_prompt_too_long_compacts_once_and_rebuilds_request(
    baseagent,
    monkeypatch,
):
    isolate_agent_loop(baseagent, monkeypatch)
    stream_calls = 0
    compact_calls = 0
    request_builds = []

    def fake_streaming(**kwargs):
        nonlocal stream_calls
        stream_calls += 1
        raise FakeAPIError(
            400,
            "prompt_is_too_long",
        )

    def fake_compact(messages):
        nonlocal compact_calls
        compact_calls += 1
        return [{
            "role": "user",
            "content": "[Reactive compact] summary",
        }]

    def build_request(messages):
        request_builds.append(list(messages))
        return list(messages)

    monkeypatch.setitem(
        baseagent,
        "create_message_streaming",
        fake_streaming,
    )
    monkeypatch.setitem(
        baseagent,
        "reactive_compact",
        fake_compact,
    )
    monkeypatch.setitem(
        baseagent,
        "build_request_messages_with_memories",
        build_request,
    )

    messages = [{"role": "user", "content": "large prompt"}]
    baseagent["agent_loop"](messages, {})

    assert compact_calls == 1
    assert stream_calls == 2
    assert len(request_builds) == 2
    assert request_builds[0][0]["content"] == "large prompt"
    assert request_builds[1][0]["content"].startswith(
        "[Reactive compact]"
    )
    assert messages[-1]["role"] == "assistant"
    assert assistant_texts(messages)[-1].startswith("[Error]")


def test_first_max_tokens_is_saved_then_continues_at_64k(
    baseagent,
    monkeypatch,
):
    isolate_agent_loop(baseagent, monkeypatch)
    responses = iter([
        fake_response("max_tokens", "first-part"),
        fake_response("end_turn", "final-part"),
    ])
    max_tokens_seen = []

    def fake_streaming(**kwargs):
        max_tokens_seen.append(kwargs["max_tokens"])
        return next(responses)

    monkeypatch.setitem(baseagent, "create_message_streaming", fake_streaming)
    messages = [{"role": "user", "content": "test"}]
    baseagent["agent_loop"](messages, {})

    assert max_tokens_seen == [8_000, 64_000]
    assert [message["role"] for message in messages] == [
        "user", "assistant", "user", "assistant",
    ]
    assert messages[2]["content"] == baseagent["CONTINUATION_PROMPT"]
    assert assistant_texts(messages) == ["first-part", "final-part"]


def test_max_tokens_tool_uses_get_error_results_before_continuation(
    baseagent,
    monkeypatch,
):
    isolate_agent_loop(baseagent, monkeypatch)
    tool_calls = [
        types.SimpleNamespace(
            type="tool_use",
            id="tool-truncated-1",
            name="bash",
            input={"command": "first"},
        ),
        types.SimpleNamespace(
            type="tool_use",
            id="tool-truncated-2",
            name="bash",
            input={"command": "second"},
        ),
    ]
    responses = iter([
        types.SimpleNamespace(
            stop_reason="max_tokens",
            content=[
                types.SimpleNamespace(type="text", text="partial"),
                *tool_calls,
            ],
        ),
        fake_response("end_turn", "resumed"),
    ])
    executed_commands = []

    def record_execution(command):
        executed_commands.append(command)

    monkeypatch.setitem(
        baseagent,
        "create_message_streaming",
        lambda **kwargs: next(responses),
    )
    monkeypatch.setitem(
        baseagent["BUILTIN_HANDLERS"],
        "bash",
        record_execution,
    )

    messages = [{"role": "user", "content": "test"}]
    baseagent["agent_loop"](messages, {})

    assert executed_commands == []
    assert messages[2]["role"] == "user"
    recovery_blocks = messages[2]["content"]
    assert isinstance(recovery_blocks, list)
    assert [block["type"] for block in recovery_blocks] == [
        "tool_result",
        "tool_result",
        "text",
    ]
    assert [
        block["tool_use_id"] for block in recovery_blocks[:-1]
    ] == ["tool-truncated-1", "tool-truncated-2"]
    assert all(block["is_error"] is True for block in recovery_blocks[:-1])
    assert all(block["content"] for block in recovery_blocks[:-1])
    assert recovery_blocks[-1] == {
        "type": "text",
        "text": baseagent["CONTINUATION_PROMPT"],
    }


def test_max_tokens_tool_uses_are_paired_when_continuations_are_exhausted(
    baseagent,
    monkeypatch,
):
    isolate_agent_loop(baseagent, monkeypatch)
    monkeypatch.setitem(baseagent, "MAX_CONTINUATIONS", 0)
    tool_calls = [
        types.SimpleNamespace(
            type="tool_use",
            id="tool-at-limit-1",
            name="bash",
            input={"command": "first"},
        ),
        types.SimpleNamespace(
            type="tool_use",
            id="tool-at-limit-2",
            name="bash",
            input={"command": "second"},
        ),
    ]
    llm_calls = []
    executed_commands = []

    def fake_streaming(**kwargs):
        llm_calls.append(kwargs["max_tokens"])
        if len(llm_calls) > 1:
            raise AssertionError("agent_loop made an unexpected continuation")
        return types.SimpleNamespace(
            stop_reason="max_tokens",
            content=[
                types.SimpleNamespace(type="text", text="partial"),
                *tool_calls,
            ],
        )

    def record_execution(command):
        executed_commands.append(command)

    monkeypatch.setitem(baseagent, "create_message_streaming", fake_streaming)
    monkeypatch.setitem(
        baseagent["BUILTIN_HANDLERS"],
        "bash",
        record_execution,
    )

    messages = [{"role": "user", "content": "test"}]
    baseagent["agent_loop"](messages, {})

    assert llm_calls == [8_000]
    assert executed_commands == []
    assert [message["role"] for message in messages] == [
        "user", "assistant", "user",
    ]
    recovery_blocks = messages[2]["content"]
    assert [block["type"] for block in recovery_blocks] == [
        "tool_result", "tool_result",
    ]
    assert [block["tool_use_id"] for block in recovery_blocks] == [
        "tool-at-limit-1", "tool-at-limit-2",
    ]
    assert all(block["is_error"] is True for block in recovery_blocks)
    assert all(block["content"] for block in recovery_blocks)


def test_continuation_is_limited_and_preserves_every_partial_response(
    baseagent,
    monkeypatch,
):
    isolate_agent_loop(baseagent, monkeypatch)
    responses = iter([
        fake_response("max_tokens", "part-0"),
        fake_response("max_tokens", "part-1"),
        fake_response("max_tokens", "part-2"),
        fake_response("max_tokens", "part-3"),
    ])
    max_tokens_seen = []

    def fake_streaming(**kwargs):
        max_tokens_seen.append(kwargs["max_tokens"])
        return next(responses)

    monkeypatch.setitem(baseagent, "create_message_streaming", fake_streaming)
    messages = [{"role": "user", "content": "test"}]
    baseagent["agent_loop"](messages, {})

    assert max_tokens_seen == [8_000, 64_000, 64_000, 64_000]
    assert [message["role"] for message in messages] == [
        "user", "assistant", "user", "assistant",
        "user", "assistant", "user", "assistant",
    ]
    assert assistant_texts(messages) == [
        "part-0",
        "part-1",
        "part-2",
        "part-3",
    ]
    assert sum(
        message.get("content") == baseagent["CONTINUATION_PROMPT"]
        for message in messages
    ) == 3


def test_mixed_recoveries_share_continuation_budget_without_fifth_call(
    baseagent,
    monkeypatch,
):
    isolate_agent_loop(baseagent, monkeypatch)
    events = [
        fake_response("max_tokens", "max-part-0"),
        baseagent["PartialStreamError"](
            "stream-part-1",
            RuntimeError("connection lost 1"),
        ),
        fake_response("max_tokens", "max-part-2"),
        baseagent["PartialStreamError"](
            "stream-part-3",
            RuntimeError("connection lost 3"),
        ),
    ]
    max_tokens_seen = []

    def fake_streaming(**kwargs):
        max_tokens_seen.append(kwargs["max_tokens"])
        if len(max_tokens_seen) > len(events):
            raise AssertionError("agent_loop made an unexpected fifth call")
        event = events[len(max_tokens_seen) - 1]
        if isinstance(event, Exception):
            raise event
        return event

    monkeypatch.setitem(baseagent, "create_message_streaming", fake_streaming)
    messages = [{"role": "user", "content": "test"}]
    baseagent["agent_loop"](messages, {})

    assert max_tokens_seen == [8_000, 64_000, 64_000, 64_000]
    assert sum(
        message.get("content") == baseagent["CONTINUATION_PROMPT"]
        for message in messages
    ) == 3
    assert assistant_texts(messages) == [
        "max-part-0",
        "stream-part-1",
        "max-part-2",
        "stream-part-3\n"
        "[Stream interrupted: RuntimeError: connection lost 3]",
    ]


def test_agent_loop_does_not_print_streamed_response_twice(
    baseagent,
    monkeypatch,
    capsys,
):
    isolate_agent_loop(baseagent, monkeypatch)

    def fake_streaming(**kwargs):
        print("unique-final-answer", end="", flush=True)
        return fake_response("end_turn", "unique-final-answer")

    monkeypatch.setitem(baseagent, "create_message_streaming", fake_streaming)
    messages = [{"role": "user", "content": "test"}]
    baseagent["agent_loop"](messages, {})

    output = capsys.readouterr().out
    assert output.count("unique-final-answer") == 1
    assert assistant_texts(messages).count("unique-final-answer") == 1


def test_partial_stream_error_is_saved_then_continued_without_replay(
    baseagent,
    monkeypatch,
):
    isolate_agent_loop(baseagent, monkeypatch)
    calls = []

    def fake_streaming(**kwargs):
        calls.append(kwargs["max_tokens"])
        if len(calls) == 1:
            raise baseagent["PartialStreamError"](
                "visible-part",
                RuntimeError("connection lost"),
            )
        return fake_response("end_turn", "resumed-part")

    monkeypatch.setitem(baseagent, "create_message_streaming", fake_streaming)
    messages = [{"role": "user", "content": "test"}]
    baseagent["agent_loop"](messages, {})

    assert calls == [8_000, 64_000]
    assert [message["role"] for message in messages] == [
        "user", "assistant", "user", "assistant",
    ]
    assert messages[2]["content"] == baseagent["CONTINUATION_PROMPT"]
    assert assistant_texts(messages) == ["visible-part", "resumed-part"]


def test_real_stream_partial_failure_continues_through_agent_loop_once(
    baseagent,
    monkeypatch,
    capsys,
):
    isolate_agent_loop(baseagent, monkeypatch)
    cause = FakeAPIError(529, "stream overloaded")
    stream_calls = []

    class PartialFailureStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        @property
        def text_stream(self):
            def chunks():
                yield "visible-"
                yield "part"
                raise cause
            return chunks()

        def get_final_message(self):
            raise AssertionError("failed stream has no final message")

    class SuccessfulStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        @property
        def text_stream(self):
            return iter(["resumed-part"])

        def get_final_message(self):
            return fake_response("end_turn", "resumed-part")

    streams = iter([PartialFailureStream(), SuccessfulStream()])

    def fake_sdk_stream(**kwargs):
        stream_calls.append(kwargs)
        return next(streams)

    baseagent["client"].messages.stream = fake_sdk_stream
    messages = [{"role": "user", "content": "test"}]
    baseagent["agent_loop"](messages, {})

    assert [call["max_tokens"] for call in stream_calls] == [8_000, 64_000]
    assert stream_calls[1]["messages"][1] == {
        "role": "assistant",
        "content": [{"type": "text", "text": "visible-part"}],
    }
    assert stream_calls[1]["messages"][2] == {
        "role": "user",
        "content": baseagent["CONTINUATION_PROMPT"],
    }
    assert assistant_texts(messages) == ["visible-part", "resumed-part"]
    assert assistant_texts(messages).count("visible-part") == 1
    output = capsys.readouterr().out
    assert output.count("visible-part") == 1
    assert output.count("resumed-part") == 1


def test_partial_stream_error_at_limit_stores_visible_marker(
    baseagent,
    monkeypatch,
    capsys,
):
    isolate_agent_loop(baseagent, monkeypatch)
    monkeypatch.setitem(baseagent, "MAX_CONTINUATIONS", 0)

    def fake_streaming(**kwargs):
        print("visible-part")
        raise baseagent["PartialStreamError"](
            "visible-part",
            RuntimeError("connection lost"),
        )

    monkeypatch.setitem(baseagent, "create_message_streaming", fake_streaming)
    messages = [{"role": "user", "content": "test"}]
    baseagent["agent_loop"](messages, {})

    marker = "[Stream interrupted: RuntimeError: connection lost]"
    assert capsys.readouterr().out.count(marker) == 1
    assert assistant_texts(messages) == [f"visible-part\n{marker}"]


def test_streamed_tool_use_keeps_adjacent_tool_result(
    baseagent,
    monkeypatch,
):
    isolate_agent_loop(baseagent, monkeypatch)
    tool_call = types.SimpleNamespace(
        type="tool_use",
        id="tool-stream-1",
        name="bash",
        input={"command": "pwd"},
    )
    responses = iter([
        types.SimpleNamespace(
            stop_reason="tool_use",
            content=[
                types.SimpleNamespace(type="text", text="Checking."),
                tool_call,
            ],
        ),
        fake_response("end_turn", "Done."),
    ])

    monkeypatch.setitem(
        baseagent,
        "create_message_streaming",
        lambda **kwargs: next(responses),
    )
    monkeypatch.setitem(
        baseagent["BUILTIN_HANDLERS"],
        "bash",
        lambda command: "/workspace",
    )

    messages = [{"role": "user", "content": "where am I?"}]
    baseagent["agent_loop"](messages, {})

    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == [{
        "type": "tool_result",
        "tool_use_id": "tool-stream-1",
        "content": "/workspace",
    }]


def test_streaming_prints_chunks_before_returning_final_message(
    baseagent,
    capsys,
):
    captured = {}
    events = []
    observed_before_final = []
    final_response = fake_response("end_turn", "live-answer")

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        @property
        def text_stream(self):
            def chunks():
                events.append("chunk-1")
                yield "live-"
                events.append("chunk-2")
                yield "answer"
            return chunks()

        def get_final_message(self):
            events.append("final")
            observed_before_final.append(capsys.readouterr().out)
            return final_response

    def fake_stream(**kwargs):
        captured.update(kwargs)
        return FakeStream()

    baseagent["client"].messages.stream = fake_stream

    result = baseagent["create_message_streaming"](
        system="system",
        request_messages=[{"role": "user", "content": "test"}],
        model="fallback-model",
        max_tokens=64_000,
        tools=baseagent["BUILTIN_TOOLS"],
    )

    assert result is final_response
    assert captured["model"] == "fallback-model"
    assert captured["max_tokens"] == 64_000
    assert events == ["chunk-1", "chunk-2", "final"]
    assert observed_before_final == ["live-answer"]
    assert capsys.readouterr().out == "\n"


def test_streaming_wraps_error_after_visible_text(baseagent, capsys):
    cause = FakeAPIError(529, "stream overloaded")

    class FailingStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        @property
        def text_stream(self):
            def chunks():
                yield "visible-part"
                raise cause
            return chunks()

        def get_final_message(self):
            raise AssertionError("failed stream has no final message")

    baseagent["client"].messages.stream = lambda **kwargs: FailingStream()

    with pytest.raises(baseagent["PartialStreamError"]) as raised:
        baseagent["create_message_streaming"](
            system="system",
            request_messages=[{"role": "user", "content": "test"}],
            model="primary-model",
            max_tokens=8_000,
            tools=baseagent["BUILTIN_TOOLS"],
        )

    assert raised.value.partial_text == "visible-part"
    assert raised.value.cause is cause
    assert capsys.readouterr().out == "visible-part\n"


def test_streaming_reraises_original_error_before_first_chunk(baseagent):
    cause = FakeAPIError(429, "rate limit before output")

    class FailingStream:
        def __enter__(self):
            raise cause

        def __exit__(self, exc_type, exc, traceback):
            return False

    baseagent["client"].messages.stream = lambda **kwargs: FailingStream()

    with pytest.raises(FakeAPIError) as raised:
        baseagent["create_message_streaming"](
            system="system",
            request_messages=[{"role": "user", "content": "test"}],
            model="primary-model",
            max_tokens=8_000,
            tools=baseagent["BUILTIN_TOOLS"],
        )

    assert raised.value is cause


def test_with_retry_never_replays_partial_stream_error(baseagent):
    attempts = 0
    error = baseagent["PartialStreamError"](
        "already visible",
        FakeAPIError(529, "stream overloaded"),
    )

    def call():
        nonlocal attempts
        attempts += 1
        raise error

    with pytest.raises(baseagent["PartialStreamError"]) as raised:
        baseagent["with_retry"](call, baseagent["RecoveryState"]())

    assert raised.value is error
    assert attempts == 1


def test_subagent_routes_llm_request_through_with_retry(
    baseagent,
    monkeypatch,
):
    retry_calls = []
    requested_models = []

    def fake_create(**kwargs):
        requested_models.append(kwargs["model"])
        return fake_response("end_turn", "subagent done")

    def spy_with_retry(call, state):
        retry_calls.append(state)
        return call()

    baseagent["client"].messages.create = fake_create
    monkeypatch.setitem(
        baseagent,
        "with_retry",
        spy_with_retry,
    )

    result = baseagent["spawn_subagent"]("review one file")

    assert result == "subagent done"
    assert len(retry_calls) == 1
    assert requested_models == ["primary-model"]
