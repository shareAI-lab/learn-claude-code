from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .contributions import (
    CompactAssistContribution,
    CompactSummaryUpdateContribution,
    RecoveryBriefContribution,
    RecoveryBriefSection,
    RuntimeStateContribution,
)
from .records import LoadedSession, SessionMessage, iso_timestamp_now

SESSION_MEMORY_STATE_KEY = "session_memory"
DEFAULT_SESSION_MEMORY_UPDATE_MESSAGE_DELTA = 4
DEFAULT_SESSION_MEMORY_UPDATE_TOKEN_DELTA = 5000
DEFAULT_SESSION_MEMORY_UPDATE_TOOL_CALL_DELTA = 3
SessionMemoryStatus = Literal["current", "stale"]


@dataclass(frozen=True, slots=True)
class SessionMemoryMetrics:
    message_count: int
    estimated_token_count: int
    tool_call_count: int


class SessionMemoryArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., min_length=1, max_length=4000)
    source: str = Field(default="manual", min_length=1, max_length=64)
    message_count: int = Field(default=0, ge=0)
    updated_at: str = Field(..., min_length=1)
    token_count: int | None = Field(default=None, ge=0)
    tool_call_count: int | None = Field(default=None, ge=0)

    @field_validator("content", "source", "updated_at")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value required")
        return value


def read_session_memory_artifact(
    state: Mapping[str, Any],
) -> SessionMemoryArtifact | None:
    value = state.get(SESSION_MEMORY_STATE_KEY)
    if not isinstance(value, dict):
        return None
    try:
        return SessionMemoryArtifact.model_validate(value)
    except ValidationError:
        return None


def write_session_memory_artifact(
    state: MutableMapping[str, Any],
    *,
    content: str,
    message_count: int,
    source: str = "manual",
    token_count: int | None = None,
    tool_call_count: int | None = None,
) -> SessionMemoryArtifact:
    artifact = SessionMemoryArtifact(
        content=content,
        source=source,
        message_count=message_count,
        updated_at=iso_timestamp_now(),
        token_count=token_count,
        tool_call_count=tool_call_count,
    )
    state[SESSION_MEMORY_STATE_KEY] = artifact.model_dump(exclude_none=True)
    return artifact


def session_memory_status(
    artifact: SessionMemoryArtifact,
    *,
    current_message_count: int,
) -> SessionMemoryStatus:
    return "stale" if artifact.message_count < current_message_count else "current"


def compact_summary_assist_text(
    artifact: SessionMemoryArtifact | None,
    *,
    current_message_count: int,
) -> str | None:
    if artifact is None:
        return None
    if session_memory_status(artifact, current_message_count=current_message_count) != "current":
        return None
    return (
        "Session memory artifact:\n"
        f"{artifact.content}\n\n"
        "Use it as a bounded continuity aid. If it conflicts with the transcript, "
        "prefer the transcript."
    )


def render_session_memory_line(
    artifact: SessionMemoryArtifact,
    *,
    current_message_count: int,
) -> str:
    status = session_memory_status(
        artifact, current_message_count=current_message_count
    )
    return (
        f"- [{status}] {artifact.content} "
        f"(source={artifact.source}; messages={artifact.message_count})"
    )


def should_refresh_session_memory(
    state: Mapping[str, Any],
    *,
    current_message_count: int,
    current_token_count: int = 0,
    current_tool_call_count: int = 0,
    min_message_delta: int = DEFAULT_SESSION_MEMORY_UPDATE_MESSAGE_DELTA,
    min_token_delta: int = DEFAULT_SESSION_MEMORY_UPDATE_TOKEN_DELTA,
    min_tool_call_delta: int = DEFAULT_SESSION_MEMORY_UPDATE_TOOL_CALL_DELTA,
) -> bool:
    artifact = read_session_memory_artifact(state)
    if artifact is None:
        return True
    if min_message_delta < 1 or min_token_delta < 1 or min_tool_call_delta < 1:
        raise ValueError("session memory thresholds must be at least 1")

    message_delta = current_message_count - artifact.message_count
    token_delta = current_token_count - (artifact.token_count or 0)
    tool_call_delta = current_tool_call_count - (artifact.tool_call_count or 0)
    return (
        message_delta >= min_message_delta
        or token_delta >= min_token_delta
        or tool_call_delta >= min_tool_call_delta
    )


def session_memory_metrics(
    messages: Sequence[dict[str, Any] | SessionMessage],
) -> SessionMemoryMetrics:
    return SessionMemoryMetrics(
        message_count=len(messages),
        estimated_token_count=sum(_estimated_message_tokens(message) for message in messages),
        tool_call_count=sum(_message_tool_call_count(message) for message in messages),
    )


def _estimated_message_tokens(message: dict[str, Any] | SessionMessage) -> int:
    text = _message_text(message)
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _message_text(message: dict[str, Any] | SessionMessage) -> str:
    if isinstance(message, SessionMessage):
        content = message.content
    else:
        content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
            elif isinstance(block.get("content"), str):
                parts.append(str(block["content"]))
        return "\n".join(parts)
    return str(content)


def _message_tool_call_count(message: dict[str, Any] | SessionMessage) -> int:
    if isinstance(message, SessionMessage):
        content = message.content
        tool_calls: Any = None
    else:
        content = message.get("content", "")
        tool_calls = message.get("tool_calls")
    count = 0
    if isinstance(content, list):
        count += sum(
            1
            for block in content
            if isinstance(block, dict) and block.get("type") == "tool_use"
        )
    if isinstance(tool_calls, list):
        count += len(tool_calls)
    return count


def runtime_state_contribution() -> RuntimeStateContribution:
    return RuntimeStateContribution(
        key=SESSION_MEMORY_STATE_KEY,
        coerce=lambda state: (
            artifact.model_dump(exclude_none=True)
            if (artifact := read_session_memory_artifact(state)) is not None
            else None
        ),
    )


def recovery_brief_contribution() -> RecoveryBriefContribution:
    def render(loaded_session: LoadedSession) -> RecoveryBriefSection:
        artifact = read_session_memory_artifact(loaded_session.state)
        lines = (
            ("- none",)
            if artifact is None
            else (
                render_session_memory_line(
                    artifact,
                    current_message_count=loaded_session.summary.message_count,
                ),
            )
        )
        return RecoveryBriefSection(title="Current-session memory:", lines=lines)

    return RecoveryBriefContribution(name=SESSION_MEMORY_STATE_KEY, render=render)


def compact_assist_contribution() -> CompactAssistContribution:
    def render(loaded_session: LoadedSession) -> str | None:
        return compact_summary_assist_text(
            read_session_memory_artifact(loaded_session.state),
            current_message_count=loaded_session.summary.message_count,
        )

    return CompactAssistContribution(name=SESSION_MEMORY_STATE_KEY, render=render)


def compact_summary_update_contribution() -> CompactSummaryUpdateContribution:
    def update(loaded_session: LoadedSession, summary: str) -> bool:
        return update_session_memory_from_summary(
            loaded_session.state,
            messages=loaded_session.history,
            summary=summary,
            source="generated_compact",
        )

    return CompactSummaryUpdateContribution(
        name=SESSION_MEMORY_STATE_KEY,
        update=update,
    )


def update_session_memory_from_summary(
    state: MutableMapping[str, Any],
    *,
    messages: Sequence[dict[str, Any] | SessionMessage],
    summary: str,
    source: str,
) -> bool:
    metrics = session_memory_metrics(messages)
    if not should_refresh_session_memory(
        state,
        current_message_count=metrics.message_count,
        current_token_count=metrics.estimated_token_count,
        current_tool_call_count=metrics.tool_call_count,
    ):
        return False
    write_session_memory_artifact(
        state,
        content=summary,
        message_count=metrics.message_count,
        token_count=metrics.estimated_token_count,
        tool_call_count=metrics.tool_call_count,
        source=source,
    )
    return True
