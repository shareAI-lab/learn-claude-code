from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable

from coding_deepgent.memory.archive import MemoryArchiveStore
from coding_deepgent.memory.backend import (
    DurableMemoryJob,
    DurableMemoryRecord,
    DurableMemoryRepository,
    MemoryJobStatus,
)
from coding_deepgent.memory.policy import evaluate_memory_quality
from coding_deepgent.memory.queue import MemoryJobEnvelope, MemoryQueue
from coding_deepgent.memory.schemas import MemoryRecord, MemoryType


@dataclass(frozen=True, slots=True)
class ExtractionCandidate:
    project_scope: str
    agent_scope: str | None
    source: str
    text: str


class MemoryService:
    def __init__(
        self,
        *,
        repository: DurableMemoryRepository,
        queue: MemoryQueue,
        archive_store: MemoryArchiveStore | None = None,
        extractor: Callable[[ExtractionCandidate], list[MemoryRecord]] | None = None,
    ) -> None:
        self.repository = repository
        self.queue = queue
        self.archive_store = archive_store
        self.extractor = extractor or (lambda candidate: [])

    def save_record(
        self,
        *,
        project_scope: str,
        agent_scope: str | None,
        record: MemoryRecord,
        source: str,
    ) -> DurableMemoryRecord:
        existing = self.repository.list_records(
            project_scope=project_scope,
            memory_type=record.type,
            agent_scope=agent_scope,
            limit=200,
        )
        quality = evaluate_memory_quality(
            record, existing_records=[item.record for item in existing]
        )
        if not quality.allowed:
            raise ValueError(quality.reason)
        if agent_scope is not None:
            self.repository.ensure_agent_scope(
                project_scope=project_scope, agent_scope=agent_scope
            )
        stored = self.repository.save_record(
            project_scope=project_scope,
            agent_scope=agent_scope,
            record=record,
            source=source,
        )
        self.enqueue_snapshot_refresh(
            project_scope=project_scope,
            agent_scope=agent_scope,
            trigger=f"save:{record.type}",
        )
        return stored

    def list_records(
        self,
        *,
        project_scope: str,
        memory_type: MemoryType | None = None,
        agent_scope: str | None = None,
        limit: int = 20,
    ) -> list[DurableMemoryRecord]:
        return self.repository.list_records(
            project_scope=project_scope,
            memory_type=memory_type,
            agent_scope=agent_scope,
            limit=limit,
        )

    def delete_record(
        self,
        *,
        record_id: str,
        deleted_by: str,
        project_scope: str,
        agent_scope: str | None,
    ) -> bool:
        deleted = self.repository.delete_record(record_id=record_id, deleted_by=deleted_by)
        if deleted:
            self.enqueue_snapshot_refresh(
                project_scope=project_scope,
                agent_scope=agent_scope,
                trigger="delete",
            )
        return deleted

    def enqueue_extraction(
        self,
        *,
        project_scope: str,
        agent_scope: str | None,
        source: str,
        text: str,
    ) -> DurableMemoryJob:
        dedupe_key = _dedupe_key("extract", project_scope, agent_scope, text)
        job = self.repository.append_job(
            project_scope=project_scope,
            agent_scope=agent_scope,
            job_type="extract_long_term_memory",
            dedupe_key=dedupe_key,
            payload={"source": source, "text": text},
        )
        self.queue.enqueue(
            MemoryJobEnvelope(
                job_id=job.id, job_type=job.job_type, dedupe_key=job.dedupe_key
            )
        )
        return job

    def enqueue_snapshot_refresh(
        self,
        *,
        project_scope: str,
        agent_scope: str | None,
        trigger: str,
    ) -> DurableMemoryJob:
        dedupe_key = _dedupe_key("snapshot", project_scope, agent_scope, trigger)
        job = self.repository.append_job(
            project_scope=project_scope,
            agent_scope=agent_scope,
            job_type="refresh_agent_memory_snapshot",
            dedupe_key=dedupe_key,
            payload={"trigger": trigger},
        )
        self.queue.enqueue(
            MemoryJobEnvelope(
                job_id=job.id, job_type=job.job_type, dedupe_key=job.dedupe_key
            )
        )
        return job

    def list_jobs(
        self,
        *,
        project_scope: str,
        status: MemoryJobStatus | None = None,
        limit: int = 20,
    ) -> list[DurableMemoryJob]:
        return self.repository.list_jobs(
            project_scope=project_scope,
            status=status,
            limit=limit,
        )

    def process_next_job(self) -> DurableMemoryJob | None:
        envelope = self.queue.dequeue()
        if envelope is None:
            return None
        job = self.repository.update_job_status(
            job_id=envelope.job_id, status=MemoryJobStatus.RUNNING
        )
        try:
            if job.job_type == "extract_long_term_memory":
                self._process_extraction_job(job)
                archive_object_key = None
            elif job.job_type == "refresh_agent_memory_snapshot":
                archive_object_key = self._process_snapshot_job(job)
            else:
                raise ValueError(f"Unsupported memory job type: {job.job_type}")
            return self.repository.update_job_status(
                job_id=job.id,
                status=MemoryJobStatus.COMPLETED,
                archive_object_key=archive_object_key,
            )
        except Exception as exc:
            return self.repository.update_job_status(
                job_id=job.id,
                status=MemoryJobStatus.FAILED,
                error_message=str(exc),
            )

    def _process_extraction_job(self, job: DurableMemoryJob) -> None:
        candidate = ExtractionCandidate(
            project_scope=job.project_scope,
            agent_scope=job.agent_scope,
            source=str(job.payload.get("source", "auto")),
            text=str(job.payload.get("text", "")),
        )
        for record in self.extractor(candidate):
            self.save_record(
                project_scope=job.project_scope,
                agent_scope=job.agent_scope,
                record=record,
                source="auto_extract",
            )

    def _process_snapshot_job(self, job: DurableMemoryJob) -> str | None:
        if self.archive_store is None:
            return None
        records = self.repository.list_records(
            project_scope=job.project_scope,
            agent_scope=job.agent_scope,
            limit=500,
        )
        object_key = _snapshot_object_key(
            project_scope=job.project_scope,
            agent_scope=job.agent_scope,
        )
        return self.archive_store.put_json(
            object_key=object_key,
            payload={
                "project_scope": job.project_scope,
                "agent_scope": job.agent_scope,
                "records": [record.record.model_dump() for record in records],
            },
        )


def _dedupe_key(
    kind: str, project_scope: str, agent_scope: str | None, text: str
) -> str:
    payload = f"{kind}\0{project_scope}\0{agent_scope or ''}\0{text}"
    return sha256(payload.encode("utf-8")).hexdigest()[:24]


def _snapshot_object_key(*, project_scope: str, agent_scope: str | None) -> str:
    slug = project_scope.strip("/").replace("/", "_")
    scope = (agent_scope or "global").replace("/", "_")
    return f"memory-snapshots/{slug}/{scope}.json"
