from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

from coding_deepgent.compact import compact_messages_with_summary
from coding_deepgent.runtime import default_runtime_state

from .records import (
    COMPACT_RECORD_TYPE,
    EVIDENCE_RECORD_TYPE,
    LoadedSession,
    MESSAGE_RECORD_TYPE,
    SESSION_RECORD_VERSION,
    STATE_SNAPSHOT_RECORD_TYPE,
    SessionContext,
    SessionCompact,
    SessionEvidence,
    SessionLoadError,
    SessionSummary,
    make_compact_record,
    make_evidence_record,
    make_message_record,
    make_state_snapshot_record,
)


class JsonlSessionStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = (
            base_dir or Path.home() / ".coding-deepgent" / "sessions"
        ).expanduser()

    def create_session(
        self,
        *,
        workdir: Path,
        session_id: str | None = None,
        entrypoint: str | None = None,
    ) -> SessionContext:
        context = self._context_for(
            workdir=workdir,
            session_id=session_id or str(uuid.uuid4()),
            entrypoint=entrypoint,
        )
        context.transcript_path.parent.mkdir(parents=True, exist_ok=True)
        context.transcript_path.touch(exist_ok=True)
        return context

    def transcript_path_for(self, *, session_id: str, workdir: Path) -> Path:
        normalized_workdir = workdir.expanduser().resolve()
        return self.workspace_dir_for(normalized_workdir) / f"{session_id}.jsonl"

    def workspace_dir_for(self, workdir: Path) -> Path:
        normalized_workdir = workdir.expanduser().resolve()
        digest = hashlib.sha1(str(normalized_workdir).encode("utf-8")).hexdigest()[:16]
        return self.base_dir / digest

    def append_message(
        self,
        context: SessionContext,
        *,
        role: str,
        content: str,
        message_index: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        record = make_message_record(
            context,
            role=role,
            content=content,
            message_index=message_index,
            metadata=metadata,
        )
        self._append_record(context.transcript_path, record)
        return context.transcript_path

    def append_state_snapshot(
        self,
        context: SessionContext,
        *,
        state: dict[str, Any],
    ) -> Path:
        serializable_state = json.loads(json.dumps(state))
        record = make_state_snapshot_record(context, state=serializable_state)
        self._append_record(context.transcript_path, record)
        return context.transcript_path

    def append_evidence(
        self,
        context: SessionContext,
        *,
        kind: str,
        summary: str,
        status: str = "recorded",
        subject: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        serializable_metadata = (
            json.loads(json.dumps(metadata)) if metadata is not None else None
        )
        record = make_evidence_record(
            context,
            kind=kind,
            summary=summary,
            status=status,
            subject=subject,
            metadata=serializable_metadata,
        )
        self._append_record(context.transcript_path, record)
        return context.transcript_path

    def append_compact(
        self,
        context: SessionContext,
        *,
        trigger: str,
        summary: str,
        original_message_count: int,
        summarized_message_count: int,
        kept_message_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        serializable_metadata = (
            json.loads(json.dumps(metadata)) if metadata is not None else None
        )
        record = make_compact_record(
            context,
            trigger=trigger,
            summary=summary,
            original_message_count=original_message_count,
            summarized_message_count=summarized_message_count,
            kept_message_count=kept_message_count,
            metadata=serializable_metadata,
        )
        self._append_record(context.transcript_path, record)
        return context.transcript_path

    def load_session(
        self,
        *,
        session_id: str,
        workdir: Path,
        default_state_factory: Callable[[], dict[str, Any]] | None = None,
    ) -> LoadedSession:
        normalized_workdir = workdir.expanduser().resolve()
        context = self._context_for(workdir=normalized_workdir, session_id=session_id)
        history: list[dict[str, str]] = []
        last_valid_state: dict[str, Any] | None = None
        created_at: str | None = None
        updated_at: str | None = None
        first_prompt: str | None = None
        evidence: list[SessionEvidence] = []
        compacts: list[SessionCompact] = []

        for record in self._iter_valid_records(context.transcript_path):
            if record.get("session_id") != session_id:
                continue
            if record.get("cwd") != str(normalized_workdir):
                continue

            timestamp = record.get("timestamp")
            if isinstance(timestamp, str):
                created_at = created_at or timestamp
                updated_at = timestamp

            record_type = record.get("record_type")
            if record_type == MESSAGE_RECORD_TYPE:
                role = record.get("role")
                content = record.get("content")
                if not isinstance(role, str) or not isinstance(content, str):
                    continue
                history.append({"role": role, "content": content})
                if first_prompt is None and role == "user":
                    first_prompt = content
            elif record_type == STATE_SNAPSHOT_RECORD_TYPE:
                state = self._coerce_state_snapshot(record.get("state"))
                if state is not None:
                    last_valid_state = state
            elif record_type == EVIDENCE_RECORD_TYPE:
                evidence_item = self._coerce_evidence(record)
                if evidence_item is not None:
                    evidence.append(evidence_item)
            elif record_type == COMPACT_RECORD_TYPE:
                compact_item = self._coerce_compact(record)
                if compact_item is not None:
                    compacts.append(compact_item)

        if not history:
            raise SessionLoadError(
                f"No valid session messages found for session {session_id}"
            )

        summary = SessionSummary(
            session_id=session_id,
            workdir=normalized_workdir,
            transcript_path=context.transcript_path,
            created_at=created_at,
            updated_at=updated_at,
            first_prompt=first_prompt,
            message_count=len(history),
            evidence_count=len(evidence),
            compact_count=len(compacts),
        )
        state_factory = default_state_factory or default_runtime_state
        state = deepcopy(
            last_valid_state if last_valid_state is not None else state_factory()
        )
        compacted_history = self._build_compacted_history(history, compacts)
        return LoadedSession(
            context=context,
            history=history,
            compacted_history=compacted_history,
            state=state,
            evidence=evidence,
            compacts=compacts,
            summary=summary,
        )

    def list_sessions(self, *, workdir: Path) -> list[SessionSummary]:
        normalized_workdir = workdir.expanduser().resolve()
        workspace_dir = self.workspace_dir_for(normalized_workdir)
        if not workspace_dir.exists():
            return []

        summaries: list[SessionSummary] = []
        for transcript_path in sorted(workspace_dir.glob("*.jsonl")):
            session_id = transcript_path.stem
            try:
                loaded = self.load_session(
                    session_id=session_id, workdir=normalized_workdir
                )
            except SessionLoadError:
                continue
            summaries.append(loaded.summary)

        return sorted(
            summaries,
            key=lambda summary: summary.updated_at or "",
            reverse=True,
        )

    def _append_record(self, transcript_path: Path, record: dict[str, Any]) -> None:
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        with transcript_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    def _context_for(
        self,
        *,
        workdir: Path,
        session_id: str,
        entrypoint: str | None = None,
    ) -> SessionContext:
        normalized_workdir = workdir.expanduser().resolve()
        return SessionContext(
            session_id=session_id,
            workdir=normalized_workdir,
            store_dir=self.base_dir,
            transcript_path=self.transcript_path_for(
                session_id=session_id,
                workdir=normalized_workdir,
            ),
            entrypoint=entrypoint,
        )

    def _iter_valid_records(self, transcript_path: Path) -> list[dict[str, Any]]:
        if not transcript_path.exists():
            return []

        records: list[dict[str, Any]] = []
        with transcript_path.open(encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                if record.get("version") != SESSION_RECORD_VERSION:
                    continue
                if not isinstance(record.get("timestamp"), str):
                    continue
                records.append(record)
        return records

    def _coerce_state_snapshot(self, state: Any) -> dict[str, Any] | None:
        if not isinstance(state, dict):
            return None

        todos = state.get("todos")
        rounds_since_update = state.get("rounds_since_update")
        if not isinstance(todos, list):
            return None
        if not isinstance(rounds_since_update, int):
            return None

        return {
            "todos": deepcopy(todos),
            "rounds_since_update": rounds_since_update,
        }

    def _coerce_evidence(self, record: dict[str, Any]) -> SessionEvidence | None:
        kind = record.get("kind")
        summary = record.get("summary")
        status = record.get("status")
        created_at = record.get("timestamp")
        subject = record.get("subject")
        metadata = record.get("metadata")
        if not isinstance(kind, str) or not kind.strip():
            return None
        if not isinstance(summary, str) or not summary.strip():
            return None
        if not isinstance(status, str) or not status.strip():
            return None
        if not isinstance(created_at, str) or not created_at.strip():
            return None
        if subject is not None and not isinstance(subject, str):
            return None
        if metadata is not None and not isinstance(metadata, dict):
            return None
        return SessionEvidence(
            kind=kind.strip(),
            summary=summary.strip(),
            status=status.strip(),
            created_at=created_at,
            subject=subject.strip() if isinstance(subject, str) and subject else None,
            metadata=deepcopy(metadata) if isinstance(metadata, dict) else None,
        )

    def _coerce_compact(self, record: dict[str, Any]) -> SessionCompact | None:
        trigger = record.get("trigger")
        summary = record.get("summary")
        created_at = record.get("timestamp")
        original_message_count = record.get("original_message_count")
        summarized_message_count = record.get("summarized_message_count")
        kept_message_count = record.get("kept_message_count")
        metadata = record.get("metadata")
        if not isinstance(trigger, str) or not trigger.strip():
            return None
        if not isinstance(summary, str) or not summary.strip():
            return None
        if not isinstance(created_at, str) or not created_at.strip():
            return None
        if not isinstance(original_message_count, int) or original_message_count < 0:
            return None
        if not isinstance(summarized_message_count, int) or summarized_message_count < 0:
            return None
        if not isinstance(kept_message_count, int) or kept_message_count < 0:
            return None
        if metadata is not None and not isinstance(metadata, dict):
            return None
        return SessionCompact(
            trigger=trigger.strip(),
            summary=summary.strip(),
            created_at=created_at,
            original_message_count=original_message_count,
            summarized_message_count=summarized_message_count,
            kept_message_count=kept_message_count,
            metadata=deepcopy(metadata) if isinstance(metadata, dict) else None,
        )

    def _build_compacted_history(
        self,
        history: list[dict[str, str]],
        compacts: list[SessionCompact],
    ) -> list[dict[str, Any]]:
        raw_history = [dict(message) for message in history]
        if not compacts:
            return raw_history

        latest = compacts[-1]
        keep_from = latest.original_message_count - latest.kept_message_count
        keep_from = min(len(raw_history), max(0, keep_from))
        preserved_tail = [dict(message) for message in raw_history[keep_from:]]
        if not preserved_tail:
            return raw_history
        return compact_messages_with_summary(
            preserved_tail,
            summary=latest.summary,
            keep_last=len(preserved_tail),
        ).messages
