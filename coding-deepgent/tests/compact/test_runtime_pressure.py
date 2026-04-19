from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Sequence
from typing import Any, cast

from langchain.agents.middleware import ModelRequest, ModelResponse
from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AnyMessage, BaseMessage
from langchain_core.prompt_values import PromptValue
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig
from pydantic import PrivateAttr

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
    drain_collapse_projection_messages,
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
from coding_deepgent.runtime import InMemoryEventSink, RuntimeContext, RuntimeEvent
from coding_deepgent.sessions import (
    COLLAPSE_EVENT_KIND,
    JsonlSessionStore,
    TranscriptProjection,
    build_recovery_brief,
    render_recovery_brief,
)
from coding_deepgent.tool_system import build_default_registry

MessageLike = BaseMessage | list[str] | tuple[str, str] | str | dict[str, Any]
ModelInput = PromptValue | str | Sequence[MessageLike]


class FakeSummarizer(FakeMessagesListChatModel):
    _requests: list[list[dict[str, Any]]] = PrivateAttr(default_factory=list)

    def __init__(self, response: str) -> None:
        super().__init__(responses=[AIMessage(content=response)])

    @property
    def requests(self) -> list[list[dict[str, Any]]]:
        return self._requests

    def invoke(
        self,
        input: ModelInput,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        if isinstance(input, list):
            self._requests.append(cast(list[dict[str, Any]], input))
        return super().invoke(input, config=config, **kwargs)


class FailingSummarizer(FakeMessagesListChatModel):
    _requests: list[list[dict[str, Any]]] = PrivateAttr(default_factory=list)

    def __init__(self) -> None:
        super().__init__(responses=[AIMessage(content="unused")])

    @property
    def requests(self) -> list[list[dict[str, Any]]]:
        return self._requests

    def invoke(
        self,
        input: ModelInput,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        del config, kwargs
        if isinstance(input, list):
            self._requests.append(cast(list[dict[str, Any]], input))
        raise RuntimeError("compact summarizer unavailable")


class PromptTooLongThenSuccessSummarizer(FakeMessagesListChatModel):
    _requests: list[list[dict[str, Any]]] = PrivateAttr(default_factory=list)

    def __init__(self, response: str) -> None:
        super().__init__(responses=[AIMessage(content=response)])

    @property
    def requests(self) -> list[list[dict[str, Any]]]:
        return self._requests

    def invoke(
        self,
        input: ModelInput,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        if isinstance(input, list):
            self._requests.append(cast(list[dict[str, Any]], input))
        if len(self._requests) == 1:
            raise RuntimeError("prompt too long for compact request")
        return super().invoke(input, config=config, **kwargs)


class PromptTooLongSummarizer(FakeMessagesListChatModel):
    _requests: list[list[dict[str, Any]]] = PrivateAttr(default_factory=list)

    def __init__(self) -> None:
        super().__init__(responses=[AIMessage(content="unused")])

    @property
    def requests(self) -> list[list[dict[str, Any]]]:
        return self._requests

    def invoke(
        self,
        input: ModelInput,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        del config, kwargs
        if isinstance(input, list):
            self._requests.append(cast(list[dict[str, Any]], input))
        raise RuntimeError("prompt too long for compact request")


def runtime_context(
    tmp_path: Path,
    *,
    session_store: JsonlSessionStore | None = None,
    entrypoint: str = "test",
    agent_name: str = "test-agent",
    transcript_projection: TranscriptProjection | None = None,
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
        transcript_projection=transcript_projection,
    )


def _unused_model() -> BaseChatModel:
    return FakeMessagesListChatModel(responses=[AIMessage(content="unused")])


def _runtime(
    context: RuntimeContext | None = None,
    *,
    store: object | None = None,
) -> Runtime[Any]:
    return Runtime(context=context, store=cast(Any, store))


def _request(
    *,
    model: BaseChatModel,
    messages: list[AnyMessage],
    context: RuntimeContext | None = None,
    state: dict[str, Any] | None = None,
    model_settings: dict[str, Any] | None = None,
    store: object | None = None,
) -> ModelRequest:
    runtime = _runtime(context, store=store) if (context is not None or store is not None) else None
    return ModelRequest(
        model=model,
        messages=messages,
        system_message=SystemMessage(content="Base"),
        tool_choice=None,
        tools=[],
        response_format=None,
        state=cast(Any, state if state is not None else {"messages": []}),
        runtime=runtime,
        model_settings=model_settings or {},
    )


def _ok_response(text: str = "ok") -> ModelResponse:
    return ModelResponse(result=[AIMessage(content=text)])


def _events(context: RuntimeContext) -> tuple[RuntimeEvent, ...]:
    return cast(InMemoryEventSink, context.event_sink).snapshot()


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
        return _ok_response()

    request = _request(
        model=_unused_model(),
        messages=[
            HumanMessage(content="inspect files"),
            _read_call("call-1"),
            ToolMessage(content="x" * 500, tool_call_id="call-1"),
            _read_call("call-2"),
            ToolMessage(content="y" * 500, tool_call_id="call-2"),
        ],
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
        return _ok_response()

    request = _request(
        model=_unused_model(),
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
        context=context,
    )

    middleware.wrap_model_call(request, handler)

    messages = captured["messages"]
    assert isinstance(messages, list)
    assert messages[2].content == MICROCOMPACT_CLEARED_MESSAGE
    assert messages[5].content == MICROCOMPACT_CLEARED_MESSAGE
    assert messages[7].content == "z" * 500
    events = _events(context)
    assert [event.kind for event in events] == ["microcompact", "token_budget"]
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

    request = _request(
        model=_unused_model(),
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
        context=context,
    )

    middleware.wrap_model_call(request, lambda _request: _ok_response())

    events = _events(context)
    assert [event.kind for event in events] == ["microcompact", "token_budget"]
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

    request = _request(
        model=_unused_model(),
        messages=[
            _assistant_at("2026-04-16T10:00:00Z"),
            _read_call("call-1"),
            ToolMessage(content="x" * 100, tool_call_id="call-1"),
            _read_call("call-2"),
            ToolMessage(content="y" * 100, tool_call_id="call-2"),
        ],
        context=context,
    )

    def handler(active_request: ModelRequest):
        captured["messages"] = active_request.messages
        return _ok_response()

    middleware.wrap_model_call(request, handler)

    messages = captured["messages"]
    assert isinstance(messages, list)
    assert messages[2].content == "x" * 100
    assert messages[4].content == "y" * 100
    assert [event.kind for event in _events(context)] == ["token_budget"]


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


def test_collapse_live_messages_with_summary_preserves_recent_assistant_round() -> None:
    messages = [
        HumanMessage(content="old request"),
        _read_call("call-1"),
        ToolMessage(content="result", tool_call_id="call-1"),
        AIMessage(content="assistant checkpoint"),
        HumanMessage(content="latest user prompt"),
    ]

    collapsed = collapse_live_messages_with_summary(
        messages,
        summary="Earlier work was collapsed.",
        keep_recent_messages=1,
    )

    assert str(collapsed[0].content).startswith(LIVE_COLLAPSE_BOUNDARY_PREFIX)
    assert str(collapsed[1].content).startswith(LIVE_COLLAPSE_SUMMARY_PREFIX)
    assert isinstance(collapsed[2], AIMessage)
    assert collapsed[2].content == "assistant checkpoint"
    assert isinstance(collapsed[3], HumanMessage)
    assert collapsed[3].content == "latest user prompt"


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

    request = _request(
        model=summarizer,
        messages=[
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        context=context,
    )

    def handler(active_request: ModelRequest):
        captured["messages"] = active_request.messages
        return _ok_response()

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


def test_maybe_collapse_messages_uses_pressure_ratio_when_configured() -> None:
    summarizer = FakeSummarizer("<summary>Ratio collapse summary.</summary>")
    messages = [
        HumanMessage(content="x" * 5000),
        HumanMessage(content="y" * 5000),
    ]

    collapsed = maybe_collapse_messages(
        messages,
        summarizer=summarizer,
        threshold_tokens=None,
        context_window_tokens=3000,
        trigger_ratio=0.5,
        keep_recent_messages=1,
    )

    assert len(summarizer.requests) == 1
    assert str(collapsed[0].content).startswith(LIVE_COLLAPSE_BOUNDARY_PREFIX)
    assert "Ratio collapse summary." in str(collapsed[1].content)


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


def test_runtime_pressure_middleware_persists_collapse_record_when_projection_exists(
    tmp_path: Path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    context = runtime_context(
        tmp_path,
        session_store=store,
        transcript_projection=TranscriptProjection(
            entries=(("msg-000000",), ("msg-000001",))
        ),
    )
    assert context.session_context is not None
    store.append_message(context.session_context, role="assistant", content="continue")
    middleware = RuntimePressureMiddleware(
        registry=build_default_registry(include_discovery=True),
        collapse_threshold_tokens=10,
        keep_recent_messages_after_collapse=1,
        auto_compact_threshold_tokens=None,
    )
    request = _request(
        model=FakeSummarizer("<summary>Generated collapse summary.</summary>"),
        messages=[
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        context=context,
    )

    middleware.wrap_model_call(request, lambda active_request: _ok_response())

    raw_records = [
        json.loads(line)
        for line in context.session_context.transcript_path.read_text(encoding="utf-8").splitlines()
    ]
    collapse_records = [
        record for record in raw_records if record.get("event_kind") == COLLAPSE_EVENT_KIND
    ]
    loaded = store.load_session(session_id="session-1", workdir=tmp_path)

    assert len(collapse_records) == 1
    assert loaded.summary.collapse_count == 1
    assert loaded.collapses[0].summary == "Generated collapse summary."
    assert loaded.collapses[0].start_message_id == "msg-000000"
    assert loaded.collapses[0].end_message_id == "msg-000000"
    assert loaded.collapses[0].covered_message_ids == ("msg-000000",)
    assert loaded.collapses[0].metadata is not None
    collapse_metadata = loaded.collapses[0].metadata
    assert collapse_metadata is not None
    assert collapse_metadata["source"] == "runtime_pressure"


def test_runtime_pressure_middleware_persists_collapse_record_using_assistant_round_boundary(
    tmp_path: Path,
) -> None:
    store = JsonlSessionStore(tmp_path / "sessions-store")
    context = runtime_context(
        tmp_path,
        session_store=store,
        transcript_projection=TranscriptProjection(
            entries=(
                ("msg-000000",),
                ("msg-000001",),
                ("msg-000002",),
                ("msg-000003",),
                ("msg-000004",),
            )
        ),
    )
    assert context.session_context is not None
    store.append_message(context.session_context, role="assistant", content="assistant one")
    store.append_message(context.session_context, role="user", content="tool result one")
    store.append_message(context.session_context, role="assistant", content="assistant two")
    store.append_message(context.session_context, role="user", content="latest user prompt")
    middleware = RuntimePressureMiddleware(
        registry=build_default_registry(include_discovery=True),
        collapse_threshold_tokens=10,
        keep_recent_messages_after_collapse=1,
        auto_compact_threshold_tokens=None,
    )
    request = _request(
        model=FakeSummarizer("<summary>Generated collapse summary.</summary>"),
        messages=[
            HumanMessage(content="x" * 5000),
            _read_call("call-1"),
            ToolMessage(content="result", tool_call_id="call-1"),
            AIMessage(content="assistant checkpoint"),
            HumanMessage(content="latest user prompt"),
        ],
        context=context,
    )

    middleware.wrap_model_call(request, lambda active_request: _ok_response())

    loaded = store.load_session(session_id="session-1", workdir=tmp_path)

    assert loaded.summary.collapse_count == 1
    assert loaded.collapses[0].start_message_id == "msg-000000"
    assert loaded.collapses[0].end_message_id == "msg-000002"
    assert loaded.collapses[0].covered_message_ids == (
        "msg-000000",
        "msg-000001",
        "msg-000002",
    )


def test_runtime_pressure_middleware_drains_collapse_projection_before_reactive_compact(
    tmp_path: Path,
) -> None:
    middleware = RuntimePressureMiddleware(
        registry=build_default_registry(include_discovery=True),
        collapse_threshold_tokens=10,
        keep_recent_messages_after_collapse=1,
        auto_compact_threshold_tokens=None,
    )
    context = runtime_context(tmp_path)
    calls: list[list[BaseMessage]] = []
    request = _request(
        model=FakeSummarizer("<summary>Generated collapse summary.</summary>"),
        messages=[
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        context=context,
    )

    def handler(active_request: ModelRequest):
        calls.append(list(active_request.messages))
        if len(calls) == 1:
            raise RuntimeError("prompt too long for current context window")
        return _ok_response()

    middleware.wrap_model_call(request, handler)

    assert len(calls) == 2
    assert str(calls[0][0].content).startswith(LIVE_COLLAPSE_BOUNDARY_PREFIX)
    assert str(calls[0][1].content).startswith(LIVE_COLLAPSE_SUMMARY_PREFIX)
    assert str(calls[1][0].content).startswith(LIVE_COLLAPSE_BOUNDARY_PREFIX)
    assert "overflow_drain" in str(calls[1][0].content)
    assert all(
        not str(message.content).startswith(LIVE_COLLAPSE_SUMMARY_PREFIX)
        for message in calls[1]
        if hasattr(message, "content")
    )
    assert [event.kind for event in _events(context)] == [
        "context_collapse",
        "context_collapse",
        "token_budget",
        "post_autocompact_turn",
    ]


def test_drain_collapse_projection_messages_removes_summary() -> None:
    drained = drain_collapse_projection_messages(
        collapse_live_messages_with_summary(
            [
                HumanMessage(content="old"),
                HumanMessage(content="recent"),
            ],
            summary="Collapsed context.",
            keep_recent_messages=1,
        )
    )

    assert str(drained[0].content).startswith(LIVE_COLLAPSE_BOUNDARY_PREFIX)
    assert "overflow_drain" in str(drained[0].content)
    assert drained[1].content == "recent"


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
        return _ok_response()

    request = _request(
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
        context=context,
    )

    middleware.wrap_model_call(request, handler)

    assert [event.kind for event in _events(context)] == [
        "snip",
        "microcompact",
        "context_collapse",
        "auto_compact",
        "auto_compact",
        "token_budget",
        "post_autocompact_turn",
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
        return _ok_response()

    request = _request(
        model=summarizer,
        messages=[
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        context=runtime_context(Path.cwd()),
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
    state: dict[str, Any] = {"messages": []}

    request = _request(
        model=summarizer,
        messages=[
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        state=state,
        context=runtime_context(Path.cwd()),
    )

    middleware.wrap_model_call(request, lambda _request: _ok_response())

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
        return _ok_response()

    def request() -> ModelRequest:
        return _request(
            model=summarizer,
            messages=[
                HumanMessage(content="x" * 5000),
                HumanMessage(content="y" * 5000),
            ],
            context=context,
        )

    middleware.wrap_model_call(request(), handler)
    middleware.wrap_model_call(request(), handler)
    middleware.wrap_model_call(request(), handler)

    assert handler_calls == 3
    assert len(summarizer.requests) == 2
    events = _events(context)
    assert [event.kind for event in events] == [
        "auto_compact",
        "token_budget",
        "auto_compact",
        "token_budget",
        "auto_compact",
        "token_budget",
    ]
    assert events[0].metadata["outcome"] == "attempted"
    assert events[2].metadata["outcome"] == "attempted"
    assert events[4].metadata == {
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

    def request(model: BaseChatModel) -> ModelRequest:
        return _request(
            model=model,
            messages=[
                HumanMessage(content="x" * 5000),
                HumanMessage(content="y" * 5000),
            ],
            context=context,
        )

    middleware.wrap_model_call(request(failing), lambda _request: _ok_response())
    middleware.wrap_model_call(
        request(first_success), lambda _request: _ok_response()
    )
    middleware.wrap_model_call(request(failing), lambda _request: _ok_response())
    middleware.wrap_model_call(
        request(second_success), lambda _request: _ok_response()
    )

    assert len(failing.requests) == 2
    assert len(first_success.requests) == 1
    assert len(second_success.requests) == 1
    assert [event.kind for event in _events(context)] == [
        "auto_compact",
        "token_budget",
        "auto_compact",
        "auto_compact",
        "token_budget",
        "post_autocompact_turn",
        "auto_compact",
        "token_budget",
        "auto_compact",
        "auto_compact",
        "token_budget",
        "post_autocompact_turn",
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

    request = _request(
        model=summarizer,
        messages=[
            HumanMessage(content="oldest context " * 500),
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        context=runtime_context(Path.cwd()),
    )

    def handler(active_request: ModelRequest):
        captured["messages"] = active_request.messages
        return _ok_response()

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
        return _request(
            model=summarizer,
            messages=[
                HumanMessage(content="oldest context " * 500),
                HumanMessage(content="x" * 5000),
                HumanMessage(content="y" * 5000),
            ],
            context=context,
        )

    middleware.wrap_model_call(request(), lambda _request: _ok_response())
    middleware.wrap_model_call(request(), lambda _request: _ok_response())

    assert len(summarizer.requests) == 2
    events = _events(context)
    assert [event.kind for event in events] == [
        "auto_compact",
        "token_budget",
        "auto_compact",
        "token_budget",
    ]
    assert events[2].metadata["trigger"] == "failure_circuit_breaker"


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

    request = _request(
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
        context=context,
    )

    middleware.wrap_model_call(request, lambda _request: _ok_response())

    events = _events(context)
    assert [event.kind for event in events] == [
        "microcompact",
        "auto_compact",
        "auto_compact",
        "token_budget",
        "post_autocompact_turn",
    ]
    assert events[0].metadata["source"] == "runtime_pressure"
    assert events[0].metadata["strategy"] == "microcompact"
    assert events[0].metadata["cleared_tool_results"] == 2
    assert events[0].metadata["tools_cleared"] == 2
    assert events[0].metadata["tools_kept"] == 1
    assert events[0].metadata["tokens_saved_estimate"] > 0
    assert events[0].metadata["keep_recent"] == 1
    assert events[1].metadata["outcome"] == "attempted"
    assert events[2].metadata == {
        "source": "runtime_pressure",
        "strategy": "auto",
        "outcome": "succeeded",
        "pre_compact_total": events[2].metadata["pre_compact_total"],
        "post_compact_total": events[2].metadata["post_compact_total"],
        "tokens_saved_estimate": events[2].metadata["tokens_saved_estimate"],
        "hidden_messages": events[2].metadata["hidden_messages"],
        "used_session_memory_assist": False,
        "restored_path_count": 0,
    }
    assert events[3].metadata["input_token_estimate"] > 0
    assert events[3].metadata["output_token_estimate"] > 0
    assert events[4].metadata["pre_compact_total"] == events[2].metadata["pre_compact_total"]
    assert events[4].metadata["post_compact_total"] == events[2].metadata["post_compact_total"]
    assert events[4].metadata["new_turn_input"] == events[3].metadata["input_token_estimate"]
    assert events[4].metadata["new_turn_output"] == events[3].metadata["output_token_estimate"]


def test_runtime_pressure_model_request_dump_is_env_gated(
    tmp_path: Path,
    monkeypatch,
) -> None:
    registry = build_default_registry(include_discovery=True)
    context = runtime_context(tmp_path)
    middleware = RuntimePressureMiddleware(
        registry=registry,
        auto_compact_threshold_tokens=None,
    )

    request = _request(
        model=_unused_model(),
        messages=[HumanMessage(content="hello dump")],
        model_settings={"api_key": "secret", "temperature": 0},
        context=context,
    )

    middleware.wrap_model_call(request, lambda _request: _ok_response())
    dump_path = (
        tmp_path
        / ".coding-deepgent"
        / "prompt-dumps"
        / "session-1__test-agent.jsonl"
    )
    assert not dump_path.exists()

    monkeypatch.setenv("CODING_DEEPGENT_DUMP_PROMPTS", "1")
    middleware.wrap_model_call(request, lambda _request: _ok_response())

    record = json.loads(dump_path.read_text(encoding="utf-8").splitlines()[0])
    assert record["record_type"] == "model_request"
    assert record["messages"][0]["content"] == "hello dump"
    assert record["model_settings"]["api_key"] == "<redacted>"


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
    calls: list[list[BaseMessage]] = []

    def handler(request: ModelRequest):
        calls.append(list(request.messages))
        if len(calls) == 1:
            raise RuntimeError("prompt too long for current context window")
        return _ok_response()

    request = _request(
        model=summarizer,
        messages=[
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        context=context,
    )

    middleware.wrap_model_call(request, handler)

    assert len(calls) == 2
    assert [event.kind for event in _events(context)] == [
        "reactive_compact",
        "token_budget",
    ]
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

    request = _request(
        model=summarizer,
        messages=[
            HumanMessage(content="x" * 5000),
            HumanMessage(content="y" * 5000),
        ],
        state={
            "messages": [],
            "session_memory": {
                "content": "Keep repo focus.",
                "source": "manual",
                "message_count": 2,
                "updated_at": "2026-04-15T00:00:00Z",
            },
        },
        context=context,
    )

    middleware.wrap_model_call(request, lambda _request: _ok_response())
    loaded = session_store.load_session(session_id="session-1", workdir=tmp_path)
    rendered = render_recovery_brief(build_recovery_brief(loaded))

    assert loaded.summary.evidence_count == 3
    assert [item.metadata["event_kind"] for item in loaded.evidence if item.metadata] == [
        "auto_compact",
        "auto_compact",
        "post_autocompact_turn",
    ]
    assert loaded.evidence[0].status == "recorded"
    first_metadata = loaded.evidence[0].metadata
    assert first_metadata is not None
    assert first_metadata["outcome"] == "attempted"
    assert loaded.evidence[1].kind == "runtime_event"
    assert loaded.evidence[1].status == "completed"
    second_metadata = loaded.evidence[1].metadata
    assert second_metadata is not None
    assert second_metadata == {
        "event_kind": "auto_compact",
        "source": "runtime_pressure",
        "strategy": "auto",
        "outcome": "succeeded",
        "hidden_messages": second_metadata["hidden_messages"],
        "pre_compact_total": second_metadata["pre_compact_total"],
        "post_compact_total": second_metadata["post_compact_total"],
        "tokens_saved_estimate": second_metadata["tokens_saved_estimate"],
        "used_session_memory_assist": True,
        "restored_path_count": 0,
    }
    third_metadata = loaded.evidence[2].metadata
    assert third_metadata is not None
    assert third_metadata == {
        "event_kind": "post_autocompact_turn",
        "source": "runtime_pressure",
        "trigger": "auto_compact",
        "pre_compact_total": third_metadata["pre_compact_total"],
        "post_compact_total": third_metadata["post_compact_total"],
        "new_turn_input": third_metadata["new_turn_input"],
        "new_turn_output": third_metadata["new_turn_output"],
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

    request = _request(
        model=_unused_model(),
        messages=[
            HumanMessage(content="inspect files"),
            _read_call("call-1"),
            ToolMessage(content="x" * 500, tool_call_id="call-1"),
            _read_call("call-2"),
            ToolMessage(content="y" * 500, tool_call_id="call-2"),
        ],
        context=context,
    )

    middleware.wrap_model_call(request, lambda _request: _ok_response())
    loaded = session_store.load_session(session_id="session-1", workdir=tmp_path)

    assert loaded.summary.evidence_count == 1
    assert loaded.evidence[0].kind == "runtime_event"
    metadata = loaded.evidence[0].metadata
    assert metadata is not None
    assert metadata["event_kind"] == "microcompact"
    assert metadata["cleared_tool_results"] == 1
    assert metadata["tools_cleared"] == 1
    assert metadata["tools_kept"] == 1
    assert metadata["tokens_saved_estimate"] > 0
    assert metadata["keep_recent"] == 1
