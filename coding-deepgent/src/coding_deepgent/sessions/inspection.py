from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .compression_view import (
    CompressionTimelineEvent,
    ProjectionMessageView,
    ProjectionMode,
    RawTranscriptMessageView,
    build_compression_view,
)
from .records import LoadedSession
from .resume import build_recovery_brief, render_recovery_brief
from .session_memory import (
    read_session_memory_artifact,
    session_memory_metrics,
    session_memory_status,
)

SessionMemoryInspectStatus = Literal["missing", "current", "stale"]


@dataclass(frozen=True, slots=True)
class SessionMemoryInspect:
    status: SessionMemoryInspectStatus
    source: str | None
    content: str | None
    artifact_message_count: int | None
    current_message_count: int
    estimated_token_count: int
    tool_call_count: int


@dataclass(frozen=True, slots=True)
class SessionInspectView:
    session_id: str
    workdir: str
    transcript_path: str
    created_at: str | None
    updated_at: str | None
    message_count: int
    evidence_count: int
    compact_count: int
    collapse_count: int
    sidechain_count: int
    recovery_brief: str
    projection_mode: ProjectionMode
    raw_messages: tuple[RawTranscriptMessageView, ...]
    model_projection: tuple[ProjectionMessageView, ...]
    timeline: tuple[CompressionTimelineEvent, ...]
    session_memory: SessionMemoryInspect

    @property
    def visible_raw_count(self) -> int:
        return sum(1 for message in self.raw_messages if message.model_visible)

    @property
    def hidden_raw_count(self) -> int:
        return len(self.raw_messages) - self.visible_raw_count


def build_session_inspect_view(
    loaded: LoadedSession,
    *,
    projection_mode: ProjectionMode = "selected",
) -> SessionInspectView:
    compression = build_compression_view(loaded, projection_mode=projection_mode)
    return SessionInspectView(
        session_id=loaded.summary.session_id,
        workdir=str(loaded.summary.workdir),
        transcript_path=str(loaded.summary.transcript_path),
        created_at=loaded.summary.created_at,
        updated_at=loaded.summary.updated_at,
        message_count=loaded.summary.message_count,
        evidence_count=loaded.summary.evidence_count,
        compact_count=loaded.summary.compact_count,
        collapse_count=loaded.summary.collapse_count,
        sidechain_count=len(loaded.sidechain_messages),
        recovery_brief=render_recovery_brief(build_recovery_brief(loaded)),
        projection_mode=compression.projection_mode,
        raw_messages=compression.raw_messages,
        model_projection=compression.model_projection,
        timeline=compression.timeline,
        session_memory=_session_memory_inspect(loaded),
    )


def _session_memory_inspect(loaded: LoadedSession) -> SessionMemoryInspect:
    metrics = session_memory_metrics(loaded.history)
    artifact = read_session_memory_artifact(loaded.state)
    if artifact is None:
        return SessionMemoryInspect(
            status="missing",
            source=None,
            content=None,
            artifact_message_count=None,
            current_message_count=metrics.message_count,
            estimated_token_count=metrics.estimated_token_count,
            tool_call_count=metrics.tool_call_count,
        )
    return SessionMemoryInspect(
        status=session_memory_status(
            artifact,
            current_message_count=metrics.message_count,
            current_token_count=metrics.estimated_token_count,
            current_tool_call_count=metrics.tool_call_count,
        ),
        source=artifact.source,
        content=artifact.content,
        artifact_message_count=artifact.message_count,
        current_message_count=metrics.message_count,
        estimated_token_count=metrics.estimated_token_count,
        tool_call_count=metrics.tool_call_count,
    )
