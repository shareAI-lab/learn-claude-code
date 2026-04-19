from __future__ import annotations

from pathlib import Path

from coding_deepgent.memory.archive import InMemoryArchiveStore
from coding_deepgent.memory.backend import (
    MemoryJobStatus,
    SqlAlchemyMemoryRepository,
    create_memory_engine,
    migrate_memory_schema,
)
from coding_deepgent.memory.queue import InMemoryQueue
from coding_deepgent.memory.schemas import MemoryRecord
from coding_deepgent.memory.service import ExtractionCandidate, MemoryService


def _sqlite_repo(tmp_path: Path) -> SqlAlchemyMemoryRepository:
    engine = create_memory_engine(f"sqlite+pysqlite:///{tmp_path / 'memory.db'}")
    migrate_memory_schema(engine)
    return SqlAlchemyMemoryRepository(engine)


def test_sqlalchemy_memory_repository_persists_records_and_versions(tmp_path: Path) -> None:
    repo = _sqlite_repo(tmp_path)
    stored = repo.save_record(
        project_scope="repo-a",
        agent_scope=None,
        record=MemoryRecord(
            type="feedback",
            rule="Run lint before commit",
            why="The repo requires clean validation before code submission",
            how_to_apply="Before any commit-like completion step, run lint first",
        ),
        source="manual",
    )

    listed = repo.list_records(project_scope="repo-a")

    assert stored.record.type == "feedback"
    assert [item.id for item in listed] == [stored.id]
    assert listed[0].record.rule == "Run lint before commit"


def test_memory_service_processes_extraction_and_snapshot_jobs(tmp_path: Path) -> None:
    repo = _sqlite_repo(tmp_path)
    queue = InMemoryQueue()
    archive = InMemoryArchiveStore()

    def extractor(candidate: ExtractionCandidate) -> list[MemoryRecord]:
        return [
            MemoryRecord(
                type="feedback",
                rule="Run lint before commit",
                why=f"Extracted from {candidate.source}",
                how_to_apply="Before any commit-like completion step, run lint first",
                source="auto_extract",
            )
        ]

    service = MemoryService(
        repository=repo,
        queue=queue,
        archive_store=archive,
        extractor=extractor,
    )

    extract_job = service.enqueue_extraction(
        project_scope="repo-a",
        agent_scope="agent-a",
        source="agent_loop",
        text="User: please run lint before commit",
    )
    processed_extract = service.process_next_job()
    assert processed_extract is not None
    assert processed_extract.id == extract_job.id
    assert processed_extract.status == MemoryJobStatus.COMPLETED

    stored = service.list_records(project_scope="repo-a", agent_scope="agent-a")
    assert stored
    assert stored[0].record.rule == "Run lint before commit"
    assert service.list_agent_scopes(project_scope="repo-a") == ["agent-a"]

    snapshot_job = service.enqueue_snapshot_refresh(
        project_scope="repo-a",
        agent_scope="agent-a",
        trigger="test",
    )
    processed_snapshot = service.process_next_job()
    assert processed_snapshot is not None
    assert processed_snapshot.status == MemoryJobStatus.COMPLETED
    assert processed_snapshot.archive_object_key is not None
    assert processed_snapshot.archive_object_key in archive.objects
    assert snapshot_job.job_type == "refresh_agent_memory_snapshot"
