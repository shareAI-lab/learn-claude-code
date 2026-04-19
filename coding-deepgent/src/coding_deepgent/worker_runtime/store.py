from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from coding_deepgent.event_stream import append_event

WORKER_NAMESPACE = ("coding_deepgent_workers",)
WorkerStatus = Literal["queued", "running", "idle", "completed", "failed", "cancelled"]


class WorkerStore(Protocol):
    def put(
        self, namespace: tuple[str, ...], key: str, value: dict[str, object]
    ) -> None: ...
    def get(self, namespace: tuple[str, ...], key: str) -> object | None: ...
    def search(self, namespace: tuple[str, ...]) -> Iterable[object]: ...


class WorkerRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worker_id: str
    kind: str = Field(default="local", min_length=1)
    session_id: str = Field(default="default", min_length=1)
    status: WorkerStatus = "queued"
    owner: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    result_summary: str | None = None
    stop_requested: bool = False
    created_at: str
    updated_at: str
    heartbeat_at: str | None = None


def create_worker(
    store: WorkerStore,
    *,
    kind: str,
    session_id: str = "default",
    owner: str | None = None,
    payload: dict[str, Any] | None = None,
) -> WorkerRecord:
    now = _now()
    worker_id = _worker_id(kind=kind, session_id=session_id, created_at=now)
    record = WorkerRecord(
        worker_id=worker_id,
        kind=kind.strip(),
        session_id=session_id.strip() or "default",
        owner=owner,
        payload=payload or {},
        created_at=now,
        updated_at=now,
    )
    return _save(store, record, event_kind="worker_created")


def get_worker(store: WorkerStore, worker_id: str) -> WorkerRecord:
    item = store.get(WORKER_NAMESPACE, worker_id)
    if item is None:
        raise KeyError(f"Unknown worker: {worker_id}")
    return WorkerRecord.model_validate(_item_value(item))


def list_workers(
    store: WorkerStore,
    *,
    include_terminal: bool = False,
) -> list[WorkerRecord]:
    records = [
        WorkerRecord.model_validate(_item_value(item))
        for item in store.search(WORKER_NAMESPACE)
    ]
    if not include_terminal:
        records = [
            record
            for record in records
            if record.status not in {"completed", "failed", "cancelled"}
        ]
    return sorted(records, key=lambda record: record.worker_id)


def heartbeat_worker(store: WorkerStore, worker_id: str) -> WorkerRecord:
    record = get_worker(store, worker_id)
    now = _now()
    return _save(
        store,
        record.model_copy(
            update={"status": "running", "heartbeat_at": now, "updated_at": now}
        ),
        event_kind="worker_heartbeat",
    )


def request_worker_stop(store: WorkerStore, worker_id: str) -> WorkerRecord:
    record = get_worker(store, worker_id)
    return _save(
        store,
        record.model_copy(update={"stop_requested": True, "updated_at": _now()}),
        event_kind="worker_stop_requested",
    )


def complete_worker(
    store: WorkerStore,
    worker_id: str,
    *,
    status: WorkerStatus = "completed",
    result_summary: str | None = None,
) -> WorkerRecord:
    if status not in {"completed", "failed", "cancelled"}:
        raise ValueError("worker completion status must be terminal")
    record = get_worker(store, worker_id)
    return _save(
        store,
        record.model_copy(
            update={
                "status": status,
                "result_summary": result_summary,
                "updated_at": _now(),
            }
        ),
        event_kind=f"worker_{status}",
    )


def _save(store: WorkerStore, record: WorkerRecord, *, event_kind: str) -> WorkerRecord:
    store.put(WORKER_NAMESPACE, record.worker_id, record.model_dump())
    append_event(
        store,
        stream_id=f"worker:{record.worker_id}",
        kind=event_kind,
        payload={
            "worker_id": record.worker_id,
            "status": record.status,
            "session_id": record.session_id,
        },
    )
    return record


def _item_value(item: object) -> dict[str, object]:
    value = getattr(item, "value", item)
    return value if isinstance(value, dict) else {}


def _worker_id(*, kind: str, session_id: str, created_at: str) -> str:
    digest = sha256(f"{kind}\0{session_id}\0{created_at}".encode("utf-8")).hexdigest()
    return f"worker-{digest[:12]}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
