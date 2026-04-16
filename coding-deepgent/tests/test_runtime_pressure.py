from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from pathlib import Path

from langchain.agents.middleware import ModelRequest
from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from coding_deepgent.compact import (
    LIVE_COLLAPSE_BOUNDARY_PREFIX,
    LIVE_COLLAPSE_SUMMARY_PREFIX,
    LIVE_COMPACT_BOUNDARY_PREFIX,
    LIVE_COMPACT_RESTORATION_PREFIX,
    LIVE_COMPACT_SUMMARY_PREFIX,
    LIVE_SNIP_BOUNDARY_PREFIX,
    MICROCOMPACT_CLEARED_MESSAGE,
    RuntimePressureMiddleware,
    collapse_live_messages_with_result,
    collapse_live_messages_with_summary,
    compact_live_messages_with_result,
    compact_live_messages_with_summary,
    estimate_message_tokens,
    is_prompt_too_long_error,
    maybe_collapse_messages,
    maybe_auto_compact_messages,
    maybe_time_based_microcompact_messages,
    microcompact_messages,
    reactive_compact_messages,
    snip_messages,
)
from coding_deepgent.hooks import HookResult, LocalHookRegistry
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


class FailingSummarizer:
    def __init__(self) -> None:
        self.requests: list[list[dict[str, object]]] = []

    def invoke(self, messages: list[dict[str, object]]) -> str:
        self.requests.append(messages)
        raise RuntimeError("compact summarizer unavailable")


class PromptTooLongThenSuccessSummarizer:
    def __init__(self, response: str) -> None:
        self.response = response
        self.requests: list[list[dict[str, object]]] = []

    def invoke(self, messages: list[dict[str, object]]) -> str:
        self.requests.append(messages)
        if len(self.requests) == 1:
            raise RuntimeError("prompt too long for compact request")
        return self.response


class PromptTooLongSummarizer:
    def __init__(self) -> None:
        self.requests: list[list[dict[str, object]]] = []

    def invoke(self, messages: list[dict[str, object]]) -> str:
        self.requests.append(messages)
        raise RuntimeError("prompt too long for compact request")


def runtime_context(
    tmp_path: Path,
    *,
    session_store: JsonlSessionStore | None = None,
    entrypoint: str = "test",
    agent_name: str = "test-agent",
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
        entrypoint=entrypoint,
        agent_name=agent_name,
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


def _assistant_at(timestamp: str) -> AIMessage:
    return AIMessage(content="completed previous turn", additional_kwargs={"timestamp": timestamp})


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


def test_microcompact_messages_can_use_token_budget_protection() -> None:
    registry = build_default_registry(include_discovery=True)
    messages = [
        HumanMessage(content="inspect files"),
        _read_call("call-1"),
        ToolMessage(content="a" * 400, tool_call_id="call-1"),
        _read_call("call-2"),
        ToolMessage(content="b" * 160, tool_call_id="call-2"),
        _read_call("call-3"),
        ToolMessage(content="c" * 160, tool_call_id="call-3"),
        _read_call("call-4"),
        ToolMessage(content="d" * 160, tool_call_id="call-4"),
    ]

    result = microcompact_messages(
        messages,
        registry=registry,
        keep_recent_tool_results=0,
        protect_recent_tokens=100,
    )

    assert result[2].content == MICROCOMPACT_CLEARED_MESSAGE
    assert result[4].content == MICROCOMPACT_CLEARED_MESSAGE
    assert result[6].content == "c" * 160
    assert result[8].content == "d" * 160


def test_microcompact_messages_token_budget_keeps_at_least_one_result() -> None:
    registry = build_default_registry(include_discovery=True)
    messages = [
        _read_call("call-1"),
        ToolMessage(content="x" * 500, tool_call_id="call-1"),
        _read_call("call-2"),
        ToolMessage(content="y" * 500, tool_call_id="call-2"),
    ]

    result = microcompact_messages(
        messages,
        registry=registry,
        keep_recent_tool_results=0,
        protect_recent_tokens=1,
    )

    assert result[1].content == MICROCOMPACT_CLEARED_MESSAGE
    assert result[3].content == "y" * 500


def test_microcompact_messages_token_budget_respects_min_saved_tokens() -> None:
    registry = build_default_registry(include_discovery=True)
    messages = [
        _read_call("call-1"),
        ToolMessage(content="x" * 500, tool_call_id="call-1"),
        _read_call("call-2"),
        ToolMessage(content="y" * 500, tool_call_id="call-2"),
    ]

    result = microcompact_messages(
        messages,
        registry=registry,
        keep_recent_tool_results=0,
        protect_recent_tokens=1,
        min_saved_tokens=10_000,
    )

    assert result == messages


def test_time_based_microcompact_skips_when_disabled(tmp_path: Path) -> None:
    registry = build_default_registry(include_discovery=True)

    decision = maybe_time_based_microcompact_messages(
        [
            _assistant_at("2026-04-16T10:00:00Z"),
            _read_call("call-1"),
            ToolMessage(content="x" * 500, tool_call_id="call-1"),
        ],
        registry=registry,
        context=runtime_context(
            tmp_path,
            entrypoint="coding-deepgent",
            agent_name="coding-deepgent",
        ),
        gap_threshold_minutes=None,
        now=lambda: datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc),
    )

    assert decision.attempted is False
    assert decision.result is None


def test_time_based_microcompact_skips_non_main_context(tmp_path: Path) -> None:
    registry = build_default_registry(include_discovery=True)

    decision = maybe_time_based_microcompact_messages(
        [
            _assistant_at("2026-04-16T10:00:00Z"),
            _read_call("call-1"),
            ToolMessage(content="x" * 500, tool_call_id="call-1"),
        ],
        registry=registry,
        context=runtime_context(
            tmp_path,
            entrypoint="run_subagent:verifier",
            agent_name="coding-deepgent-verifier",
        ),
        gap_threshold_minutes=60,
        now=lambda: datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc),
    )

    assert decision.attempted is False
    assert decision.result is None


def test_time_based_microcompact_skips_without_assistant_timestamp(
    tmp_path: Path,
) -> None:
    registry = build_default_registry(include_discovery=True)

    decision = maybe_time_based_microcompact_messages(
        [
            _read_call("call-1"),
            ToolMessage(content="x" * 500, tool_call_id="call-1"),
        ],
        registry=registry,
        context=runtime_context(
            tmp_path,
            entrypoint="coding-deepgent",
            agent_name="coding-deepgent",
        ),
        gap_threshold_minutes=60,
        now=lambda: datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc),
    )

    assert decision.attempted is False
    assert decision.result is None


def test_time_based_microcompact_skips_under_gap_threshold(tmp_path: Path) -> None:
    registry = build_default_registry(include_discovery=True)

    decision = maybe_time_based_microcompact_messages(
        [
            _assistant_at("2026-04-16T11:30:00Z"),
            _read_call("call-1"),
            ToolMessage(content="x" * 500, tool_call_id="call-1"),
        ],
        registry=registry,
        context=runtime_context(
            tmp_path,
            entrypoint="coding-deepgent",
            agent_name="coding-deepgent",
        ),
        gap_threshold_minutes=60,
        now=lambda: datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc),
    )

    assert decision.attempted is False
    assert decision.result is None


def test_snip_messages_hides_older_projection_and_preserves_tool_pair() -> None:
    messages = [
        HumanMessage(content="old request"),
        _read_call("call-1"),
        ToolMessage(content="result", tool_call_id="call-1"),
    ]

    result = snip_messages(
        messages,
        threshold_tokens=1,
        keep_recent_messages=1,
    )

    assert str(result[0].content).startswith(LIVE_SNIP_BOUNDARY_PREFIX)
    assert "hidden_messages=1" in str(result[0].content)
    assert isinstance(result[1], AIMessage)
    assert isinstance(result[2], ToolMessage)
    assert messages[0].content == "old request"


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


def test_runtime_pressure_middleware_runs_time_based_microcompact(
    tmp_path: Path,
) -> None:
    registry = build_default_registry(include_discovery=True)
    context = runtime_context(
        tmp_path,
        entrypoint="coding-deepgent",
        agent_name="coding-deepgent",
    )
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=None,
        keep_recent_tool_results=0,
        microcompact_time_gap_minutes=60,
        main_entrypoint="coding-deepgent",
        main_agent_name="coding-deepgent",
        now=lambda: datetime(2026, 4, 16, 12, 5, tzinfo=timezone.utc),
    )
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
            _assistant_at("2026-04-16T10:00:00Z"),
            _read_call("call-2"),
            ToolMessage(content="y" * 500, tool_call_id="call-2"),
            _read_call("call-3"),
            ToolMessage(content="z" * 500, tool_call_id="call-3"),
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

    messages = captured["messages"]
    assert isinstance(messages, list)
    assert messages[2].content == MICROCOMPACT_CLEARED_MESSAGE
    assert messages[5].content == MICROCOMPACT_CLEARED_MESSAGE
    assert messages[7].content == "z" * 500
    events = context.event_sink.snapshot()
    assert [event.kind for event in events] == ["microcompact"]
    assert events[0].metadata["trigger"] == "time_gap"
    assert events[0].metadata["gap_minutes"] == 125
    assert events[0].metadata["tools_cleared"] == 2
    assert events[0].metadata["tools_kept"] == 1
    assert events[0].metadata["keep_recent"] == 1
    assert events[0].metadata["tokens_saved_estimate"] > 0


def test_runtime_pressure_middleware_runs_token_budget_microcompact(
    tmp_path: Path,
) -> None:
    registry = build_default_registry(include_discovery=True)
    context = runtime_context(tmp_path)
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=None,
        keep_recent_tool_results=0,
        microcompact_protect_recent_tokens=100,
    )

    request = ModelRequest(
        model=SimpleNamespace(),
        messages=[
            _read_call("call-1"),
            ToolMessage(content="a" * 400, tool_call_id="call-1"),
            _read_call("call-2"),
            ToolMessage(content="b" * 160, tool_call_id="call-2"),
            _read_call("call-3"),
            ToolMessage(content="c" * 160, tool_call_id="call-3"),
            _read_call("call-4"),
            ToolMessage(content="d" * 160, tool_call_id="call-4"),
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
    assert [event.kind for event in events] == ["microcompact"]
    assert events[0].metadata["tools_cleared"] == 2
    assert events[0].metadata["tools_kept"] == 2
    assert events[0].metadata["keep_recent"] == 2
    assert events[0].metadata["protected_recent_tokens"] == 100
    assert events[0].metadata["tokens_saved_estimate"] > 0


def test_time_based_microcompact_min_saved_tokens_skips_low_value_clear(
    tmp_path: Path,
) -> None:
    registry = build_default_registry(include_discovery=True)
    context = runtime_context(
        tmp_path,
        entrypoint="coding-deepgent",
        agent_name="coding-deepgent",
    )
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=None,
        keep_recent_tool_results=0,
        min_content_chars=1,
        microcompact_time_gap_minutes=60,
        microcompact_min_saved_tokens=10_000,
        main_entrypoint="coding-deepgent",
        main_agent_name="coding-deepgent",
        now=lambda: datetime(2026, 4, 16, 12, 5, tzinfo=timezone.utc),
    )
    captured: dict[str, object] = {}

    request = ModelRequest(
        model=SimpleNamespace(),
        messages=[
            _assistant_at("2026-04-16T10:00:00Z"),
            _read_call("call-1"),
            ToolMessage(content="x" * 100, tool_call_id="call-1"),
            _read_call("call-2"),
            ToolMessage(content="y" * 100, tool_call_id="call-2"),
        ],
        system_message=SystemMessage(content="Base"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state={"messages": []},
        runtime=SimpleNamespace(context=context),
        model_settings={},
    )

    def handler(active_request: ModelRequest):
        captured["messages"] = active_request.messages
        return SimpleNamespace(result="ok")

    middleware.wrap_model_call(request, handler)

    messages = captured["messages"]
    assert isinstance(messages, list)
    assert messages[2].content == "x" * 100
    assert messages[4].content == "y" * 100
    assert context.event_sink.snapshot() == ()


def test_collapse_live_messages_with_summary_preserves_tool_pair_in_tail() -> None:
    messages = [
        HumanMessage(content="old request"),
        _read_call("call-1"),
        ToolMessage(content="result", tool_call_id="call-1"),
    ]

    collapsed = collapse_live_messages_with_summary(
        messages,
        summary="Earlier work was collapsed.",
        keep_recent_messages=1,
    )

    assert str(collapsed[0].content).startswith(LIVE_COLLAPSE_BOUNDARY_PREFIX)
    assert str(collapsed[1].content).startswith(LIVE_COLLAPSE_SUMMARY_PREFIX)
    assert isinstance(collapsed[2], AIMessage)
    assert isinstance(collapsed[3], ToolMessage)


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


def test_live_compaction_result_renders_stable_order_with_metadata() -> None:
    messages = [
        HumanMessage(content="old request"),
        _read_call("call-1"),
        ToolMessage(
            content="preview",
            tool_call_id="call-1",
            artifact={
                "kind": "persisted_output",
                "path": ".coding-deepgent/tool-results/session-1/call-1.txt",
            },
        ),
        HumanMessage(content="recent request"),
    ]

    result = compact_live_messages_with_result(
        messages,
        summary="Keep the continuation moving.",
        keep_recent_messages=1,
    )
    rendered = result.render()

    assert result.trigger == "auto_compact"
    assert result.original_token_estimate > 0
    assert result.projected_token_estimate > 0
    assert result.restored_path_count == 1
    assert str(rendered[0].content).startswith(LIVE_COMPACT_BOUNDARY_PREFIX)
    assert str(rendered[1].content).startswith(LIVE_COMPACT_SUMMARY_PREFIX)
    assert str(rendered[2].content).startswith(LIVE_COMPACT_RESTORATION_PREFIX)
    assert rendered[3].content == "recent request"


def test_live_collapse_result_renders_stable_order() -> None:
    messages = [
        HumanMessage(content="old request"),
        HumanMessage(content="recent request"),
    ]

    result = collapse_live_messages_with_result(
        messages,
        summary="Earlier context collapsed.",
        keep_recent_messages=1,
    )
    rendered = result.render()

    assert result.trigger == "context_collapse"
    assert result.restored_path_count == 0
    assert str(rendered[0].content).startswith(LIVE_COLLAPSE_BOUNDARY_PREFIX)
    assert str(rendered[1].content).startswith(LIVE_COLLAPSE_SUMMARY_PREFIX)
    assert rendered[2].content == "recent request"


def test_compact_result_restores_active_todos_from_runtime_state() -> None:
    messages = [
        HumanMessage(content="old request"),
        HumanMessage(content="recent request"),
    ]

    result = compact_live_messages_with_result(
        messages,
        summary="Keep the active plan.",
        keep_recent_messages=1,
        state={
            "todos": [
                {
                    "content": "Inspect runtime pressure tests",
                    "status": "in_progress",
                    "activeForm": "Inspecting runtime pressure tests",
                },
                {
                    "content": "Run verification",
                    "status": "pending",
                    "activeForm": "Running verification",
                },
                {
                    "content": "Done item",
                    "status": "completed",
                    "activeForm": "Done",
                },
            ]
        },
    )

    rendered = result.render()
    assert str(rendered[2].content).startswith("Post-compact restored state:")
    assert "[in_progress] Inspect runtime pressure tests" in str(rendered[2].content)
    assert "[pending] Run verification" in str(rendered[2].content)
    assert "Done item" not in str(rendered[2].content)
    assert rendered[3].content == "recent request"


def test_auto_compact_uses_pre_and_post_compact_hook_context(tmp_path: Path) -> None:
    registry = build_default_registry(include_discovery=True)
    summarizer = FakeSummarizer("<summary>Hook-aware compact summary.</summary>")
    context = runtime_context(tmp_path)
    context.hook_registry.register(
        "PreCompact",
        lambda _payload: HookResult(additional_context="Preserve schema decisions."),
    )
    context.hook_registry.register(
        "PostCompact",
        lambda _payload: HookResult(additional_context="Reinforce project constraints."),
    )
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=10,
        keep_recent_messages=1,
    )
    captured: dict[str, object] = {}

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

    def handler(active_request: ModelRequest):
        captured["messages"] = active_request.messages
        return SimpleNamespace(result="ok")

    middleware.wrap_model_call(request, handler)

    assert any(
        "Preserve schema decisions." in str(item.get("content"))
        for item in summarizer.requests[0]
    )
    messages = captured["messages"]
    assert isinstance(messages, list)
    assert "PostCompact hook context:" in str(messages[2].content)
    assert "Reinforce project constraints." in str(messages[2].content)


def test_maybe_collapse_messages_uses_summary_when_threshold_exceeded() -> None:
    summarizer = FakeSummarizer("<summary>Generated collapse summary.</summary>")
    messages = [
        HumanMessage(content="x" * 5000),
        HumanMessage(content="y" * 5000),
    ]

    collapsed = maybe_collapse_messages(
        messages,
        summarizer=summarizer,
        threshold_tokens=10,
        keep_recent_messages=1,
    )

    assert len(summarizer.requests) == 1
    assert str(collapsed[0].content).startswith(LIVE_COLLAPSE_BOUNDARY_PREFIX)
    assert "Generated collapse summary." in str(collapsed[1].content)
    assert collapsed[2].content == "y" * 5000


def test_maybe_collapse_messages_fails_open_on_summarizer_error() -> None:
    def failing_summarizer(_messages):
        raise RuntimeError("collapse unavailable")

    messages = [
        HumanMessage(content="x" * 5000),
        HumanMessage(content="y" * 5000),
    ]

    collapsed = maybe_collapse_messages(
        messages,
        summarizer=failing_summarizer,
        threshold_tokens=10,
        keep_recent_messages=1,
    )

    assert collapsed == messages


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


def test_runtime_pressure_middleware_runs_snip_microcollapse_autocompact_order(
    tmp_path: Path,
) -> None:
    registry = build_default_registry(include_discovery=True)
    summarizer = FakeSummarizer("<summary>Generated pressure summary.</summary>")
    context = runtime_context(tmp_path)
    middleware = RuntimePressureMiddleware(
        registry=registry,
        snip_threshold_tokens=10,
        keep_recent_messages_after_snip=8,
        keep_recent_tool_results=1,
        collapse_threshold_tokens=10,
        keep_recent_messages_after_collapse=2,
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
            HumanMessage(content="old context " * 1000),
            HumanMessage(content="older context " * 1000),
            _read_call("call-1"),
            ToolMessage(content="x" * 500, tool_call_id="call-1"),
            _read_call("call-2"),
            ToolMessage(content="y" * 500, tool_call_id="call-2"),
            _read_call("call-3"),
            ToolMessage(content="z" * 500, tool_call_id="call-3"),
            HumanMessage(content="tail one " * 5000),
            HumanMessage(content="tail two " * 5000),
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

    assert [event.kind for event in context.event_sink.snapshot()] == [
        "snip",
        "microcompact",
        "context_collapse",
        "auto_compact",
    ]
    assert len(summarizer.requests) == 2
    messages = captured["messages"]
    assert isinstance(messages, list)
    assert str(messages[0].content).startswith(LIVE_COMPACT_BOUNDARY_PREFIX)
    assert "Generated pressure summary." in str(messages[1].content)


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


def test_auto_compact_failure_circuit_breaker_skips_after_max_failures(
    tmp_path: Path,
) -> None:
    registry = build_default_registry(include_discovery=True)
    summarizer = FailingSummarizer()
    context = runtime_context(tmp_path)
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=10,
        auto_compact_max_failures=2,
        keep_recent_messages=1,
    )
    handler_calls = 0

    def handler(_request: ModelRequest):
        nonlocal handler_calls
        handler_calls += 1
        return SimpleNamespace(result="ok")

    def request() -> ModelRequest:
        return ModelRequest(
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

    middleware.wrap_model_call(request(), handler)
    middleware.wrap_model_call(request(), handler)
    middleware.wrap_model_call(request(), handler)

    assert handler_calls == 3
    assert len(summarizer.requests) == 2
    events = context.event_sink.snapshot()
    assert [event.kind for event in events] == ["auto_compact"]
    assert events[0].metadata == {
        "source": "runtime_pressure",
        "strategy": "auto",
        "trigger": "failure_circuit_breaker",
        "failure_count": 2,
        "max_failures": 2,
    }


def test_auto_compact_success_resets_failure_circuit_breaker(tmp_path: Path) -> None:
    registry = build_default_registry(include_discovery=True)
    failing = FailingSummarizer()
    first_success = FakeSummarizer("<summary>Recovered compact summary.</summary>")
    second_success = FakeSummarizer("<summary>Still allowed summary.</summary>")
    context = runtime_context(tmp_path)
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=10,
        auto_compact_max_failures=2,
        keep_recent_messages=1,
    )

    def request(model: object) -> ModelRequest:
        return ModelRequest(
            model=model,
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

    middleware.wrap_model_call(request(failing), lambda _request: SimpleNamespace(result="ok"))
    middleware.wrap_model_call(
        request(first_success), lambda _request: SimpleNamespace(result="ok")
    )
    middleware.wrap_model_call(request(failing), lambda _request: SimpleNamespace(result="ok"))
    middleware.wrap_model_call(
        request(second_success), lambda _request: SimpleNamespace(result="ok")
    )

    assert len(failing.requests) == 2
    assert len(first_success.requests) == 1
    assert len(second_success.requests) == 1
    assert [event.kind for event in context.event_sink.snapshot()] == [
        "auto_compact",
        "auto_compact",
    ]


def test_auto_compact_retries_prompt_too_long_summary_source() -> None:
    registry = build_default_registry(include_discovery=True)
    summarizer = PromptTooLongThenSuccessSummarizer(
        "<summary>Retry compact summary.</summary>"
    )
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=10,
        auto_compact_ptl_retry_limit=1,
        keep_recent_messages=1,
    )
    captured: dict[str, object] = {}

    request = ModelRequest(
        model=summarizer,
        messages=[
            HumanMessage(content="oldest context " * 500),
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

    def handler(active_request: ModelRequest):
        captured["messages"] = active_request.messages
        return SimpleNamespace(result="ok")

    middleware.wrap_model_call(request, handler)

    assert len(summarizer.requests) == 2
    assert len(summarizer.requests[1]) < len(summarizer.requests[0])
    messages = captured["messages"]
    assert isinstance(messages, list)
    assert str(messages[0].content).startswith(LIVE_COMPACT_BOUNDARY_PREFIX)
    assert "Retry compact summary." in str(messages[1].content)


def test_auto_compact_does_not_retry_non_prompt_too_long_failure() -> None:
    summarizer = FailingSummarizer()

    maybe_auto_compact_messages(
        [
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        summarizer=summarizer,
        threshold_tokens=10,
        keep_recent_messages=1,
        ptl_retry_limit=3,
    )

    assert len(summarizer.requests) == 1


def test_auto_compact_exhausted_ptl_retries_can_trip_circuit_breaker(
    tmp_path: Path,
) -> None:
    registry = build_default_registry(include_discovery=True)
    summarizer = PromptTooLongSummarizer()
    context = runtime_context(tmp_path)
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=10,
        auto_compact_max_failures=1,
        auto_compact_ptl_retry_limit=1,
        keep_recent_messages=1,
    )

    def request() -> ModelRequest:
        return ModelRequest(
            model=summarizer,
            messages=[
                HumanMessage(content="oldest context " * 500),
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

    middleware.wrap_model_call(request(), lambda _request: SimpleNamespace(result="ok"))
    middleware.wrap_model_call(request(), lambda _request: SimpleNamespace(result="ok"))

    assert len(summarizer.requests) == 2
    events = context.event_sink.snapshot()
    assert [event.kind for event in events] == ["auto_compact"]
    assert events[0].metadata["trigger"] == "failure_circuit_breaker"


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
    assert events[0].metadata["source"] == "runtime_pressure"
    assert events[0].metadata["strategy"] == "microcompact"
    assert events[0].metadata["cleared_tool_results"] == 2
    assert events[0].metadata["tools_cleared"] == 2
    assert events[0].metadata["tools_kept"] == 1
    assert events[0].metadata["tokens_saved_estimate"] > 0
    assert events[0].metadata["keep_recent"] == 1
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


def test_runtime_pressure_microcompact_evidence_includes_bounded_savings(
    tmp_path: Path,
) -> None:
    registry = build_default_registry(include_discovery=True)
    session_store = JsonlSessionStore(tmp_path / "sessions")
    context = runtime_context(tmp_path, session_store=session_store)
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=None,
        keep_recent_tool_results=1,
    )

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
        runtime=SimpleNamespace(context=context),
        model_settings={},
    )

    middleware.wrap_model_call(request, lambda _request: SimpleNamespace(result="ok"))
    loaded = session_store.load_session(session_id="session-1", workdir=tmp_path)

    assert loaded.summary.evidence_count == 1
    assert loaded.evidence[0].kind == "runtime_event"
    assert loaded.evidence[0].metadata["event_kind"] == "microcompact"
    assert loaded.evidence[0].metadata["cleared_tool_results"] == 1
    assert loaded.evidence[0].metadata["tools_cleared"] == 1
    assert loaded.evidence[0].metadata["tools_kept"] == 1
    assert loaded.evidence[0].metadata["tokens_saved_estimate"] > 0
    assert loaded.evidence[0].metadata["keep_recent"] == 1
