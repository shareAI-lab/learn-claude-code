from __future__ import annotations

from typing import Any

from dependency_injector import containers, providers
from redis import Redis

from coding_deepgent.memory.extractor import extract_memory_candidates
from coding_deepgent.memory.archive import (
    S3ArchiveSettings,
    S3MemoryArchiveStore,
)
from coding_deepgent.memory.backend import (
    create_memory_engine,
    migrate_memory_schema,
    SqlAlchemyMemoryRepository,
)
from coding_deepgent.memory.queue import InMemoryQueue, RedisMemoryQueue
from coding_deepgent.memory.service import MemoryService
from coding_deepgent.settings import Settings


def _resolve_memory_database_url(settings: Settings) -> str:
    if settings.postgres_url:
        return settings.postgres_url
    db_path = (settings.workdir / ".coding-deepgent" / "memory.db").resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+pysqlite:///{db_path}"


def _build_memory_queue(settings: Settings):
    if settings.redis_url:
        return RedisMemoryQueue(Redis.from_url(settings.redis_url))
    return InMemoryQueue()


def _build_archive_store(settings: Settings):
    if settings.offload_backend != "s3":
        return None
    required = (
        settings.s3_bucket,
        settings.s3_endpoint_url,
        settings.s3_region,
        settings.s3_access_key_id,
        settings.s3_secret_access_key,
    )
    if any(value in (None, "") for value in required):
        return None
    assert settings.s3_secret_access_key is not None
    return S3MemoryArchiveStore(
        S3ArchiveSettings(
            bucket=str(settings.s3_bucket),
            endpoint_url=str(settings.s3_endpoint_url),
            region=str(settings.s3_region),
            access_key_id=str(settings.s3_access_key_id),
            secret_access_key=settings.s3_secret_access_key.get_secret_value(),
        )
    )


class MemoryBackendContainer(containers.DeclarativeContainer):
    settings: Any = providers.Dependency()

    engine: Any = providers.Singleton(create_memory_engine, providers.Callable(_resolve_memory_database_url, settings))
    migrate: Any = providers.Callable(migrate_memory_schema, engine)
    repository: Any = providers.Singleton(SqlAlchemyMemoryRepository, engine)
    queue: Any = providers.Singleton(_build_memory_queue, settings)
    archive_store: Any = providers.Singleton(_build_archive_store, settings)
    extractor: Any = providers.Object(extract_memory_candidates)
    service: Any = providers.Singleton(
        MemoryService,
        repository=repository,
        queue=queue,
        archive_store=archive_store,
        extractor=extractor,
    )
