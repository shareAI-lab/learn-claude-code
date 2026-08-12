import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from homework.agent_app.core import recovery


BASE_AGENT = (
    REPO_ROOT
    / "homework"
    / "BaseAgent.py"
)


class BaseAgentModule:
    def __init__(self, module):
        object.__setattr__(self, "module", module)

    def __getitem__(self, name):
        return getattr(self.module, name)

    def __getattr__(self, name):
        return getattr(self.module, name)

    def __contains__(self, name):
        return hasattr(self.module, name)

    def __iter__(self):
        return iter(vars(self.module))

    def __setattr__(self, name, value):
        setattr(self.module, name, value)

    def __delattr__(self, name):
        delattr(self.module, name)


def load_baseagent_module():
    spec = importlib.util.spec_from_file_location("_baseagent_error_recovery", BASE_AGENT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return BaseAgentModule(module)


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

    return load_baseagent_module()


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


def test_retry_delay_grows_exponentially_and_caps_at_32_seconds(monkeypatch):
    monkeypatch.setattr(
        recovery.random,
        "uniform",
        lambda _start, _end: 0,
    )

    assert recovery.retry_delay(0, base_delay_ms=500) == 0.5
    assert recovery.retry_delay(1, base_delay_ms=500) == 1.0
    assert recovery.retry_delay(2, base_delay_ms=500) == 2.0
    assert recovery.retry_delay(20, base_delay_ms=500) == 32.0


def test_retry_delay_prefers_retry_after():
    assert recovery.retry_delay(10, retry_after=7) == 7


def test_429_retries_twice_then_returns_success(
    monkeypatch,
):
    monkeypatch.setattr(recovery.time, "sleep", lambda _delay: None)
    attempts = 0

    def call():
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise FakeAPIError(429, "rate limit")
        return fake_response()

    result = recovery.with_retry(
        call,
        recovery.RecoveryState("primary-model", "fallback-model"),
    )

    assert result.stop_reason == "end_turn"
    assert attempts == 3


def test_429_uses_retry_after_header(monkeypatch):
    sleeps = []
    attempts = 0

    monkeypatch.setattr(
        recovery.time,
        "sleep",
        sleeps.append,
    )
    monkeypatch.setattr(
        recovery.random,
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

    recovery.with_retry(
        call,
        recovery.RecoveryState("primary-model", "fallback-model"),
    )

    assert sleeps == [6.0]


def test_transient_retry_count_is_bounded(
    monkeypatch,
):
    monkeypatch.setattr(recovery.time, "sleep", lambda _delay: None)
    attempts = 0

    def call():
        nonlocal attempts
        attempts += 1
        raise FakeAPIError(429, "rate limit")

    with pytest.raises(FakeAPIError):
        recovery.with_retry(
            call,
            recovery.RecoveryState("primary-model", "fallback-model"),
            max_transient_retries=3,
        )

    assert attempts == 3


def test_529_switches_model_before_the_next_real_request(
    monkeypatch,
):
    monkeypatch.setattr(recovery.time, "sleep", lambda _delay: None)
    state = recovery.RecoveryState("primary-model", "fallback-model")
    requested_models = []

    def call():
        requested_models.append(state.current_model)
        if len(requested_models) <= 3:
            raise FakeAPIError(529, "overloaded")
        return fake_response()

    result = recovery.with_retry(call, state)

    assert result.stop_reason == "end_turn"
    assert requested_models == [
        "primary-model",
        "primary-model",
        "primary-model",
        "fallback-model",
    ]
    assert state.consecutive_529 == 0


def test_non_transient_error_is_not_retried(
    monkeypatch,
):
    monkeypatch.setattr(recovery.time, "sleep", lambda _delay: None)
    attempts = 0

    def call():
        nonlocal attempts
        attempts += 1
        raise ValueError("invalid request")

    with pytest.raises(ValueError):
        recovery.with_retry(
            call,
            recovery.RecoveryState("primary-model", "fallback-model"),
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
    message,
):
    assert recovery.is_prompt_too_long_error(
        ValueError(message)
    )


def test_prompt_too_long_does_not_match_unrelated_token_error():
    assert not recovery.is_prompt_too_long_error(
        ValueError("invalid billing token")
    )


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


def test_with_retry_never_replays_partial_stream_error():
    attempts = 0
    error = recovery.PartialStreamError(
        "already visible",
        FakeAPIError(529, "stream overloaded"),
    )

    def call():
        nonlocal attempts
        attempts += 1
        raise error

    with pytest.raises(recovery.PartialStreamError) as raised:
        recovery.with_retry(
            call,
            recovery.RecoveryState("primary-model", "fallback-model"),
        )

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

    def spy_with_retry(call, state, **kwargs):
        retry_calls.append((state, kwargs))
        return call()

    baseagent["client"].messages.create = fake_create
    monkeypatch.setattr(baseagent, "with_retry", spy_with_retry)

    result = baseagent["spawn_subagent"]("review one file")

    assert result == "subagent done"
    assert len(retry_calls) == 1
    assert retry_calls[0][1] == {
        "max_transient_retries": baseagent["MAX_TRANSIENT_RETRIES"],
        "max_consecutive_529": baseagent["MAX_CONSECUTIVE_529"],
        "base_delay_ms": baseagent["BASE_DELAY_MS"],
    }
    assert requested_models == ["primary-model"]
