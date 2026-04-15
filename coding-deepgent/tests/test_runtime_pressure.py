from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

from langchain.agents.middleware import ModelRequest
from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from coding_deepgent.compact import (
    LIVE_COMPACT_BOUNDARY_PREFIX,
    LIVE_COMPACT_RESTORATION_PREFIX,
    LIVE_COMPACT_SUMMARY_PREFIX,
    MICROCOMPACT_CLEARED_MESSAGE,
    RuntimePressureMiddleware,
    compact_live_messages_with_summary,
    estimate_message_tokens,
    is_prompt_too_long_error,
    maybe_auto_compact_messages,
    microcompact_messages,
    reactive_compact_messages,
)
from coding_deepgent.hooks import LocalHookRegistry
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext
from coding_deepgent.sessions import JsonlSessionStore, build_recovery_brief, render_recovery_brief
from coding_deepgent.tool_system import build_default_registry


class FakeSummarizer:
    def __init__(self, response: str) -> None:
        self.response = response
        self.requests: list[list[dict[str, object]]] = []

    def invoke(self, messages: list[dict[str, object]]) -> str:
        self.requests.append(messages)
        return self.response


def runtime_context(
    tmp_path: Path, *, session_store: JsonlSessionStore | None = None
) -> RuntimeContext:
    session_context = None
    if session_store is not None:
        session_context = session_store.create_session(
            workdir=tmp_path, session_id="session-1"
        )
        session_store.append_message(session_context, role="user", content="start")
    return RuntimeContext(
        session_id="session-1",
        workdir=tmp_path,
        trusted_workdirs=(),
        entrypoint="test",
        agent_name="test-agent",
        skill_dir=tmp_path / "skills",
        event_sink=InMemoryEventSink(),
        hook_registry=LocalHookRegistry(),
        session_context=session_context,
    )


def _read_call(tool_call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "read_file",
                "args": {"path": f"{tool_call_id}.txt"},
                "id": tool_call_id,
                "type": "tool_call",
            }
        ],
    )


def test_microcompact_messages_clears_older_eligible_tool_results() -> None:
    registry = build_default_registry(include_discovery=True)
    messages = [
        HumanMessage(content="inspect files"),
        _read_call("call-1"),
        ToolMessage(
            content="x" * 500,
            tool_call_id="call-1",
            artifact={"path": ".coding-deepgent/tool-results/session-1/call-1.txt"},
        ),
        _read_call("call-2"),
        ToolMessage(
            content="y" * 500,
            tool_call_id="call-2",
            artifact={"path": ".coding-deepgent/tool-results/session-1/call-2.txt"},
        ),
        _read_call("call-3"),
        ToolMessage(content="z" * 500, tool_call_id="call-3"),
        _read_call("call-4"),
        ToolMessage(content="w" * 500, tool_call_id="call-4"),
    ]

    result = microcompact_messages(
        messages,
        registry=registry,
        keep_recent_tool_results=2,
    )

    assert result[2].content == (
        f"{MICROCOMPACT_CLEARED_MESSAGE} "
        "Full output remains available at: .coding-deepgent/tool-results/session-1/call-1.txt"
    )
    assert result[4].content == (
        f"{MICROCOMPACT_CLEARED_MESSAGE} "
        "Full output remains available at: .coding-deepgent/tool-results/session-1/call-2.txt"
    )
    assert result[6].content == "z" * 500
    assert result[8].content == "w" * 500


def test_microcompact_messages_skips_ineligible_tool_results() -> None:
    registry = build_default_registry(include_discovery=True)
    messages = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "TodoWrite",
                    "args": {"todos": []},
                    "id": "todo-1",
                    "type": "tool_call",
                }
            ],
        ),
        ToolMessage(content="x" * 500, tool_call_id="todo-1"),
    ]

    result = microcompact_messages(messages, registry=registry, keep_recent_tool_results=0)

    assert result[1].content == "x" * 500


def test_runtime_pressure_middleware_rewrites_request_messages_before_model_call() -> None:
    registry = build_default_registry(include_discovery=True)
    middleware = RuntimePressureMiddleware(registry=registry, keep_recent_tool_results=1)
    captured: dict[str, object] = {}

    def handler(request: ModelRequest):
        captured["messages"] = request.messages
        return SimpleNamespace(result="ok")

    request = ModelRequest(
        model=SimpleNamespace(),
        messages=[
            HumanMessage(content="inspect files"),
            _read_call("call-1"),
            ToolMessage(content="x" * 500, tool_call_id="call-1"),
            _read_call("call-2"),
            ToolMessage(content="y" * 500, tool_call_id="call-2"),
        ],
        system_message=SystemMessage(content="Base"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"messages": []},
        runtime=SimpleNamespace(),
        model_settings={},
    )

    middleware.wrap_model_call(request, handler)

    compacted = captured["messages"]
    assert isinstance(compacted, list)
    assert compacted[2].content == MICROCOMPACT_CLEARED_MESSAGE
    assert compacted[4].content == "y" * 500


def test_compact_live_messages_with_summary_preserves_tool_pair_in_tail() -> None:
    messages = [
        HumanMessage(content="old request"),
        _read_call("call-1"),
        ToolMessage(content="result", tool_call_id="call-1"),
    ]

    compacted = compact_live_messages_with_summary(
        messages,
        summary="Keep the recent tool exchange.",
        keep_recent_messages=1,
    )

    assert str(compacted[0].content).startswith(LIVE_COMPACT_BOUNDARY_PREFIX)
    assert str(compacted[1].content).startswith(LIVE_COMPACT_SUMMARY_PREFIX)
    assert isinstance(compacted[2], AIMessage)
    assert isinstance(compacted[3], ToolMessage)


def test_maybe_auto_compact_messages_uses_summary_when_threshold_exceeded() -> None:
    summarizer = FakeSummarizer("<summary>Generated compact summary.</summary>")
    messages = [
        HumanMessage(content="x" * 5000),
        HumanMessage(content="y" * 5000),
    ]

    compacted = maybe_auto_compact_messages(
        messages,
        summarizer=summarizer,
        threshold_tokens=10,
        keep_recent_messages=1,
    )

    assert len(summarizer.requests) == 1
    assert estimate_message_tokens(messages) > 10
    assert str(compacted[0].content).startswith(LIVE_COMPACT_BOUNDARY_PREFIX)
    assert "Generated compact summary." in str(compacted[1].content)
    assert compacted[2].content == "y" * 5000


def test_compact_live_messages_with_summary_restores_persisted_output_paths() -> None:
    messages = [
        HumanMessage(content="old request"),
        _read_call("call-1"),
        ToolMessage(
            content="preview",
            tool_call_id="call-1",
            artifact={"kind": "persisted_output", "path": ".coding-deepgent/tool-results/session-1/call-1.txt"},
        ),
        HumanMessage(content="recent request"),
    ]

    compacted = compact_live_messages_with_summary(
        messages,
        summary="Keep the continuation moving.",
        keep_recent_messages=1,
    )

    assert str(compacted[2].content).startswith(LIVE_COMPACT_RESTORATION_PREFIX)
    assert ".coding-deepgent/tool-results/session-1/call-1.txt" in str(compacted[2].content)
    assert compacted[3].content == "recent request"


def test_runtime_pressure_middleware_auto_compacts_when_threshold_is_crossed() -> None:
    registry = build_default_registry(include_discovery=True)
    summarizer = FakeSummarizer("<summary>Generated compact summary.</summary>")
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=10,
        keep_recent_messages=1,
    )
    captured: dict[str, object] = {}

    def handler(request: ModelRequest):
        captured["messages"] = request.messages
        return SimpleNamespace(result="ok")

    request = ModelRequest(
        model=summarizer,
        messages=[
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        system_message=SystemMessage(content="Base"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"messages": []},
        runtime=SimpleNamespace(context=runtime_context(Path.cwd())),
        model_settings={},
    )

    middleware.wrap_model_call(request, handler)

    compacted = captured["messages"]
    assert isinstance(compacted, list)
    assert str(compacted[0].content).startswith(LIVE_COMPACT_BOUNDARY_PREFIX)
    assert "Generated compact summary." in str(compacted[1].content)
    assert compacted[2].content == "y" * 5000


def test_runtime_pressure_middleware_refreshes_session_memory_after_auto_compact() -> None:
    registry = build_default_registry(include_discovery=True)
    summarizer = FakeSummarizer("<summary>Generated compact summary.</summary>")
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=10,
        keep_recent_messages=1,
    )
    state = {"messages": []}

    request = ModelRequest(
        model=summarizer,
        messages=[
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        system_message=SystemMessage(content="Base"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state=state,
        runtime=SimpleNamespace(context=runtime_context(Path.cwd())),
        model_settings={},
    )

    middleware.wrap_model_call(request, lambda _request: SimpleNamespace(result="ok"))

    assert state["session_memory"] == {
        "content": "Generated compact summary.",
        "source": "live_compact",
        "message_count": 2,
        "updated_at": state["session_memory"]["updated_at"],
        "token_count": 2500,
        "tool_call_count": 0,
    }


def test_runtime_pressure_middleware_emits_microcompact_and_auto_events(
    tmp_path: Path,
) -> None:
    registry = build_default_registry(include_discovery=True)
    summarizer = FakeSummarizer("<summary>Generated compact summary.</summary>")
    context = runtime_context(tmp_path)
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=10,
        keep_recent_tool_results=1,
        keep_recent_messages=1,
    )

    request = ModelRequest(
        model=summarizer,
        messages=[
            HumanMessage(content="inspect files"),
            _read_call("call-1"),
            ToolMessage(content="x" * 500, tool_call_id="call-1"),
            _read_call("call-2"),
            ToolMessage(content="y" * 500, tool_call_id="call-2"),
            _read_call("call-3"),
            ToolMessage(content="z" * 500, tool_call_id="call-3"),
            HumanMessage(content="tail"),
        ],
        system_message=SystemMessage(content="Base"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"messages": []},
        runtime=SimpleNamespace(context=context),
        model_settings={},
    )

    middleware.wrap_model_call(request, lambda _request: SimpleNamespace(result="ok"))

    events = context.event_sink.snapshot()
    assert [event.kind for event in events] == ["microcompact", "auto_compact"]
    assert events[0].metadata == {
        "source": "runtime_pressure",
        "strategy": "microcompact",
        "cleared_tool_results": 2,
    }
    assert events[1].metadata == {
        "source": "runtime_pressure",
        "strategy": "auto",
        "used_session_memory_assist": False,
        "restored_path_count": 0,
    }


def test_maybe_auto_compact_messages_passes_session_memory_assist() -> None:
    summarizer = FakeSummarizer("<summary>Generated compact summary.</summary>")
    messages = [
        HumanMessage(content="x" * 5000),
        HumanMessage(content="y" * 5000),
    ]

    maybe_auto_compact_messages(
        messages,
        summarizer=summarizer,
        threshold_tokens=10,
        keep_recent_messages=1,
        assist_context="Session memory artifact:\nKeep repo focus.",
    )

    assert len(summarizer.requests) == 1
    assert summarizer.requests[0][-2]["role"] == "system"
    assert "Keep repo focus." in str(summarizer.requests[0][-2]["content"])


def test_reactive_compact_messages_uses_summarizer_without_threshold() -> None:
    summarizer = FakeSummarizer("<summary>Reactive compact summary.</summary>")
    messages = [
        HumanMessage(content="x" * 5000),
        HumanMessage(content="y" * 5000),
    ]

    compacted = reactive_compact_messages(
        messages,
        summarizer=summarizer,
        keep_recent_messages=1,
    )

    assert len(summarizer.requests) == 1
    assert str(compacted[0].content).startswith(LIVE_COMPACT_BOUNDARY_PREFIX)
    assert "Reactive compact summary." in str(compacted[1].content)


def test_runtime_pressure_middleware_retries_once_on_prompt_too_long() -> None:
    registry = build_default_registry(include_discovery=True)
    summarizer = FakeSummarizer("<summary>Reactive compact summary.</summary>")
    context = runtime_context(Path.cwd())
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=None,
        keep_recent_messages=1,
    )
    calls: list[list[object]] = []

    def handler(request: ModelRequest):
        calls.append(list(request.messages))
        if len(calls) == 1:
            raise RuntimeError("prompt too long for current context window")
        return SimpleNamespace(result="ok")

    request = ModelRequest(
        model=summarizer,
        messages=[
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        system_message=SystemMessage(content="Base"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"messages": []},
        runtime=SimpleNamespace(context=context),
        model_settings={},
    )

    middleware.wrap_model_call(request, handler)

    assert len(calls) == 2
    assert [event.kind for event in context.event_sink.snapshot()] == ["reactive_compact"]
    assert str(calls[1][0].content).startswith(LIVE_COMPACT_BOUNDARY_PREFIX)
    assert "Reactive compact summary." in str(calls[1][1].content)


def test_is_prompt_too_long_error_matches_expected_phrases() -> None:
    assert is_prompt_too_long_error(RuntimeError("maximum context length exceeded"))
    assert not is_prompt_too_long_error(RuntimeError("permission denied"))


def test_runtime_pressure_events_append_session_evidence(tmp_path: Path) -> None:
    registry = build_default_registry(include_discovery=True)
    session_store = JsonlSessionStore(tmp_path / "sessions")
    context = runtime_context(tmp_path, session_store=session_store)
    summarizer = FakeSummarizer("<summary>Generated compact summary.</summary>")
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=10,
        keep_recent_messages=1,
    )

    request = ModelRequest(
        model=summarizer,
        messages=[
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        system_message=SystemMessage(content="Base"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={
            "messages": [],
            "session_memory": {
                "content": "Keep repo focus.",
                "source": "manual",
                "message_count": 2,
                "updated_at": "2026-04-15T00:00:00Z",
            },
        },
        runtime=SimpleNamespace(context=context),
        model_settings={},
    )

    middleware.wrap_model_call(request, lambda _request: SimpleNamespace(result="ok"))
    loaded = session_store.load_session(session_id="session-1", workdir=tmp_path)
    rendered = render_recovery_brief(build_recovery_brief(loaded))

    assert loaded.summary.evidence_count == 1
    assert loaded.evidence[0].kind == "runtime_event"
    assert loaded.evidence[0].status == "completed"
    assert loaded.evidence[0].metadata == {
        "event_kind": "auto_compact",
        "source": "runtime_pressure",
        "strategy": "auto",
        "used_session_memory_assist": True,
        "restored_path_count": 0,
    }
    assert "[completed] runtime_event: Live auto-compact summarized history." in rendered
