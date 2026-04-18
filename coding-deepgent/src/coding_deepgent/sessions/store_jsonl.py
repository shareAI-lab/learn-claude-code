from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

from coding_deepgent.compact.artifacts import (
    build_collapse_boundary_message,
    build_collapse_summary_message,
    build_compact_boundary_message,
    build_compact_summary_message,
)
from coding_deepgent.runtime import default_runtime_state

from .contribution_registry import RUNTIME_STATE_CONTRIBUTIONS
from .contributions import coerce_runtime_state_contributions
from .records import (
    COLLAPSE_EVENT_KIND,
    CollapsedHistorySource,
    COMPACT_EVENT_KIND,
    EVIDENCE_RECORD_TYPE,
    LoadedSession,
    MESSAGE_RECORD_TYPE,
    SUBAGENT_MESSAGE_EVENT_KIND,
    TRANSCRIPT_EVENT_RECORD_TYPE,
    SESSION_RECORD_VERSION,
    STATE_SNAPSHOT_RECORD_TYPE,
    CompactedHistorySource,
    MessageReference,
    SessionContext,
    SessionCollapse,
    SessionCompact,
    SessionEvidence,
    SessionLoadError,
    SessionMessage,
    SessionSidechainMessage,
    SessionSummary,
    make_evidence_record,
    make_message_record,
    make_state_snapshot_record,
    make_transcript_event_record,
    message_id_for_index,
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
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        record = make_message_record(
            context,
            message_id=self._next_message_id(context),
            role=role,
            content=content,
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

    def append_sidechain_message(
        self,
        context: SessionContext,
        *,
        agent_type: str,
        role: str,
        content: str,
        subagent_thread_id: str,
        parent_message_id: str | None = None,
        parent_thread_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        payload: dict[str, Any] = {
            "agent_type": agent_type.strip(),
            "role": role.strip(),
            "content": content,
            "subagent_thread_id": subagent_thread_id.strip(),
        }
        if parent_message_id is not None and parent_message_id.strip():
            payload["parent_message_id"] = parent_message_id.strip()
        if parent_thread_id is not None and parent_thread_id.strip():
            payload["parent_thread_id"] = parent_thread_id.strip()
        if metadata is not None:
            payload["metadata"] = json.loads(json.dumps(metadata))
        record = make_transcript_event_record(
            context,
            event_kind=SUBAGENT_MESSAGE_EVENT_KIND,
            payload=payload,
        )
        self._append_record(context.transcript_path, record)
        return context.transcript_path

    def append_compact(
        self,
        context: SessionContext,
        *,
        trigger: str,
        summary: str,
        start_message_id: str,
        end_message_id: str,
        covered_message_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        payload = MessageReference(
            start_message_id=start_message_id,
            end_message_id=end_message_id,
            covered_message_ids=tuple(covered_message_ids)
            if covered_message_ids is not None
            else None,
        ).as_payload()
        payload["trigger"] = trigger.strip()
        payload["summary"] = summary.strip()
        if metadata is not None:
            payload["metadata"] = json.loads(json.dumps(metadata))
        record = make_transcript_event_record(
            context,
            event_kind=COMPACT_EVENT_KIND,
            payload=payload,
        )
        self._append_record(context.transcript_path, record)
        return context.transcript_path

    def append_collapse(
        self,
        context: SessionContext,
        *,
        trigger: str,
        summary: str,
        start_message_id: str,
        end_message_id: str,
        covered_message_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        payload = MessageReference(
            start_message_id=start_message_id,
            end_message_id=end_message_id,
            covered_message_ids=tuple(covered_message_ids)
            if covered_message_ids is not None
            else None,
        ).as_payload()
        payload["trigger"] = trigger.strip()
        payload["summary"] = summary.strip()
        if metadata is not None:
            payload["metadata"] = json.loads(json.dumps(metadata))
        record = make_transcript_event_record(
            context,
            event_kind=COLLAPSE_EVENT_KIND,
            payload=payload,
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
        history: list[SessionMessage] = []
        last_valid_state: dict[str, Any] | None = None
        created_at: str | None = None
        updated_at: str | None = None
        first_prompt: str | None = None
        evidence: list[SessionEvidence] = []
        compacts: list[SessionCompact] = []
        collapses: list[SessionCollapse] = []
        sidechain_messages: list[SessionSidechainMessage] = []

        for record in self._iter_valid_records(context.transcript_path):
            if record.get("session_id") != session_id:
                continue
            record_cwd = record.get("cwd")
            if isinstance(record_cwd, str) and record_cwd != str(normalized_workdir):
                continue

            timestamp = record.get("timestamp")
            if isinstance(timestamp, str):
                created_at = created_at or timestamp
                updated_at = timestamp

            record_type = record.get("record_type")
            if record_type == MESSAGE_RECORD_TYPE:
                message = self._coerce_message(record)
                if message is not None:
                    history.append(message)
                    if first_prompt is None and message.role == "user":
                        first_prompt = message.content
            elif record_type == STATE_SNAPSHOT_RECORD_TYPE:
                state = self._coerce_state_snapshot(record.get("state"))
                if state is not None:
                    last_valid_state = state
            elif record_type == EVIDENCE_RECORD_TYPE:
                evidence_item = self._coerce_evidence(record)
                if evidence_item is not None:
                    evidence.append(evidence_item)
            elif record_type == TRANSCRIPT_EVENT_RECORD_TYPE:
                compact_item = self._coerce_compact(record)
                if compact_item is not None:
                    compacts.append(compact_item)
                    continue
                collapse_item = self._coerce_collapse(record)
                if collapse_item is not None:
                    collapses.append(collapse_item)
                    continue
                sidechain_item = self._coerce_sidechain_message(record)
                if sidechain_item is not None:
                    sidechain_messages.append(sidechain_item)

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
            collapse_count=len(collapses),
        )
        state_factory = default_state_factory or default_runtime_state
        state = deepcopy(
            last_valid_state if last_valid_state is not None else state_factory()
        )
        compacted_history, compacted_history_source = self._build_compacted_history(
            history, compacts
        )
        collapsed_history, collapsed_history_source = self._build_collapsed_history(
            history,
            collapses,
        )
        return LoadedSession(
            context=context,
            history=history,
            compacted_history=compacted_history,
            compacted_history_source=compacted_history_source,
            collapsed_history=collapsed_history,
            collapsed_history_source=collapsed_history_source,
            state=state,
            evidence=evidence,
            compacts=compacts,
            summary=summary,
            collapses=collapses,
            sidechain_messages=sidechain_messages,
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

    def _next_message_id(self, context: SessionContext) -> str:
        message_count = sum(
            1
            for record in self._iter_valid_records(context.transcript_path)
            if record.get("session_id") == context.session_id
            and record.get("record_type") == MESSAGE_RECORD_TYPE
        )
        return message_id_for_index(message_count)

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

        coerced = {
            "todos": deepcopy(todos),
            "rounds_since_update": rounds_since_update,
        }
        coerced.update(
            coerce_runtime_state_contributions(state, RUNTIME_STATE_CONTRIBUTIONS)
        )
        return coerced

    def _coerce_message(self, record: dict[str, Any]) -> SessionMessage | None:
        message_id = record.get("message_id")
        role = record.get("role")
        content = record.get("content")
        created_at = record.get("timestamp")
        metadata = record.get("metadata")
        if not isinstance(message_id, str) or not message_id.strip():
            return None
        if not isinstance(role, str) or not role.strip():
            return None
        if not isinstance(content, str):
            return None
        if not isinstance(created_at, str) or not created_at.strip():
            return None
        if metadata is not None and not isinstance(metadata, dict):
            return None
        return SessionMessage(
            message_id=message_id.strip(),
            created_at=created_at,
            role=role.strip(),
            content=content,
            metadata=deepcopy(metadata) if isinstance(metadata, dict) else None,
        )

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
        payload = self._coerce_transcript_reference_payload(
            record,
            event_kind=COMPACT_EVENT_KIND,
        )
        if payload is None:
            return None
        return SessionCompact(
            trigger=payload["trigger"],
            summary=payload["summary"],
            created_at=payload["created_at"],
            start_message_id=payload["start_message_id"],
            end_message_id=payload["end_message_id"],
            covered_message_ids=payload["covered_message_ids"],
            metadata=payload["metadata"],
        )

    def _coerce_collapse(self, record: dict[str, Any]) -> SessionCollapse | None:
        payload = self._coerce_transcript_reference_payload(
            record,
            event_kind=COLLAPSE_EVENT_KIND,
        )
        if payload is None:
            return None
        return SessionCollapse(
            trigger=payload["trigger"],
            summary=payload["summary"],
            created_at=payload["created_at"],
            start_message_id=payload["start_message_id"],
            end_message_id=payload["end_message_id"],
            covered_message_ids=payload["covered_message_ids"],
            metadata=payload["metadata"],
        )

    def _coerce_sidechain_message(
        self,
        record: dict[str, Any],
    ) -> SessionSidechainMessage | None:
        if record.get("event_kind") != SUBAGENT_MESSAGE_EVENT_KIND:
            return None
        payload = record.get("payload")
        created_at = record.get("timestamp")
        if not isinstance(payload, dict):
            return None
        agent_type = payload.get("agent_type")
        role = payload.get("role")
        content = payload.get("content")
        subagent_thread_id = payload.get("subagent_thread_id")
        parent_message_id = payload.get("parent_message_id")
        parent_thread_id = payload.get("parent_thread_id")
        metadata = payload.get("metadata")
        if not isinstance(created_at, str) or not created_at.strip():
            return None
        if not isinstance(agent_type, str) or not agent_type.strip():
            return None
        if not isinstance(role, str) or not role.strip():
            return None
        if not isinstance(content, str):
            return None
        if not isinstance(subagent_thread_id, str) or not subagent_thread_id.strip():
            return None
        if parent_message_id is not None and not isinstance(parent_message_id, str):
            return None
        if parent_thread_id is not None and not isinstance(parent_thread_id, str):
            return None
        if metadata is not None and not isinstance(metadata, dict):
            return None
        return SessionSidechainMessage(
            created_at=created_at,
            agent_type=agent_type.strip(),
            role=role.strip(),
            content=content,
            subagent_thread_id=subagent_thread_id.strip(),
            parent_message_id=parent_message_id.strip()
            if isinstance(parent_message_id, str) and parent_message_id.strip()
            else None,
            parent_thread_id=parent_thread_id.strip()
            if isinstance(parent_thread_id, str) and parent_thread_id.strip()
            else None,
            metadata=deepcopy(metadata) if isinstance(metadata, dict) else None,
        )

    def _coerce_transcript_reference_payload(
        self,
        record: dict[str, Any],
        *,
        event_kind: str,
    ) -> dict[str, Any] | None:
        if record.get("event_kind") != event_kind:
            return None
        payload = record.get("payload")
        created_at = record.get("timestamp")
        if not isinstance(payload, dict):
            return None
        trigger = payload.get("trigger")
        summary = payload.get("summary")
        start_message_id = payload.get("start_message_id")
        end_message_id = payload.get("end_message_id")
        covered_message_ids = payload.get("covered_message_ids")
        metadata = payload.get("metadata")
        if not isinstance(trigger, str) or not trigger.strip():
            return None
        if not isinstance(summary, str) or not summary.strip():
            return None
        if not isinstance(created_at, str) or not created_at.strip():
            return None
        if not isinstance(start_message_id, str) or not start_message_id.strip():
            return None
        if not isinstance(end_message_id, str) or not end_message_id.strip():
            return None
        if covered_message_ids is not None and (
            not isinstance(covered_message_ids, list)
            or not covered_message_ids
            or any(
                not isinstance(item, str) or not item.strip()
                for item in covered_message_ids
            )
        ):
            return None
        if metadata is not None and not isinstance(metadata, dict):
            return None
        return {
            "trigger": trigger.strip(),
            "summary": summary.strip(),
            "created_at": created_at,
            "start_message_id": start_message_id.strip(),
            "end_message_id": end_message_id.strip(),
            "covered_message_ids": tuple(
                item.strip() for item in covered_message_ids
            )
            if isinstance(covered_message_ids, list)
            else None,
            "metadata": deepcopy(metadata) if isinstance(metadata, dict) else None,
        }

    def _build_compacted_history(
        self,
        history: list[SessionMessage],
        compacts: list[SessionCompact],
    ) -> tuple[list[dict[str, Any]], CompactedHistorySource]:
        projected_history = [message.as_conversation_dict() for message in history]
        if not compacts:
            return projected_history, CompactedHistorySource(
                mode="raw", reason="no_compacts"
            )

        for index in range(len(compacts) - 1, -1, -1):
            compact = compacts[index]
            compacted = self._build_history_for_compact(history, compact)
            if compacted is not None:
                return compacted, CompactedHistorySource(
                    mode="compact",
                    reason="latest_valid_compact",
                    compact_index=index,
                )
        return projected_history, CompactedHistorySource(
            mode="raw", reason="no_valid_compact"
        )

    def _build_history_for_compact(
        self,
        raw_history: list[SessionMessage],
        compact: SessionCompact,
    ) -> list[dict[str, Any]] | None:
        id_to_index = {
            message.message_id: index for index, message in enumerate(raw_history)
        }
        start_index = id_to_index.get(compact.start_message_id)
        end_index = id_to_index.get(compact.end_message_id)
        if start_index is None or end_index is None or start_index != 0 or end_index < start_index:
            return None
        covered_slice = tuple(
            message.message_id for message in raw_history[start_index : end_index + 1]
        )
        if compact.covered_message_ids is not None and compact.covered_message_ids != covered_slice:
            return None
        preserved_tail = [
            message.as_conversation_dict() for message in raw_history[end_index + 1 :]
        ]
        return [
            build_compact_boundary_message(
                trigger=compact.trigger,
                original_message_count=len(raw_history),
                summarized_message_count=end_index + 1,
                kept_message_count=len(preserved_tail),
                start_message_id=compact.start_message_id,
                end_message_id=compact.end_message_id,
                covered_message_ids=list(compact.covered_message_ids)
                if compact.covered_message_ids is not None
                else None,
                metadata=deepcopy(compact.metadata) if compact.metadata is not None else None,
            ),
            build_compact_summary_message(compact.summary),
            *preserved_tail,
        ]

    def _build_collapsed_history(
        self,
        history: list[SessionMessage],
        collapses: list[SessionCollapse],
    ) -> tuple[list[dict[str, Any]], CollapsedHistorySource]:
        projected_history = [message.as_conversation_dict() for message in history]
        if not collapses:
            return projected_history, CollapsedHistorySource(
                mode="raw",
                reason="no_collapses",
            )

        selected: list[tuple[int, int, int, SessionCollapse]] = []
        covered_indexes: set[int] = set()
        id_to_index = {
            message.message_id: index for index, message in enumerate(history)
        }
        for collapse_index in range(len(collapses) - 1, -1, -1):
            collapse = collapses[collapse_index]
            span = self._collapse_span(history, id_to_index, collapse)
            if span is None:
                continue
            start_index, end_index = span
            span_indexes = set(range(start_index, end_index + 1))
            if covered_indexes & span_indexes:
                continue
            covered_indexes.update(span_indexes)
            selected.append((start_index, end_index, collapse_index, collapse))

        if not selected:
            return projected_history, CollapsedHistorySource(
                mode="raw",
                reason="no_valid_collapse",
            )

        selected.sort(key=lambda item: item[0])
        collapsed: list[dict[str, Any]] = []
        cursor = 0
        for start_index, end_index, _collapse_index, collapse in selected:
            collapsed.extend(
                message.as_conversation_dict() for message in history[cursor:start_index]
            )
            collapsed.extend(
                self._collapse_projection_messages(
                    history=history,
                    collapse=collapse,
                    start_index=start_index,
                    end_index=end_index,
                )
            )
            cursor = end_index + 1
        collapsed.extend(message.as_conversation_dict() for message in history[cursor:])
        latest_index = max(item[2] for item in selected)
        return collapsed, CollapsedHistorySource(
            mode="collapse",
            reason="valid_collapses",
            collapse_index=latest_index,
        )

    def _collapse_span(
        self,
        history: list[SessionMessage],
        id_to_index: dict[str, int],
        collapse: SessionCollapse,
    ) -> tuple[int, int] | None:
        start_index = id_to_index.get(collapse.start_message_id)
        end_index = id_to_index.get(collapse.end_message_id)
        if start_index is None or end_index is None or end_index < start_index:
            return None
        covered_slice = tuple(
            message.message_id for message in history[start_index : end_index + 1]
        )
        if (
            collapse.covered_message_ids is not None
            and collapse.covered_message_ids != covered_slice
        ):
            return None
        return start_index, end_index

    def _collapse_projection_messages(
        self,
        *,
        history: list[SessionMessage],
        collapse: SessionCollapse,
        start_index: int,
        end_index: int,
    ) -> list[dict[str, Any]]:
        kept_message_count = len(history) - (end_index - start_index + 1)
        covered_message_ids = [
            message.message_id for message in history[start_index : end_index + 1]
        ]
        return [
            build_collapse_boundary_message(
                trigger=collapse.trigger,
                original_message_count=len(history),
                collapsed_message_count=len(covered_message_ids),
                kept_message_count=kept_message_count,
                start_message_id=collapse.start_message_id,
                end_message_id=collapse.end_message_id,
                covered_message_ids=covered_message_ids,
                metadata=(
                    deepcopy(collapse.metadata)
                    if collapse.metadata is not None
                    else None
                ),
            ),
            build_collapse_summary_message(collapse.summary),
        ]

    def latest_message_id(self, context: SessionContext) -> str | None:
        latest: str | None = None
        for record in self._iter_valid_records(context.transcript_path):
            if (
                record.get("session_id") == context.session_id
                and record.get("record_type") == MESSAGE_RECORD_TYPE
                and isinstance(record.get("message_id"), str)
            ):
                latest = str(record["message_id"])
        return latest
