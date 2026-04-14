from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

SESSION_RECORD_VERSION = 1
MESSAGE_RECORD_TYPE = "message"
STATE_SNAPSHOT_RECORD_TYPE = "state_snapshot"
EVIDENCE_RECORD_TYPE = "evidence"
COMPACT_RECORD_TYPE = "compact"


def iso_timestamp_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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


@dataclass(frozen=True, slots=True)
class SessionEvidence:
    kind: str
    summary: str
    status: str
    created_at: str
    subject: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class SessionCompact:
    trigger: str
    summary: str
    created_at: str
    original_message_count: int
    summarized_message_count: int
    kept_message_count: int
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CompactedHistorySource:
    mode: Literal["raw", "compact"]
    reason: str
    compact_index: int | None = None


@dataclass(frozen=True, slots=True)
class LoadedSession:
    context: SessionContext
    history: list[dict[str, str]]
    compacted_history: list[dict[str, Any]]
    compacted_history_source: CompactedHistorySource
    state: dict[str, Any]
    evidence: list[SessionEvidence]
    compacts: list[SessionCompact]
    summary: SessionSummary


class SessionLoadError(RuntimeError):
    """Raised when a targeted session cannot be resumed from valid transcript records."""


def make_message_record(
    context: SessionContext,
    *,
    role: str,
    content: str,
    message_index: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_type": MESSAGE_RECORD_TYPE,
        "version": SESSION_RECORD_VERSION,
        "session_id": context.session_id,
        "timestamp": iso_timestamp_now(),
        "cwd": str(context.workdir),
        "role": role,
        "content": content,
    }
    if context.entrypoint:
        record["entrypoint"] = context.entrypoint
    if message_index is not None:
        record["message_index"] = message_index
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


def make_compact_record(
    context: SessionContext,
    *,
    trigger: str,
    summary: str,
    original_message_count: int,
    summarized_message_count: int,
    kept_message_count: int,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_type": COMPACT_RECORD_TYPE,
        "version": SESSION_RECORD_VERSION,
        "session_id": context.session_id,
        "timestamp": iso_timestamp_now(),
        "cwd": str(context.workdir),
        "trigger": trigger.strip(),
        "summary": summary.strip(),
        "original_message_count": original_message_count,
        "summarized_message_count": summarized_message_count,
        "kept_message_count": kept_message_count,
    }
    if context.entrypoint:
        record["entrypoint"] = context.entrypoint
    if metadata:
        record["metadata"] = metadata
    return record
