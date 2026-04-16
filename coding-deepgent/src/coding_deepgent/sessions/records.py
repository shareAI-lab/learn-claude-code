from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

SESSION_RECORD_VERSION = 1
MESSAGE_RECORD_TYPE = "message"
TRANSCRIPT_EVENT_RECORD_TYPE = "transcript_event"
STATE_SNAPSHOT_RECORD_TYPE = "state_snapshot"
EVIDENCE_RECORD_TYPE = "evidence"
COMPACT_EVENT_KIND = "compact"
COLLAPSE_EVENT_KIND = "collapse"


def iso_timestamp_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def message_id_for_index(index: int) -> str:
    if index < 0:
        raise ValueError("message index must be non-negative")
    return f"msg-{index:06d}"


@dataclass(frozen=True, slots=True)
class SessionContext:
    session_id: str
    workdir: Path
    store_dir: Path
    transcript_path: Path
    entrypoint: str | None = None


@dataclass(frozen=True, slots=True)
class SessionSummary:
    session_id: str
    workdir: Path
    transcript_path: Path
    created_at: str | None
    updated_at: str | None
    first_prompt: str | None
    message_count: int
    evidence_count: int = 0
    compact_count: int = 0
    collapse_count: int = 0


@dataclass(frozen=True, slots=True)
class SessionEvidence:
    kind: str
    summary: str
    status: str
    created_at: str
    subject: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class SessionMessage:
    message_id: str
    created_at: str
    role: str
    content: str
    metadata: dict[str, Any] | None = None

    def as_conversation_dict(self) -> dict[str, Any]:
        message: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }
        if self.metadata is not None:
            message["metadata"] = deepcopy(self.metadata)
        return message


@dataclass(frozen=True, slots=True)
class TranscriptProjection:
    entries: tuple[tuple[str, ...], ...]

    def covered_message_ids_for_prefix(self, count: int) -> tuple[str, ...]:
        if count <= 0:
            return ()
        covered: list[str] = []
        for entry in self.entries[:count]:
            covered.extend(entry)
        return tuple(covered)


@dataclass(frozen=True, slots=True)
class MessageReference:
    start_message_id: str
    end_message_id: str
    covered_message_ids: tuple[str, ...] | None = None

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "start_message_id": self.start_message_id,
            "end_message_id": self.end_message_id,
        }
        if self.covered_message_ids:
            payload["covered_message_ids"] = list(self.covered_message_ids)
        return payload


@dataclass(frozen=True, slots=True)
class SessionCompact:
    trigger: str
    summary: str
    created_at: str
    start_message_id: str
    end_message_id: str
    covered_message_ids: tuple[str, ...] | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class SessionCollapse:
    trigger: str
    summary: str
    created_at: str
    start_message_id: str
    end_message_id: str
    covered_message_ids: tuple[str, ...] | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CompactedHistorySource:
    mode: Literal["raw", "compact"]
    reason: str
    compact_index: int | None = None


@dataclass(frozen=True, slots=True)
class CollapsedHistorySource:
    mode: Literal["raw", "collapse"]
    reason: str
    collapse_index: int | None = None


@dataclass(frozen=True, slots=True)
class LoadedSession:
    context: SessionContext
    history: list[SessionMessage]
    compacted_history: list[dict[str, Any]]
    compacted_history_source: CompactedHistorySource
    collapsed_history: list[dict[str, Any]]
    collapsed_history_source: CollapsedHistorySource
    state: dict[str, Any]
    evidence: list[SessionEvidence]
    compacts: list[SessionCompact]
    summary: SessionSummary
    collapses: list[SessionCollapse] = field(default_factory=list)


class SessionLoadError(RuntimeError):
    """Raised when a targeted session cannot be resumed from valid transcript records."""


def make_message_record(
    context: SessionContext,
    *,
    message_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_type": MESSAGE_RECORD_TYPE,
        "version": SESSION_RECORD_VERSION,
        "session_id": context.session_id,
        "timestamp": iso_timestamp_now(),
        "message_id": message_id,
        "role": role,
        "content": content,
    }
    if metadata:
        record["metadata"] = metadata
    return record


def make_state_snapshot_record(
    context: SessionContext,
    *,
    state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "record_type": STATE_SNAPSHOT_RECORD_TYPE,
        "version": SESSION_RECORD_VERSION,
        "session_id": context.session_id,
        "timestamp": iso_timestamp_now(),
        "cwd": str(context.workdir),
        "state": state,
    }


def make_evidence_record(
    context: SessionContext,
    *,
    kind: str,
    summary: str,
    status: str = "recorded",
    subject: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_type": EVIDENCE_RECORD_TYPE,
        "version": SESSION_RECORD_VERSION,
        "session_id": context.session_id,
        "timestamp": iso_timestamp_now(),
        "cwd": str(context.workdir),
        "kind": kind.strip(),
        "summary": summary.strip(),
        "status": status.strip(),
    }
    if subject:
        record["subject"] = subject.strip()
    if metadata:
        record["metadata"] = metadata
    return record


def make_transcript_event_record(
    context: SessionContext,
    *,
    event_kind: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "record_type": TRANSCRIPT_EVENT_RECORD_TYPE,
        "version": SESSION_RECORD_VERSION,
        "session_id": context.session_id,
        "timestamp": iso_timestamp_now(),
        "event_kind": event_kind,
        "payload": payload,
    }
