from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, cast

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from coding_deepgent.compact.summarizer import generate_compact_summary
from coding_deepgent.runtime.events import RuntimeEvent
from coding_deepgent.sessions.evidence_events import append_runtime_event_evidence
from coding_deepgent.sessions.session_memory import (
    compact_summary_assist_text,
    read_session_memory_artifact,
    update_session_memory_from_summary,
)
from coding_deepgent.tool_system.capabilities import CapabilityRegistry

MICROCOMPACT_CLEARED_MESSAGE = "[Old tool result content cleared]"
DEFAULT_KEEP_RECENT_TOOL_RESULTS = 3
DEFAULT_MICROCOMPACT_MIN_CONTENT_CHARS = 120
LIVE_COMPACT_BOUNDARY_PREFIX = "coding-deepgent live compact boundary"
LIVE_COMPACT_SUMMARY_PREFIX = "This session is being continued from a compacted live invocation."
LIVE_COMPACT_RESTORATION_PREFIX = "Restored persisted tool outputs:"
DEFAULT_AUTO_COMPACT_THRESHOLD_TOKENS = 8000
DEFAULT_KEEP_RECENT_MESSAGES = 4


def microcompact_messages(
    messages: Sequence[BaseMessage],
    *,
    registry: CapabilityRegistry,
    keep_recent_tool_results: int = DEFAULT_KEEP_RECENT_TOOL_RESULTS,
    min_content_chars: int = DEFAULT_MICROCOMPACT_MIN_CONTENT_CHARS,
) -> list[BaseMessage]:
    if keep_recent_tool_results < 0:
        raise ValueError("keep_recent_tool_results must be non-negative")

    eligible_tool_calls = _eligible_tool_calls(messages, registry=registry)
    if not eligible_tool_calls:
        return list(messages)

    compactable_indexes = [
        index
        for index, message in enumerate(messages)
        if _is_compactable_tool_result(
            message,
            eligible_tool_calls=eligible_tool_calls,
            min_content_chars=min_content_chars,
        )
    ]
    if len(compactable_indexes) <= keep_recent_tool_results:
        return list(messages)

    rewritten = list(messages)
    for index in compactable_indexes[:-keep_recent_tool_results]:
        message = rewritten[index]
        if isinstance(message, ToolMessage):
            rewritten[index] = message.model_copy(
                update={"content": _microcompacted_content(message)}
            )
    return rewritten


@dataclass(frozen=True, slots=True)
class RuntimePressureMiddleware(AgentMiddleware):
    registry: CapabilityRegistry
    keep_recent_tool_results: int = DEFAULT_KEEP_RECENT_TOOL_RESULTS
    min_content_chars: int = DEFAULT_MICROCOMPACT_MIN_CONTENT_CHARS
    auto_compact_threshold_tokens: int | None = DEFAULT_AUTO_COMPACT_THRESHOLD_TOKENS
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        processed = microcompact_messages(
            request.messages,
            registry=self.registry,
            keep_recent_tool_results=self.keep_recent_tool_results,
            min_content_chars=self.min_content_chars,
        )
        if processed != list(request.messages):
            _emit_runtime_pressure_event(
                request,
                kind="microcompact",
                message="Runtime pressure middleware microcompacted older tool results.",
                metadata={
                    "source": "runtime_pressure",
                    "strategy": "microcompact",
                    "cleared_tool_results": _count_compacted_tool_results(processed),
                },
            )
        session_memory_assist = _session_memory_assist_text(request.state, processed)
        processed = maybe_auto_compact_messages(
            processed,
            summarizer=request.model,
            threshold_tokens=self.auto_compact_threshold_tokens,
            keep_recent_messages=self.keep_recent_messages,
            assist_context=session_memory_assist,
            state=request.state,
        )
        if _is_live_compacted(processed):
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


def maybe_auto_compact_messages(
    messages: Sequence[BaseMessage],
    *,
    summarizer: Any,
    threshold_tokens: int | None,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
    assist_context: str | None = None,
    state: Any = None,
) -> list[BaseMessage]:
    if threshold_tokens is None:
        return list(messages)
    if threshold_tokens < 1:
        raise ValueError("threshold_tokens must be positive")
    if estimate_message_tokens(messages) < threshold_tokens:
        return list(messages)
    try:
        summary = generate_compact_summary(
            _messages_as_compact_dicts(messages),
            summarizer,
            assist_context=assist_context,
        )
    except Exception:
        return list(messages)
    _maybe_refresh_session_memory_state(state, messages=messages, summary=summary)
    return compact_live_messages_with_summary(
        messages,
        summary=summary,
        keep_recent_messages=keep_recent_messages,
    )


def compact_live_messages_with_summary(
    messages: Sequence[BaseMessage],
    *,
    summary: str,
    keep_recent_messages: int = DEFAULT_KEEP_RECENT_MESSAGES,
) -> list[BaseMessage]:
    if not messages:
        raise ValueError("messages are required for compaction")
    if keep_recent_messages < 0:
        raise ValueError("keep_recent_messages must be non-negative")
    if not summary.strip():
        raise ValueError("summary is required for compaction")

    clean_messages = [
        message.model_copy(deep=True)
        for message in messages
        if not _is_live_compact_message(message)
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

    compacted_messages: list[BaseMessage] = [
        SystemMessage(
            content=(
                f"{LIVE_COMPACT_BOUNDARY_PREFIX}: "
                f"original_messages={len(clean_messages)}; "
                f"summarized_messages={keep_start}; "
                f"kept_messages={len(preserved_tail)}"
            )
        ),
        HumanMessage(
            content=f"{LIVE_COMPACT_SUMMARY_PREFIX}\n\nSummary:\n{summary.strip()}"
        ),
    ]
    if restored_paths:
        compacted_messages.append(
            SystemMessage(
                content=(
                    f"{LIVE_COMPACT_RESTORATION_PREFIX}\n"
                    + "\n".join(f"- {path}" for path in restored_paths)
                )
            )
        )
    compacted_messages.extend(preserved_tail)
    return compacted_messages


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
    )


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


def _is_live_compact_message(message: BaseMessage) -> bool:
    content = str(getattr(message, "content", ""))
    return content.startswith(LIVE_COMPACT_BOUNDARY_PREFIX) or content.startswith(
        LIVE_COMPACT_SUMMARY_PREFIX
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


def _is_live_compacted(messages: Sequence[BaseMessage]) -> bool:
    return bool(messages) and isinstance(messages[0], SystemMessage) and str(
        messages[0].content
    ).startswith(LIVE_COMPACT_BOUNDARY_PREFIX)


def _restored_path_count(messages: Sequence[BaseMessage]) -> int:
    for message in messages:
        if isinstance(message, SystemMessage) and str(message.content).startswith(
            LIVE_COMPACT_RESTORATION_PREFIX
        ):
            return max(0, len(str(message.content).splitlines()) - 1)
    return 0
