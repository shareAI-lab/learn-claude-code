from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4

import psycopg
from sqlalchemy import (
    JSON,
    DateTime,
    Engine,
    MetaData,
    or_,
    String,
    Text,
    create_engine,
    desc,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.engine import URL, make_url

from coding_deepgent.memory.schemas import MemoryRecord, MemoryType


def _utc_now() -> datetime:
    return datetime.now(UTC)


class MemoryRecordStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MemoryJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Base(DeclarativeBase):
    metadata = MetaData()


class MemoryRecordRow(Base):
    __tablename__ = "memory_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_scope: Mapped[str] = mapped_column(String(512), index=True)
    agent_scope: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    memory_type: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MemoryVersionRow(Base):
    __tablename__ = "memory_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    memory_record_id: Mapped[str] = mapped_column(String(36), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MemoryExtractionJobRow(Base):
    __tablename__ = "memory_extraction_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_scope: Mapped[str] = mapped_column(String(512), index=True)
    agent_scope: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    dedupe_key: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    archive_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentMemoryScopeRow(Base):
    __tablename__ = "agent_memory_scopes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_scope: Mapped[str] = mapped_column(String(512), index=True)
    agent_scope: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


@dataclass(frozen=True, slots=True)
class DurableMemoryRecord:
    id: str
    project_scope: str
    agent_scope: str | None
    record: MemoryRecord
    source: str
    status: MemoryRecordStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DurableMemoryVersion:
    id: str
    memory_record_id: str
    payload: dict[str, Any]
    source: str
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DurableMemoryJob:
    id: str
    project_scope: str
    agent_scope: str | None
    status: MemoryJobStatus
    job_type: str
    dedupe_key: str
    payload: dict[str, Any]
    archive_object_key: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


def create_memory_engine(database_url: str) -> Engine:
    if database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgres://") :]
    elif database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgresql://") :]
    return create_engine(database_url, future=True)


def migrate_memory_schema(engine: Engine) -> None:
    _ensure_postgres_database_exists(engine.url)
    Base.metadata.create_all(engine)


def _ensure_postgres_database_exists(database_url: URL | str) -> None:
    url = make_url(database_url) if isinstance(database_url, str) else database_url
    if url.get_backend_name() != "postgresql":
        return
    database = url.database
    if not database:
        return
    with psycopg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        dbname="postgres",
        autocommit=True,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
            if cur.fetchone() is not None:
                return
            cur.execute(f'CREATE DATABASE "{database}"')


class DurableMemoryRepository(Protocol):
    def save_record(
        self,
        *,
        project_scope: str,
        agent_scope: str | None,
        record: MemoryRecord,
        source: str,
    ) -> DurableMemoryRecord: ...

    def list_records(
        self,
        *,
        project_scope: str,
        memory_type: MemoryType | None = None,
        agent_scope: str | None = None,
        include_deleted: bool = False,
        limit: int = 20,
    ) -> list[DurableMemoryRecord]: ...

    def delete_record(
        self,
        *,
        record_id: str,
        deleted_by: str,
    ) -> bool: ...

    def append_job(
        self,
        *,
        project_scope: str,
        agent_scope: str | None,
        job_type: str,
        dedupe_key: str,
        payload: dict[str, Any],
    ) -> DurableMemoryJob: ...

    def get_job(self, job_id: str) -> DurableMemoryJob | None: ...

    def list_jobs(
        self,
        *,
        project_scope: str,
        agent_scope: str | None = None,
        job_type: str | None = None,
        status: MemoryJobStatus | None = None,
        limit: int = 20,
    ) -> list[DurableMemoryJob]: ...

    def update_job_status(
        self,
        *,
        job_id: str,
        status: MemoryJobStatus,
        error_message: str | None = None,
        archive_object_key: str | None = None,
    ) -> DurableMemoryJob: ...

    def ensure_agent_scope(self, *, project_scope: str, agent_scope: str) -> None: ...
    def list_agent_scopes(self, *, project_scope: str) -> list[str]: ...


class SqlAlchemyMemoryRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        migrate_memory_schema(engine)

    def save_record(
        self,
        *,
        project_scope: str,
        agent_scope: str | None,
        record: MemoryRecord,
        source: str,
    ) -> DurableMemoryRecord:
        now = _utc_now()
        row = MemoryRecordRow(
            id=str(uuid4()),
            project_scope=project_scope,
            agent_scope=agent_scope,
            memory_type=record.type,
            payload=record.model_dump(),
            source=source,
            status=MemoryRecordStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
        )
        version = MemoryVersionRow(
            id=str(uuid4()),
            memory_record_id=row.id,
            payload=row.payload,
            source=source,
            status=row.status,
            created_at=now,
        )
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(row)
            session.add(version)
            session.commit()
        return _record_from_row(row)

    def list_records(
        self,
        *,
        project_scope: str,
        memory_type: MemoryType | None = None,
        agent_scope: str | None = None,
        include_deleted: bool = False,
        limit: int = 20,
    ) -> list[DurableMemoryRecord]:
        stmt = select(MemoryRecordRow).where(MemoryRecordRow.project_scope == project_scope)
        if memory_type is not None:
            stmt = stmt.where(MemoryRecordRow.memory_type == memory_type)
        if agent_scope is not None:
            stmt = stmt.where(
                or_(
                    MemoryRecordRow.agent_scope == agent_scope,
                    MemoryRecordRow.agent_scope.is_(None),
                )
            )
        if not include_deleted:
            stmt = stmt.where(MemoryRecordRow.status != MemoryRecordStatus.DELETED.value)
        stmt = stmt.order_by(desc(MemoryRecordRow.updated_at)).limit(limit)
        with Session(self.engine) as session:
            rows = session.scalars(stmt).all()
        return [_record_from_row(row) for row in rows]

    def delete_record(self, *, record_id: str, deleted_by: str) -> bool:
        with Session(self.engine, expire_on_commit=False) as session:
            row = session.get(MemoryRecordRow, record_id)
            if row is None:
                return False
            row.status = MemoryRecordStatus.DELETED.value
            row.updated_at = _utc_now()
            session.add(
                MemoryVersionRow(
                    id=str(uuid4()),
                    memory_record_id=row.id,
                    payload=row.payload,
                    source=deleted_by,
                    status=row.status,
                    created_at=row.updated_at,
                )
            )
            session.commit()
            return True

    def append_job(
        self,
        *,
        project_scope: str,
        agent_scope: str | None,
        job_type: str,
        dedupe_key: str,
        payload: dict[str, Any],
    ) -> DurableMemoryJob:
        with Session(self.engine, expire_on_commit=False) as session:
            existing = session.scalar(
                select(MemoryExtractionJobRow).where(
                    MemoryExtractionJobRow.dedupe_key == dedupe_key
                )
            )
            if existing is not None:
                return _job_from_row(existing)
            now = _utc_now()
            row = MemoryExtractionJobRow(
                id=str(uuid4()),
                project_scope=project_scope,
                agent_scope=agent_scope,
                status=MemoryJobStatus.QUEUED.value,
                job_type=job_type,
                dedupe_key=dedupe_key,
                payload=payload,
                archive_object_key=None,
                error_message=None,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.commit()
            return _job_from_row(row)

    def get_job(self, job_id: str) -> DurableMemoryJob | None:
        with Session(self.engine, expire_on_commit=False) as session:
            row = session.get(MemoryExtractionJobRow, job_id)
        return _job_from_row(row) if row is not None else None

    def list_jobs(
        self,
        *,
        project_scope: str,
        agent_scope: str | None = None,
        job_type: str | None = None,
        status: MemoryJobStatus | None = None,
        limit: int = 20,
    ) -> list[DurableMemoryJob]:
        stmt = select(MemoryExtractionJobRow).where(
            MemoryExtractionJobRow.project_scope == project_scope
        )
        if agent_scope is not None:
            stmt = stmt.where(MemoryExtractionJobRow.agent_scope == agent_scope)
        if job_type is not None:
            stmt = stmt.where(MemoryExtractionJobRow.job_type == job_type)
        if status is not None:
            stmt = stmt.where(MemoryExtractionJobRow.status == status.value)
        stmt = stmt.order_by(desc(MemoryExtractionJobRow.updated_at)).limit(limit)
        with Session(self.engine, expire_on_commit=False) as session:
            rows = session.scalars(stmt).all()
        return [_job_from_row(row) for row in rows]

    def update_job_status(
        self,
        *,
        job_id: str,
        status: MemoryJobStatus,
        error_message: str | None = None,
        archive_object_key: str | None = None,
    ) -> DurableMemoryJob:
        with Session(self.engine, expire_on_commit=False) as session:
            row = session.get(MemoryExtractionJobRow, job_id)
            if row is None:
                raise KeyError(f"Unknown memory extraction job: {job_id}")
            row.status = status.value
            row.updated_at = _utc_now()
            row.error_message = error_message
            row.archive_object_key = archive_object_key
            session.commit()
            return _job_from_row(row)

    def ensure_agent_scope(self, *, project_scope: str, agent_scope: str) -> None:
        with Session(self.engine, expire_on_commit=False) as session:
            existing = session.scalar(
                select(AgentMemoryScopeRow).where(
                    AgentMemoryScopeRow.project_scope == project_scope,
                    AgentMemoryScopeRow.agent_scope == agent_scope,
                )
            )
            if existing is not None:
                return
            now = _utc_now()
            session.add(
                AgentMemoryScopeRow(
                    id=str(uuid4()),
                    project_scope=project_scope,
                    agent_scope=agent_scope,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()

    def list_agent_scopes(self, *, project_scope: str) -> list[str]:
        stmt = (
            select(AgentMemoryScopeRow.agent_scope)
            .where(AgentMemoryScopeRow.project_scope == project_scope)
            .order_by(AgentMemoryScopeRow.agent_scope)
        )
        with Session(self.engine, expire_on_commit=False) as session:
            return list(session.scalars(stmt).all())


def _record_from_row(row: MemoryRecordRow) -> DurableMemoryRecord:
    return DurableMemoryRecord(
        id=row.id,
        project_scope=row.project_scope,
        agent_scope=row.agent_scope,
        record=MemoryRecord.model_validate(row.payload),
        source=row.source,
        status=MemoryRecordStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _job_from_row(row: MemoryExtractionJobRow) -> DurableMemoryJob:
    return DurableMemoryJob(
        id=row.id,
        project_scope=row.project_scope,
        agent_scope=row.agent_scope,
        status=MemoryJobStatus(row.status),
        job_type=row.job_type,
        dedupe_key=row.dedupe_key,
        payload=dict(row.payload),
        archive_object_key=row.archive_object_key,
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
