from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, cast

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from coding_deepgent.compact.summarizer import generate_compact_summary
from coding_deepgent.hooks.dispatcher import dispatch_context_hook
from coding_deepgent.hooks.events import HookEventName
from coding_deepgent.runtime.events import RuntimeEvent
from coding_deepgent.sessions.evidence_events import append_runtime_event_evidence
from coding_deepgent.sessions.records import SessionContext, TranscriptProjection
from coding_deepgent.sessions.store_jsonl import JsonlSessionStore
from coding_deepgent.sessions.session_memory import (
    compact_summary_assist_text,
    read_session_memory_artifact,
    update_session_memory_from_summary,
)
from coding_deepgent.tool_system.capabilities import CapabilityRegistry

MICROCOMPACT_CLEARED_MESSAGE = "[Old tool result content cleared]"
DEFAULT_KEEP_RECENT_TOOL_RESULTS = 3
DEFAULT_MICROCOMPACT_MIN_CONTENT_CHARS = 120
LIVE_SNIP_BOUNDARY_PREFIX = "coding-deepgent live snip boundary"
LIVE_COLLAPSE_BOUNDARY_PREFIX = "coding-deepgent live collapse boundary"
LIVE_COLLAPSE_SUMMARY_PREFIX = "This session is being continued from a collapsed live context."
LIVE_COMPACT_BOUNDARY_PREFIX = "coding-deepgent live compact boundary"
LIVE_COMPACT_SUMMARY_PREFIX = "This session is being continued from a compacted live invocation."
LIVE_COMPACT_RESTORATION_PREFIX = "Restored persisted tool outputs:"
DEFAULT_AUTO_COMPACT_THRESHOLD_TOKENS = 8000
DEFAULT_KEEP_RECENT_MESSAGES = 4
DEFAULT_SNIP_THRESHOLD_TOKENS = None
DEFAULT_KEEP_RECENT_MESSAGES_AFTER_SNIP = 12
DEFAULT_COLLAPSE_THRESHOLD_TOKENS = 12000
DEFAULT_KEEP_RECENT_MESSAGES_AFTER_COLLAPSE = 8
DEFAULT_MICROCOMPACT_TIME_GAP_MINUTES = None
DEFAULT_MICROCOMPACT_MIN_SAVED_TOKENS = 0
DEFAULT_MICROCOMPACT_PROTECT_RECENT_TOKENS = None
DEFAULT_MICROCOMPACT_MIN_PRUNE_SAVED_TOKENS = 0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class MicrocompactStats:
    cleared_tool_results: int = 0
    kept_tool_results: int = 0
    tokens_saved_estimate: int = 0
    keep_recent_tool_results: int = DEFAULT_KEEP_RECENT_TOOL_RESULTS
    protected_recent_tokens: int | None = DEFAULT_MICROCOMPACT_PROTECT_RECENT_TOKENS


@dataclass(frozen=True, slots=True)
class MicrocompactResult:
    messages: list[BaseMessage]
    stats: MicrocompactStats


@dataclass(frozen=True, slots=True)
class TimeBasedMicrocompactDecision:
    attempted: bool
    result: MicrocompactResult | None = None
    gap_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class AutoCompactResult:
    messages: list[BaseMessage]
    attempted: bool = False
    compacted: bool = False
    failed: bool = False


@dataclass(frozen=True, slots=True)
class LiveCompactionResult:
    boundary_message: SystemMessage
    summary_message: HumanMessage
    preserved_tail: tuple[BaseMessage, ...]
    trigger: str
    restoration_messages: tuple[SystemMessage, ...] = ()
    original_token_estimate: int = 0
    projected_token_estimate: int = 0

    @property
    def restored_path_count(self) -> int:
        return sum(
            max(0, len(str(message.content).splitlines()) - 1)
            for message in self.restoration_messages
        )

    def render(self) -> list[BaseMessage]:
        return [
            self.boundary_message,
            self.summary_message,
            *self.restoration_messages,
            *self.preserved_tail,
        ]


def _with_projected_token_estimate(result: LiveCompactionResult) -> LiveCompactionResult:
    return LiveCompactionResult(
        boundary_message=result.boundary_message,
        summary_message=result.summary_message,
        restoration_messages=result.restoration_messages,
        preserved_tail=result.preserved_tail,
        trigger=result.trigger,
        original_token_estimate=result.original_token_estimate,
        projected_token_estimate=estimate_message_tokens(result.render()),
    )


def microcompact_messages(
    messages: Sequence[BaseMessage],
    *,
    registry: CapabilityRegistry,
    keep_recent_tool_results: int = DEFAULT_KEEP_RECENT_TOOL_RESULTS,
    min_content_chars: int = DEFAULT_MICROCOMPACT_MIN_CONTENT_CHARS,
    protect_recent_tokens: int | None = DEFAULT_MICROCOMPACT_PROTECT_RECENT_TOKENS,
    min_saved_tokens: int = DEFAULT_MICROCOMPACT_MIN_PRUNE_SAVED_TOKENS,
) -> list[BaseMessage]:
    return microcompact_messages_with_stats(
        messages,
        registry=registry,
        keep_recent_tool_results=keep_recent_tool_results,
        min_content_chars=min_content_chars,
        protect_recent_tokens=protect_recent_tokens,
        min_saved_tokens=min_saved_tokens,
    ).messages


def microcompact_messages_with_stats(
    messages: Sequence[BaseMessage],
    *,
    registry: CapabilityRegistry,
    keep_recent_tool_results: int = DEFAULT_KEEP_RECENT_TOOL_RESULTS,
    min_content_chars: int = DEFAULT_MICROCOMPACT_MIN_CONTENT_CHARS,
    protect_recent_tokens: int | None = DEFAULT_MICROCOMPACT_PROTECT_RECENT_TOKENS,
    min_saved_tokens: int = DEFAULT_MICROCOMPACT_MIN_PRUNE_SAVED_TOKENS,
) -> MicrocompactResult:
    if keep_recent_tool_results < 0:
        raise ValueError("keep_recent_tool_results must be non-negative")
    if protect_recent_tokens is not None and protect_recent_tokens < 1:
        raise ValueError("protect_recent_tokens must be positive")
    if min_saved_tokens < 0:
        raise ValueError("min_saved_tokens must be non-negative")

    eligible_tool_calls = _eligible_tool_calls(messages, registry=registry)
    if not eligible_tool_calls:
        return MicrocompactResult(
            messages=list(messages),
            stats=MicrocompactStats(
                keep_recent_tool_results=keep_recent_tool_results,
                protected_recent_tokens=protect_recent_tokens,
            ),
        )

    compactable_indexes = [
        index
        for index, message in enumerate(messages)
        if _is_compactable_tool_result(
            message,
            eligible_tool_calls=eligible_tool_calls,
            min_content_chars=min_content_chars,
        )
    ]
    if protect_recent_tokens is None and len(compactable_indexes) <= keep_recent_tool_results:
        return MicrocompactResult(
            messages=list(messages),
            stats=MicrocompactStats(
                kept_tool_results=len(compactable_indexes),
                keep_recent_tool_results=keep_recent_tool_results,
                protected_recent_tokens=protect_recent_tokens,
            ),
        )

    rewritten = list(messages)
    if protect_recent_tokens is None:
        indexes_to_clear = compactable_indexes[:-keep_recent_tool_results or None]
        kept_count = len(compactable_indexes) - len(indexes_to_clear)
    else:
        indexes_to_clear = _token_budget_indexes_to_clear(
            messages,
            compactable_indexes=compactable_indexes,
            protect_recent_tokens=protect_recent_tokens,
        )
        kept_count = len(compactable_indexes) - len(indexes_to_clear)
        if not indexes_to_clear:
            return MicrocompactResult(
                messages=list(messages),
                stats=MicrocompactStats(
                    kept_tool_results=kept_count,
                    keep_recent_tool_results=kept_count,
                    protected_recent_tokens=protect_recent_tokens,
                ),
            )
    tokens_saved_estimate = 0
    for index in indexes_to_clear:
        message = rewritten[index]
        if isinstance(message, ToolMessage):
            original_tokens = _estimate_message_tokens(message)
            rewritten[index] = message.model_copy(
                update={"content": _microcompacted_content(message)}
            )
            tokens_saved_estimate += max(
                0, original_tokens - _estimate_message_tokens(rewritten[index])
            )
    if tokens_saved_estimate < min_saved_tokens:
        return MicrocompactResult(
            messages=list(messages),
            stats=MicrocompactStats(
                kept_tool_results=len(compactable_indexes),
                keep_recent_tool_results=keep_recent_tool_results,
                protected_recent_tokens=protect_recent_tokens,
            ),
        )
    return MicrocompactResult(
        messages=rewritten,
        stats=MicrocompactStats(
            cleared_tool_results=len(indexes_to_clear),
            kept_tool_results=kept_count,
            tokens_saved_estimate=tokens_saved_estimate,
            keep_recent_tool_results=(
                keep_recent_tool_results
                if protect_recent_tokens is None
                else kept_count
            ),
            protected_recent_tokens=protect_recent_tokens,
        ),
    )


def _microcompact_event_metadata(stats: MicrocompactStats) -> dict[str, object]:
    metadata: dict[str, object] = {
        "source": "runtime_pressure",
        "strategy": "microcompact",
        "cleared_tool_results": stats.cleared_tool_results,
        "tools_cleared": stats.cleared_tool_results,
        "tools_kept": stats.kept_tool_results,
        "tokens_saved_estimate": stats.tokens_saved_estimate,
        "keep_recent": stats.keep_recent_tool_results,
    }
    if stats.protected_recent_tokens is not None:
        metadata["protected_recent_tokens"] = stats.protected_recent_tokens
    return metadata


def maybe_time_based_microcompact_messages(
    messages: Sequence[BaseMessage],
    *,
    registry: CapabilityRegistry,
    context: object,
    gap_threshold_minutes: int | None,
    now: Callable[[], datetime] = _utc_now,
    keep_recent_tool_results: int = DEFAULT_KEEP_RECENT_TOOL_RESULTS,
    min_content_chars: int = DEFAULT_MICROCOMPACT_MIN_CONTENT_CHARS,
    min_saved_tokens: int = DEFAULT_MICROCOMPACT_MIN_SAVED_TOKENS,
    main_entrypoint: str = "coding-deepgent",
    main_agent_name: str = "coding-deepgent",
) -> TimeBasedMicrocompactDecision:
    if gap_threshold_minutes is None:
        return TimeBasedMicrocompactDecision(attempted=False)
    if gap_threshold_minutes < 1:
        raise ValueError("gap_threshold_minutes must be positive")
    if min_saved_tokens < 0:
        raise ValueError("min_saved_tokens must be non-negative")
    if not _is_main_runtime_context(
        context,
        main_entrypoint=main_entrypoint,
        main_agent_name=main_agent_name,
    ):
        return TimeBasedMicrocompactDecision(attempted=False)

    last_assistant_timestamp = _latest_assistant_timestamp(messages)
    if last_assistant_timestamp is None:
        return TimeBasedMicrocompactDecision(attempted=False)

    gap = now() - last_assistant_timestamp
    gap_minutes = max(0, int(gap.total_seconds() // 60))
    if gap_minutes < gap_threshold_minutes:
        return TimeBasedMicrocompactDecision(attempted=False)

    result = microcompact_messages_with_stats(
        messages,
        registry=registry,
        keep_recent_tool_results=max(1, keep_recent_tool_results),
        min_content_chars=min_content_chars,
    )
    if result.messages == list(messages):
        return TimeBasedMicrocompactDecision(
            attempted=True,
            result=None,
            gap_minutes=gap_minutes,
        )
    if result.stats.tokens_saved_estimate < min_saved_tokens:
        return TimeBasedMicrocompactDecision(
            attempted=True,
            result=None,
            gap_minutes=gap_minutes,
        )
    return TimeBasedMicrocompactDecision(
        attempted=True,
        result=result,
        gap_minutes=gap_minutes,
    )


def _time_based_microcompact_event_metadata(
    *, stats: MicrocompactStats, gap_minutes: int
) -> dict[str, object]:
    metadata = _microcompact_event_metadata(stats)
    metadata.update(
        {
            "trigger": "time_gap",
            "gap_minutes": gap_minutes,
        }
    )
    return metadata


@dataclass(frozen=True, slots=True)
class RuntimePressureMiddleware(AgentMiddleware):
    registry: CapabilityRegistry
    keep_recent_tool_results: int = DEFAULT_KEEP_RECENT_TOOL_RESULTS
    min_content_chars: int = DEFAULT_MICROCOMPACT_MIN_CONTENT_CHARS
    snip_threshold_tokens: int | None = DEFAULT_SNIP_THRESHOLD_TOKENS
    keep_recent_messages_after_snip: int = DEFAULT_KEEP_RECENT_MESSAGES_AFTER_SNIP
    collapse_threshold_tokens: int | None = DEFAULT_COLLAPSE_THRESHOLD_TOKENS
    model_context_window_tokens: int | None = None
    collapse_trigger_ratio: float | None = None
    keep_recent_messages_after_collapse: int = DEFAULT_KEEP_RECENT_MESSAGES_AFTER_COLLAPSE
    auto_compact_threshold_tokens: int | None = DEFAULT_AUTO_COMPACT_THRESHOLD_TOKENS
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES
    auto_compact_max_failures: int | None = None
    auto_compact_ptl_retry_limit: int = 0
    microcompact_time_gap_minutes: int | None = DEFAULT_MICROCOMPACT_TIME_GAP_MINUTES
    microcompact_min_saved_tokens: int = DEFAULT_MICROCOMPACT_MIN_SAVED_TOKENS
    microcompact_protect_recent_tokens: int | None = (
        DEFAULT_MICROCOMPACT_PROTECT_RECENT_TOKENS
    )
    microcompact_min_prune_saved_tokens: int = (
        DEFAULT_MICROCOMPACT_MIN_PRUNE_SAVED_TOKENS
    )
    main_entrypoint: str = "coding-deepgent"
    main_agent_name: str = "coding-deepgent"
    now: Callable[[], datetime] = _utc_now
    _auto_compact_failure_count: int = field(default=0, init=False, compare=False, repr=False)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        current_projection = _runtime_transcript_projection(request)
        processed = snip_messages(
            request.messages,
            threshold_tokens=self.snip_threshold_tokens,
            keep_recent_messages=self.keep_recent_messages_after_snip,
        )
        if _is_snipped(processed):
            current_projection = _projection_after_snip(
                request.messages,
                current_projection,
                keep_recent_messages=self.keep_recent_messages_after_snip,
            )
            _emit_runtime_pressure_event(
                request,
                kind="snip",
                message="Runtime pressure middleware snipped older live history.",
                metadata={
                    "source": "runtime_pressure",
                    "strategy": "snip",
                    "hidden_messages": _snip_hidden_message_count(processed),
                },
            )
        before_microcompact = processed
        context = getattr(request.runtime, "context", None)
        time_based_microcompact = maybe_time_based_microcompact_messages(
            before_microcompact,
            registry=self.registry,
            context=context,
            gap_threshold_minutes=self.microcompact_time_gap_minutes,
            now=self.now,
            keep_recent_tool_results=self.keep_recent_tool_results,
            min_content_chars=self.min_content_chars,
            min_saved_tokens=self.microcompact_min_saved_tokens,
            main_entrypoint=self.main_entrypoint,
            main_agent_name=self.main_agent_name,
        )
        if time_based_microcompact.result is not None:
            processed = time_based_microcompact.result.messages
            _emit_runtime_pressure_event(
                request,
                kind="microcompact",
                message="Runtime pressure middleware microcompacted older tool results.",
                metadata=_time_based_microcompact_event_metadata(
                    stats=time_based_microcompact.result.stats,
                    gap_minutes=time_based_microcompact.gap_minutes or 0,
                ),
            )
        elif not time_based_microcompact.attempted:
            microcompact_result = microcompact_messages_with_stats(
                before_microcompact,
                registry=self.registry,
                keep_recent_tool_results=self.keep_recent_tool_results,
                min_content_chars=self.min_content_chars,
                protect_recent_tokens=self.microcompact_protect_recent_tokens,
                min_saved_tokens=self.microcompact_min_prune_saved_tokens,
            )
            processed = microcompact_result.messages
            if processed != list(before_microcompact):
                _emit_runtime_pressure_event(
                    request,
                    kind="microcompact",
                    message="Runtime pressure middleware microcompacted older tool results.",
                    metadata=_microcompact_event_metadata(microcompact_result.stats),
                )
        session_memory_assist = _session_memory_assist_text(request.state, processed)
        collapse_source_messages = list(processed)
        collapse_source_projection = current_projection
        processed = maybe_collapse_messages(
            processed,
            summarizer=request.model,
            threshold_tokens=self.collapse_threshold_tokens,
            context_window_tokens=self.model_context_window_tokens,
            trigger_ratio=self.collapse_trigger_ratio,
            keep_recent_messages=self.keep_recent_messages_after_collapse,
            assist_context=session_memory_assist,
        )
        if _is_collapsed(processed):
            _append_collapse_record(
                request,
                source_messages=collapse_source_messages,
                projection=collapse_source_projection,
                collapsed_messages=processed,
                threshold_tokens=self.collapse_threshold_tokens,
                context_window_tokens=self.model_context_window_tokens,
                trigger_ratio=self.collapse_trigger_ratio,
                used_session_memory_assist=session_memory_assist is not None,
            )
            collapse_pressure = _pressure_metadata(
                collapse_source_messages,
                context_window_tokens=self.model_context_window_tokens,
            )
            _emit_runtime_pressure_event(
                request,
                kind="context_collapse",
                message="Runtime pressure middleware collapsed older live history.",
                metadata={
                    "source": "runtime_pressure",
                    "strategy": "context_collapse",
                    "collapsed_messages": _collapse_collapsed_message_count(processed),
                    "used_session_memory_assist": session_memory_assist is not None,
                    "restored_path_count": _restored_path_count(processed),
                    **collapse_pressure,
                },
            )
        if self._should_skip_auto_compact():
            _emit_runtime_pressure_event(
                request,
                kind="auto_compact",
                message="Runtime pressure middleware skipped proactive auto-compact after repeated failures.",
                metadata={
                    "source": "runtime_pressure",
                    "strategy": "auto",
                    "trigger": "failure_circuit_breaker",
                    "failure_count": self._auto_compact_failure_count,
                    "max_failures": self.auto_compact_max_failures or 0,
                },
            )
        else:
            auto_compact_result = maybe_auto_compact_messages_with_status(
                processed,
                summarizer=request.model,
                threshold_tokens=self.auto_compact_threshold_tokens,
                keep_recent_messages=self.keep_recent_messages,
                assist_context=session_memory_assist,
                state=request.state,
                ptl_retry_limit=self.auto_compact_ptl_retry_limit,
                hook_context=context,
            )
            processed = auto_compact_result.messages
            if auto_compact_result.compacted:
                self._reset_auto_compact_failure_count()
                _emit_runtime_pressure_event(
                    request,
                    kind="auto_compact",
                    message="Runtime pressure middleware proactively compacted live history.",
                    metadata={
                        "source": "runtime_pressure",
                        "strategy": "auto",
                        "used_session_memory_assist": session_memory_assist is not None,
                        "restored_path_count": _restored_path_count(processed),
                    },
                )
            elif auto_compact_result.failed:
                self._increment_auto_compact_failure_count()
        active_request = (
            request
            if processed == list(request.messages)
            else request.override(messages=cast(list[Any], processed))
        )
        try:
            return handler(active_request)
        except Exception as exc:
            if not is_prompt_too_long_error(exc):
                raise
            drained = drain_collapse_projection_messages(active_request.messages)
            if drained != list(active_request.messages):
                _emit_runtime_pressure_event(
                    request,
                    kind="context_collapse",
                    message="Runtime pressure middleware drained collapse projection before reactive compact.",
                    metadata={
                        "source": "runtime_pressure",
                        "strategy": "context_collapse",
                        "trigger": "overflow_drain",
                        "drained_summaries": _drained_collapse_summary_count(
                            active_request.messages
                        ),
                    },
                )
                drained_request = active_request.override(messages=cast(list[Any], drained))
                try:
                    return handler(drained_request)
                except Exception as drained_exc:
                    if not is_prompt_too_long_error(drained_exc):
                        raise
                    active_request = drained_request
            compacted = reactive_compact_messages(
                active_request.messages,
                summarizer=request.model,
                keep_recent_messages=self.keep_recent_messages,
                assist_context=_session_memory_assist_text(
                    active_request.state, active_request.messages
                ),
                state=active_request.state,
            )
            if compacted == list(active_request.messages):
                raise
            _emit_runtime_pressure_event(
                request,
                kind="reactive_compact",
                message="Runtime pressure middleware retried with reactive compact.",
                metadata={
                    "source": "runtime_pressure",
                    "strategy": "reactive",
                    "used_session_memory_assist": _session_memory_assist_text(
                        active_request.state, active_request.messages
                    )
                    is not None,
                    "restored_path_count": _restored_path_count(compacted),
                },
            )
            return handler(active_request.override(messages=cast(list[Any], compacted)))

    def _should_skip_auto_compact(self) -> bool:
        return (
            self.auto_compact_max_failures is not None
            and self._auto_compact_failure_count >= self.auto_compact_max_failures
        )

    def _increment_auto_compact_failure_count(self) -> None:
        if self.auto_compact_max_failures is None:
            return
        object.__setattr__(
            self,
            "_auto_compact_failure_count",
            self._auto_compact_failure_count + 1,
        )

    def _reset_auto_compact_failure_count(self) -> None:
        if self._auto_compact_failure_count == 0:
            return
        object.__setattr__(self, "_auto_compact_failure_count", 0)


def _eligible_tool_calls(
    messages: Sequence[BaseMessage], *, registry: CapabilityRegistry
) -> set[str]:
    eligible: set[str] = set()
    for message in messages:
        if not isinstance(message, AIMessage):
            continue
        for call in message.tool_calls:
            tool_name = call.get("name")
            tool_call_id = call.get("id")
            if not isinstance(tool_name, str) or not isinstance(tool_call_id, str):
                continue
            capability = registry.get(tool_name)
            if capability is not None and capability.microcompact_eligible:
                eligible.add(tool_call_id)
    return eligible


def _is_compactable_tool_result(
    message: BaseMessage,
    *,
    eligible_tool_calls: set[str],
    min_content_chars: int,
) -> bool:
    if not isinstance(message, ToolMessage):
        return False
    if message.status != "success":
        return False
    if message.tool_call_id not in eligible_tool_calls:
        return False
    return len(str(message.content)) > min_content_chars


def _microcompacted_content(message: ToolMessage) -> str:
    artifact = message.artifact if isinstance(message.artifact, dict) else {}
    path = artifact.get("path")
    if isinstance(path, str) and path.strip():
        return f"{MICROCOMPACT_CLEARED_MESSAGE} Full output remains available at: {path.strip()}"
    return MICROCOMPACT_CLEARED_MESSAGE


def _token_budget_indexes_to_clear(
    messages: Sequence[BaseMessage],
    *,
    compactable_indexes: Sequence[int],
    protect_recent_tokens: int,
) -> list[int]:
    protected_indexes: set[int] = set()
    remaining_tokens = protect_recent_tokens
    for index in reversed(compactable_indexes):
        message_tokens = _estimate_message_tokens(messages[index])
        if not protected_indexes:
            protected_indexes.add(index)
            remaining_tokens = max(0, remaining_tokens - message_tokens)
            continue
        if message_tokens > remaining_tokens:
            break
        protected_indexes.add(index)
        remaining_tokens -= message_tokens
    return [index for index in compactable_indexes if index not in protected_indexes]


def _is_main_runtime_context(
    context: object,
    *,
    main_entrypoint: str,
    main_agent_name: str,
) -> bool:
    return (
        getattr(context, "entrypoint", None) == main_entrypoint
        and getattr(context, "agent_name", None) == main_agent_name
    )


def _latest_assistant_timestamp(messages: Sequence[BaseMessage]) -> datetime | None:
    for message in reversed(messages):
        if not isinstance(message, AIMessage):
            continue
        timestamp = _message_timestamp(message)
        if timestamp is not None:
            return timestamp
    return None


def _message_timestamp(message: BaseMessage) -> datetime | None:
    for metadata in (message.additional_kwargs, message.response_metadata):
        for key in ("timestamp", "created_at", "createdAt"):
            value = metadata.get(key)
            if isinstance(value, datetime):
                return _ensure_aware_datetime(value)
            if isinstance(value, str):
                parsed = _parse_datetime(value)
                if parsed is not None:
                    return parsed
    return None


def _parse_datetime(value: str) -> datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return _ensure_aware_datetime(datetime.fromisoformat(normalized))
    except ValueError:
        return None


def _ensure_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def snip_messages(
    messages: Sequence[BaseMessage],
    *,
    threshold_tokens: int | None,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES_AFTER_SNIP,
) -> list[BaseMessage]:
    if threshold_tokens is None:
        return list(messages)
    if threshold_tokens < 1:
        raise ValueError("threshold_tokens must be positive")
    if keep_recent_messages < 0:
        raise ValueError("keep_recent_messages must be non-negative")
    clean_messages = [
        message.model_copy(deep=True)
        for message in messages
        if not _is_live_pressure_artifact_message(message)
    ]
    if estimate_message_tokens(clean_messages) < threshold_tokens:
        return list(messages)

    keep_start = _adjust_keep_start_for_live_tool_pairs(
        clean_messages,
        max(0, len(clean_messages) - keep_recent_messages),
    )
    preserved_tail = clean_messages[keep_start:]
    hidden_count = keep_start
    if hidden_count <= 0:
        return list(messages)
    return [
        SystemMessage(
            content=(
                f"{LIVE_SNIP_BOUNDARY_PREFIX}: "
                f"original_messages={len(clean_messages)}; "
                f"hidden_messages={hidden_count}; "
                f"kept_messages={len(preserved_tail)}"
            )
        ),
        *preserved_tail,
    ]


def maybe_collapse_messages(
    messages: Sequence[BaseMessage],
    *,
    summarizer: Any,
    threshold_tokens: int | None,
    context_window_tokens: int | None = None,
    trigger_ratio: float | None = None,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES_AFTER_COLLAPSE,
    assist_context: str | None = None,
) -> list[BaseMessage]:
    if threshold_tokens is None and (
        context_window_tokens is None or trigger_ratio is None
    ):
        return list(messages)
    if threshold_tokens is not None and threshold_tokens < 1:
        raise ValueError("threshold_tokens must be positive")
    if context_window_tokens is not None and context_window_tokens < 1:
        raise ValueError("context_window_tokens must be positive")
    if trigger_ratio is not None and not 0 <= trigger_ratio <= 1:
        raise ValueError("trigger_ratio must be between 0 and 1")
    if keep_recent_messages < 0:
        raise ValueError("keep_recent_messages must be non-negative")
    if not _collapse_pressure_exceeded(
        messages,
        threshold_tokens=threshold_tokens,
        context_window_tokens=context_window_tokens,
        trigger_ratio=trigger_ratio,
    ):
        return list(messages)
    try:
        summary = generate_compact_summary(
            _messages_as_compact_dicts(messages),
            summarizer,
            assist_context=assist_context,
        )
    except Exception:
        return list(messages)
    return collapse_live_messages_with_summary(
        messages,
        summary=summary,
        keep_recent_messages=keep_recent_messages,
    )


def collapse_live_messages_with_summary(
    messages: Sequence[BaseMessage],
    *,
    summary: str,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES_AFTER_COLLAPSE,
) -> list[BaseMessage]:
    if not _has_collapsible_source(
        messages,
        keep_recent_messages=keep_recent_messages,
    ):
        return list(messages)
    return collapse_live_messages_with_result(
        messages,
        summary=summary,
        keep_recent_messages=keep_recent_messages,
    ).render()


def collapse_live_messages_with_result(
    messages: Sequence[BaseMessage],
    *,
    summary: str,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES_AFTER_COLLAPSE,
) -> LiveCompactionResult:
    if not messages:
        raise ValueError("messages are required for collapse")
    if keep_recent_messages < 0:
        raise ValueError("keep_recent_messages must be non-negative")
    if not summary.strip():
        raise ValueError("summary is required for collapse")

    clean_messages = [
        message.model_copy(deep=True)
        for message in messages
        if not _is_live_pressure_artifact_message(message)
    ]
    keep_start = _adjust_keep_start_for_live_tool_pairs(
        clean_messages,
        max(0, len(clean_messages) - keep_recent_messages),
    )
    collapsed_source = clean_messages[:keep_start]
    preserved_tail = clean_messages[keep_start:]
    if not collapsed_source:
        raise ValueError("collapse requires messages outside the preserved tail")
    restored_paths = _restored_persisted_output_paths(
        compacted_messages=collapsed_source,
        preserved_tail=preserved_tail,
    )

    restoration_messages: list[SystemMessage] = []
    if restored_paths:
        restoration_messages.append(
            SystemMessage(
                content=(
                    f"{LIVE_COMPACT_RESTORATION_PREFIX}\n"
                    + "\n".join(f"- {path}" for path in restored_paths)
                )
            )
        )
    result = LiveCompactionResult(
        boundary_message=SystemMessage(
            content=(
                f"{LIVE_COLLAPSE_BOUNDARY_PREFIX}: "
                f"original_messages={len(clean_messages)}; "
                f"collapsed_messages={len(collapsed_source)}; "
                f"kept_messages={len(preserved_tail)}"
            )
        ),
        summary_message=HumanMessage(
            content=f"{LIVE_COLLAPSE_SUMMARY_PREFIX}\n\nSummary:\n{summary.strip()}"
        ),
        restoration_messages=tuple(restoration_messages),
        preserved_tail=tuple(preserved_tail),
        trigger="context_collapse",
        original_token_estimate=estimate_message_tokens(clean_messages),
    )
    return _with_projected_token_estimate(result)


def _collapse_pressure_exceeded(
    messages: Sequence[BaseMessage],
    *,
    threshold_tokens: int | None,
    context_window_tokens: int | None,
    trigger_ratio: float | None,
) -> bool:
    estimated_tokens = estimate_message_tokens(messages)
    if threshold_tokens is not None and estimated_tokens >= threshold_tokens:
        return True
    if (
        context_window_tokens is not None
        and trigger_ratio is not None
        and estimated_tokens / context_window_tokens >= trigger_ratio
    ):
        return True
    return False


def maybe_auto_compact_messages(
    messages: Sequence[BaseMessage],
    *,
    summarizer: Any,
    threshold_tokens: int | None,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
    assist_context: str | None = None,
    state: Any = None,
    ptl_retry_limit: int = 0,
    hook_context: object | None = None,
) -> list[BaseMessage]:
    return maybe_auto_compact_messages_with_status(
        messages,
        summarizer=summarizer,
        threshold_tokens=threshold_tokens,
        keep_recent_messages=keep_recent_messages,
        assist_context=assist_context,
        state=state,
        ptl_retry_limit=ptl_retry_limit,
        hook_context=hook_context,
    ).messages


def maybe_auto_compact_messages_with_status(
    messages: Sequence[BaseMessage],
    *,
    summarizer: Any,
    threshold_tokens: int | None,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
    assist_context: str | None = None,
    state: Any = None,
    ptl_retry_limit: int = 0,
    hook_context: object | None = None,
) -> AutoCompactResult:
    if ptl_retry_limit < 0:
        raise ValueError("ptl_retry_limit must be non-negative")
    if threshold_tokens is None:
        return AutoCompactResult(messages=list(messages))
    if threshold_tokens < 1:
        raise ValueError("threshold_tokens must be positive")
    if estimate_message_tokens(messages) < threshold_tokens:
        return AutoCompactResult(messages=list(messages))
    summary_source = list(messages)
    pre_compact_context = _compact_hook_additional_context(
        hook_context,
        event="PreCompact",
        data={"trigger": "auto_compact", "message_count": len(summary_source)},
    )
    post_compact_context = _compact_hook_additional_context(
        hook_context,
        event="PostCompact",
        data={"trigger": "auto_compact", "message_count": len(messages)},
    )
    summarizer_assist = _combine_assist_context(assist_context, pre_compact_context)
    attempts = 0
    try:
        while True:
            try:
                summary = generate_compact_summary(
                    _messages_as_compact_dicts(summary_source),
                    summarizer,
                    assist_context=summarizer_assist,
                )
                break
            except Exception as exc:
                if not is_prompt_too_long_error(exc) or attempts >= ptl_retry_limit:
                    raise
                next_source = _drop_oldest_compact_source_group(summary_source)
                if not next_source or len(next_source) == len(summary_source):
                    raise
                summary_source = next_source
                attempts += 1
        _maybe_refresh_session_memory_state(state, messages=messages, summary=summary)
        compacted = compact_live_messages_with_summary(
            messages,
            summary=summary,
            keep_recent_messages=keep_recent_messages,
            state=state,
            post_compact_context=post_compact_context,
        )
    except Exception:
        return AutoCompactResult(messages=list(messages), attempted=True, failed=True)
    return AutoCompactResult(
        messages=compacted,
        attempted=True,
        compacted=True,
    )


def compact_live_messages_with_summary(
    messages: Sequence[BaseMessage],
    *,
    summary: str,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
    state: Any = None,
    post_compact_context: Sequence[str] = (),
) -> list[BaseMessage]:
    return compact_live_messages_with_result(
        messages,
        summary=summary,
        keep_recent_messages=keep_recent_messages,
        state=state,
        post_compact_context=post_compact_context,
    ).render()


def compact_live_messages_with_result(
    messages: Sequence[BaseMessage],
    *,
    summary: str,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
    state: Any = None,
    post_compact_context: Sequence[str] = (),
) -> LiveCompactionResult:
    if not messages:
        raise ValueError("messages are required for compaction")
    if keep_recent_messages < 0:
        raise ValueError("keep_recent_messages must be non-negative")
    if not summary.strip():
        raise ValueError("summary is required for compaction")

    clean_messages = [
        message.model_copy(deep=True)
        for message in messages
        if not _is_live_pressure_artifact_message(message)
    ]
    keep_start = _adjust_keep_start_for_live_tool_pairs(
        clean_messages,
        max(0, len(clean_messages) - keep_recent_messages),
    )
    preserved_tail = clean_messages[keep_start:]
    if not preserved_tail:
        raise ValueError("compaction requires a preserved tail")
    restored_paths = _restored_persisted_output_paths(
        compacted_messages=clean_messages[:keep_start],
        preserved_tail=preserved_tail,
    )

    restoration_messages: list[SystemMessage] = []
    if restored_paths:
        restoration_messages.append(
            SystemMessage(
                content=(
                    f"{LIVE_COMPACT_RESTORATION_PREFIX}\n"
                    + "\n".join(f"- {path}" for path in restored_paths)
                )
            )
        )
    restoration_messages.extend(_post_compact_state_restoration_messages(state))
    restoration_messages.extend(
        _post_compact_hook_restoration_messages(post_compact_context)
    )
    result = LiveCompactionResult(
        boundary_message=SystemMessage(
            content=(
                f"{LIVE_COMPACT_BOUNDARY_PREFIX}: "
                f"original_messages={len(clean_messages)}; "
                f"summarized_messages={keep_start}; "
                f"kept_messages={len(preserved_tail)}"
            )
        ),
        summary_message=HumanMessage(
            content=f"{LIVE_COMPACT_SUMMARY_PREFIX}\n\nSummary:\n{summary.strip()}"
        ),
        restoration_messages=tuple(restoration_messages),
        preserved_tail=tuple(preserved_tail),
        trigger="auto_compact",
        original_token_estimate=estimate_message_tokens(clean_messages),
    )
    return _with_projected_token_estimate(result)


def reactive_compact_messages(
    messages: Sequence[BaseMessage],
    *,
    summarizer: Any,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
    assist_context: str | None = None,
    state: Any = None,
) -> list[BaseMessage]:
    summary = generate_compact_summary(
        _messages_as_compact_dicts(messages),
        summarizer,
        assist_context=assist_context,
    )
    _maybe_refresh_session_memory_state(state, messages=messages, summary=summary)
    return compact_live_messages_with_summary(
        messages,
        summary=summary,
        keep_recent_messages=keep_recent_messages,
        state=state,
    )


def drain_collapse_projection_messages(
    messages: Sequence[BaseMessage],
) -> list[BaseMessage]:
    drained: list[BaseMessage] = []
    index = 0
    changed = False
    while index < len(messages):
        message = messages[index]
        if (
            isinstance(message, SystemMessage)
            and str(message.content).startswith(LIVE_COLLAPSE_BOUNDARY_PREFIX)
            and index + 1 < len(messages)
            and isinstance(messages[index + 1], HumanMessage)
            and str(messages[index + 1].content).startswith(
                LIVE_COLLAPSE_SUMMARY_PREFIX
            )
        ):
            drained.append(
                SystemMessage(
                    content=(
                        f"{LIVE_COLLAPSE_BOUNDARY_PREFIX}: "
                        "trigger=overflow_drain; drained_summaries=1"
                    )
                )
            )
            index += 2
            changed = True
            continue
        drained.append(message)
        index += 1
    return drained if changed else list(messages)


def estimate_message_tokens(messages: Sequence[BaseMessage]) -> int:
    return sum(_estimate_message_tokens(message) for message in messages)


def _estimate_message_tokens(message: BaseMessage) -> int:
    text = _message_text(message)
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _message_text(message: BaseMessage) -> str:
    if isinstance(message, AIMessage):
        parts = [str(message.content or "")]
        if message.tool_calls:
            parts.extend(
                f"{call.get('name', '')} {call.get('args', {})}" for call in message.tool_calls
            )
        return "\n".join(part for part in parts if part).strip()
    if isinstance(message, ToolMessage):
        return str(message.content or "").strip()
    return str(getattr(message, "content", "")).strip()


def _messages_as_compact_dicts(messages: Sequence[BaseMessage]) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    for message in messages:
        if isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            role = "user"
        rendered.append({"role": role, "content": _message_text(message)})
    return rendered


def _drop_oldest_compact_source_group(
    messages: Sequence[BaseMessage],
) -> list[BaseMessage]:
    if len(messages) <= 1:
        return []
    first = messages[0]
    drop_count = 1
    if isinstance(first, AIMessage):
        tool_call_ids = {
            str(call["id"])
            for call in first.tool_calls
            if isinstance(call.get("id"), str)
        }
        while drop_count < len(messages):
            candidate = messages[drop_count]
            if not isinstance(candidate, ToolMessage):
                break
            if candidate.tool_call_id not in tool_call_ids:
                break
            drop_count += 1
    elif isinstance(first, ToolMessage):
        while drop_count < len(messages) and isinstance(messages[drop_count], ToolMessage):
            drop_count += 1
    return list(messages[drop_count:])


def _has_collapsible_source(
    messages: Sequence[BaseMessage], *, keep_recent_messages: int
) -> bool:
    clean_messages = [
        message.model_copy(deep=True)
        for message in messages
        if not _is_live_pressure_artifact_message(message)
    ]
    keep_start = _adjust_keep_start_for_live_tool_pairs(
        clean_messages,
        max(0, len(clean_messages) - keep_recent_messages),
    )
    return keep_start > 0


def _is_live_compact_message(message: BaseMessage) -> bool:
    content = str(getattr(message, "content", ""))
    return content.startswith(LIVE_COMPACT_BOUNDARY_PREFIX) or content.startswith(
        LIVE_COMPACT_SUMMARY_PREFIX
    )


def _is_live_collapse_message(message: BaseMessage) -> bool:
    content = str(getattr(message, "content", ""))
    return content.startswith(LIVE_COLLAPSE_BOUNDARY_PREFIX) or content.startswith(
        LIVE_COLLAPSE_SUMMARY_PREFIX
    )


def _is_live_snip_message(message: BaseMessage) -> bool:
    content = str(getattr(message, "content", ""))
    return content.startswith(LIVE_SNIP_BOUNDARY_PREFIX)


def _is_live_pressure_artifact_message(message: BaseMessage) -> bool:
    return (
        _is_live_compact_message(message)
        or _is_live_collapse_message(message)
        or _is_live_snip_message(message)
        or str(getattr(message, "content", "")).startswith(LIVE_COMPACT_RESTORATION_PREFIX)
    )


def _adjust_keep_start_for_live_tool_pairs(
    messages: Sequence[BaseMessage], start_index: int
) -> int:
    if start_index <= 0 or start_index >= len(messages):
        return start_index

    needed_tool_calls = {
        message.tool_call_id
        for message in messages[start_index:]
        if isinstance(message, ToolMessage) and message.tool_call_id
    }
    if not needed_tool_calls:
        return start_index

    kept_tool_calls: set[str] = set()
    for message in messages[start_index:]:
        if isinstance(message, AIMessage):
            kept_tool_calls.update(
                str(call["id"])
                for call in message.tool_calls
                if isinstance(call.get("id"), str)
            )
    missing = needed_tool_calls - kept_tool_calls
    adjusted = start_index
    for index in range(start_index - 1, -1, -1):
        message = messages[index]
        if isinstance(message, AIMessage):
            tool_calls = {
                str(call["id"])
                for call in message.tool_calls
                if isinstance(call.get("id"), str)
            }
            if missing & tool_calls:
                adjusted = index
                missing -= tool_calls
            if not missing:
                break
    return adjusted


def _restored_persisted_output_paths(
    *,
    compacted_messages: Sequence[BaseMessage],
    preserved_tail: Sequence[BaseMessage],
) -> list[str]:
    preserved_paths = {
        path for message in preserved_tail if (path := _persisted_output_path(message)) is not None
    }
    restored: list[str] = []
    for message in compacted_messages:
        path = _persisted_output_path(message)
        if path is None or path in preserved_paths or path in restored:
            continue
        restored.append(path)
    return restored


def _post_compact_state_restoration_messages(state: Any) -> list[SystemMessage]:
    if not isinstance(state, dict):
        return []
    todos = state.get("todos")
    if not isinstance(todos, list):
        return []
    active_lines: list[str] = []
    for item in todos:
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        if status not in {"pending", "in_progress"}:
            continue
        content = item.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        active_lines.append(f"- [{status}] {content.strip()}")
        if len(active_lines) >= 6:
            break
    if not active_lines:
        return []
    return [
        SystemMessage(
            content=(
                "Post-compact restored state:\n"
                "Active todos:\n"
                + "\n".join(active_lines)
            )
        )
    ]


def _post_compact_hook_restoration_messages(
    contexts: Sequence[str],
) -> list[SystemMessage]:
    cleaned = tuple(_bounded_context_line(context) for context in contexts)
    lines = tuple(line for line in cleaned if line)
    if not lines:
        return []
    return [
        SystemMessage(
            content=(
                "PostCompact hook context:\n"
                + "\n".join(f"- {line}" for line in lines[:6])
            )
        )
    ]


def _compact_hook_additional_context(
    context: object | None,
    *,
    event: HookEventName,
    data: dict[str, object],
) -> tuple[str, ...]:
    if context is None:
        return ()
    outcome = dispatch_context_hook(
        context=context,
        session_id=str(getattr(context, "session_id", "unknown")),
        event=event,
        data=data,
    )
    if outcome is None or outcome.blocked:
        return ()
    return tuple(
        line
        for item in outcome.additional_context
        if (line := _bounded_context_line(item))
    )


def _combine_assist_context(
    assist_context: str | None, additions: Sequence[str]
) -> str | None:
    parts = [assist_context.strip()] if assist_context and assist_context.strip() else []
    parts.extend(additions)
    return "\n\n".join(parts) if parts else None


def _bounded_context_line(value: str) -> str:
    line = " ".join(value.strip().split())
    if not line:
        return ""
    return line[:1000]


def _persisted_output_path(message: BaseMessage) -> str | None:
    if not isinstance(message, ToolMessage):
        return None
    artifact = message.artifact if isinstance(message.artifact, dict) else None
    if artifact is None or artifact.get("kind") != "persisted_output":
        return None
    path = artifact.get("path")
    return path.strip() if isinstance(path, str) and path.strip() else None


def is_prompt_too_long_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(
        pattern in message
        for pattern in (
            "prompt too long",
            "context length",
            "maximum context length",
            "context window",
            "too many tokens",
            "token limit",
        )
    )


def _session_memory_assist_text(
    state: Any, messages: Sequence[BaseMessage]
) -> str | None:
    if not isinstance(state, dict):
        return None
    artifact = read_session_memory_artifact(state)
    if artifact is None:
        return None
    return compact_summary_assist_text(
        artifact,
        current_message_count=len(_messages_as_compact_dicts(messages)),
    )


def _maybe_refresh_session_memory_state(
    state: Any, *, messages: Sequence[BaseMessage], summary: str
) -> bool:
    if not isinstance(state, dict):
        return False
    return update_session_memory_from_summary(
        state,
        messages=_messages_as_compact_dicts(messages),
        summary=summary,
        source="live_compact",
    )


def _emit_runtime_pressure_event(
    request: ModelRequest,
    *,
    kind: str,
    message: str,
    metadata: dict[str, object],
) -> None:
    context = getattr(request.runtime, "context", None)
    sink = getattr(context, "event_sink", None)
    session_id = str(getattr(context, "session_id", "unknown"))
    runtime_event = RuntimeEvent(
        kind=kind,
        message=message,
        session_id=session_id,
        metadata=metadata,
    )
    emit = getattr(sink, "emit", None)
    if callable(emit):
        emit(runtime_event)
    append_runtime_event_evidence(context=context, event=runtime_event)


def _count_compacted_tool_results(messages: Sequence[BaseMessage]) -> int:
    return sum(
        1
        for message in messages
        if isinstance(message, ToolMessage)
        and str(message.content).startswith(MICROCOMPACT_CLEARED_MESSAGE)
    )


def _is_snipped(messages: Sequence[BaseMessage]) -> bool:
    return bool(messages) and isinstance(messages[0], SystemMessage) and str(
        messages[0].content
    ).startswith(LIVE_SNIP_BOUNDARY_PREFIX)


def _is_collapsed(messages: Sequence[BaseMessage]) -> bool:
    return bool(messages) and isinstance(messages[0], SystemMessage) and str(
        messages[0].content
    ).startswith(LIVE_COLLAPSE_BOUNDARY_PREFIX)


def _is_live_compacted(messages: Sequence[BaseMessage]) -> bool:
    return bool(messages) and isinstance(messages[0], SystemMessage) and str(
        messages[0].content
    ).startswith(LIVE_COMPACT_BOUNDARY_PREFIX)


def _snip_hidden_message_count(messages: Sequence[BaseMessage]) -> int:
    return _metadata_count_from_first_message(messages, "hidden_messages")


def _collapse_collapsed_message_count(messages: Sequence[BaseMessage]) -> int:
    return _metadata_count_from_first_message(messages, "collapsed_messages")


def _metadata_count_from_first_message(
    messages: Sequence[BaseMessage], field_name: str
) -> int:
    if not messages:
        return 0
    content = str(getattr(messages[0], "content", ""))
    marker = f"{field_name}="
    if marker not in content:
        return 0
    raw_value = content.split(marker, 1)[1].split(";", 1)[0].strip()
    try:
        return max(0, int(raw_value))
    except ValueError:
        return 0


def _restored_path_count(messages: Sequence[BaseMessage]) -> int:
    for message in messages:
        if isinstance(message, SystemMessage) and str(message.content).startswith(
            LIVE_COMPACT_RESTORATION_PREFIX
        ):
            return max(0, len(str(message.content).splitlines()) - 1)
    return 0


def _runtime_transcript_projection(
    request: ModelRequest,
) -> TranscriptProjection | None:
    context = getattr(request.runtime, "context", None)
    projection = getattr(context, "transcript_projection", None)
    return projection if isinstance(projection, TranscriptProjection) else None


def _projection_after_snip(
    messages: Sequence[BaseMessage],
    projection: TranscriptProjection | None,
    *,
    keep_recent_messages: int,
) -> TranscriptProjection | None:
    if projection is None or len(projection.entries) != len(messages):
        return projection
    clean_pairs = [
        (message, entry)
        for message, entry in zip(messages, projection.entries, strict=True)
        if not _is_live_pressure_artifact_message(message)
    ]
    clean_messages = [message for message, _entry in clean_pairs]
    clean_entries = [entry for _message, entry in clean_pairs]
    keep_start = _adjust_keep_start_for_live_tool_pairs(
        clean_messages,
        max(0, len(clean_messages) - keep_recent_messages),
    )
    if keep_start <= 0:
        return projection
    return TranscriptProjection(entries=((), *clean_entries[keep_start:]))


def _append_collapse_record(
    request: ModelRequest,
    *,
    source_messages: Sequence[BaseMessage],
    projection: TranscriptProjection | None,
    collapsed_messages: Sequence[BaseMessage],
    threshold_tokens: int | None,
    context_window_tokens: int | None,
    trigger_ratio: float | None,
    used_session_memory_assist: bool,
) -> bool:
    context = getattr(request.runtime, "context", None)
    session_context = getattr(context, "session_context", None)
    if not isinstance(session_context, SessionContext):
        return False
    if projection is None or len(projection.entries) != len(source_messages):
        return False
    collapsed_count = _collapse_collapsed_message_count(collapsed_messages)
    if collapsed_count <= 0:
        return False
    covered_message_ids = _covered_projection_ids_for_prefix(
        source_messages,
        projection,
        collapsed_count,
    )
    if not covered_message_ids:
        return False
    summary = _collapse_summary_text(collapsed_messages)
    if summary is None:
        return False
    pressure_metadata = _pressure_metadata(
        source_messages,
        context_window_tokens=context_window_tokens,
    )
    JsonlSessionStore(session_context.store_dir).append_collapse(
        session_context,
        trigger="threshold_tokens",
        summary=summary,
        start_message_id=covered_message_ids[0],
        end_message_id=covered_message_ids[-1],
        covered_message_ids=list(covered_message_ids),
        metadata={
            "source": "runtime_pressure",
            "strategy": "context_collapse",
            "estimated_token_count": estimate_message_tokens(source_messages),
            "threshold_tokens": threshold_tokens,
            "context_window_tokens": context_window_tokens,
            "trigger_ratio_percent": int(trigger_ratio * 100)
            if trigger_ratio is not None
            else None,
            "entrypoint": getattr(context, "entrypoint", None),
            "agent_name": getattr(context, "agent_name", None),
            "used_session_memory_assist": used_session_memory_assist,
            **pressure_metadata,
        },
    )
    return True


def _covered_projection_ids_for_prefix(
    messages: Sequence[BaseMessage],
    projection: TranscriptProjection,
    collapsed_count: int,
) -> tuple[str, ...]:
    covered: list[str] = []
    remaining = collapsed_count
    for message, entry in zip(messages, projection.entries, strict=True):
        if _is_live_pressure_artifact_message(message):
            continue
        covered.extend(entry)
        remaining -= 1
        if remaining <= 0:
            break
    return tuple(covered)


def _collapse_summary_text(messages: Sequence[BaseMessage]) -> str | None:
    if len(messages) < 2 or not isinstance(messages[1], HumanMessage):
        return None
    prefix = f"{LIVE_COLLAPSE_SUMMARY_PREFIX}\n\nSummary:\n"
    content = str(messages[1].content)
    if not content.startswith(prefix):
        return None
    summary = content[len(prefix) :].strip()
    return summary or None


def _pressure_metadata(
    messages: Sequence[BaseMessage],
    *,
    context_window_tokens: int | None,
) -> dict[str, int]:
    estimated_tokens = estimate_message_tokens(messages)
    metadata = {"estimated_token_count": estimated_tokens}
    if context_window_tokens is not None and context_window_tokens > 0:
        metadata["context_window_tokens"] = context_window_tokens
        metadata["estimated_token_ratio_percent"] = int(
            (estimated_tokens / context_window_tokens) * 100
        )
    return metadata


def _drained_collapse_summary_count(messages: Sequence[BaseMessage]) -> int:
    count = 0
    for index, message in enumerate(messages[:-1]):
        if (
            isinstance(message, SystemMessage)
            and str(message.content).startswith(LIVE_COLLAPSE_BOUNDARY_PREFIX)
            and isinstance(messages[index + 1], HumanMessage)
            and str(messages[index + 1].content).startswith(
                LIVE_COLLAPSE_SUMMARY_PREFIX
            )
        ):
            count += 1
    return count
