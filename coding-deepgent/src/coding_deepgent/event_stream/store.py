from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

EVENT_STREAM_NAMESPACE = "coding_deepgent_event_stream"
EventVisibility = Literal["visible", "internal"]


class EventStore(Protocol):
    def put(
        self, namespace: tuple[str, ...], key: str, value: dict[str, object]
    ) -> None: ...
    def get(self, namespace: tuple[str, ...], key: str) -> object | None: ...
    def search(self, namespace: tuple[str, ...]) -> Iterable[object]: ...


class EventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    stream_id: str
    sequence: int = Field(..., ge=1)
    kind: str = Field(..., min_length=1)
    visibility: EventVisibility = "visible"
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    acked: bool = False
    acked_at: str | None = None


def event_namespace(stream_id: str) -> tuple[str, ...]:
    return (EVENT_STREAM_NAMESPACE, stream_id.strip() or "default")


def append_event(
    store: EventStore,
    *,
    stream_id: str,
    kind: str,
    payload: dict[str, Any] | None = None,
    visibility: EventVisibility = "visible",
) -> EventRecord:
    records = list_events(store, stream_id=stream_id, include_internal=True)
    sequence = (records[-1].sequence + 1) if records else 1
    event_id = _event_id(stream_id=stream_id, sequence=sequence, kind=kind)
    record = EventRecord(
        event_id=event_id,
        stream_id=stream_id.strip() or "default",
        sequence=sequence,
        kind=kind.strip(),
        visibility=visibility,
        payload=payload or {},
        created_at=_now(),
    )
    store.put(event_namespace(record.stream_id), record.event_id, record.model_dump())
    return record


def get_event(store: EventStore, *, stream_id: str, event_id: str) -> EventRecord:
    item = store.get(event_namespace(stream_id), event_id)
    if item is None:
        raise KeyError(f"Unknown event: {event_id}")
    return EventRecord.model_validate(_item_value(item))


def list_events(
    store: EventStore,
    *,
    stream_id: str,
    after_sequence: int | None = None,
    include_internal: bool = False,
) -> list[EventRecord]:
    records = [
        EventRecord.model_validate(_item_value(item))
        for item in store.search(event_namespace(stream_id))
    ]
    if after_sequence is not None:
        records = [record for record in records if record.sequence > after_sequence]
    if not include_internal:
        records = [record for record in records if record.visibility == "visible"]
    return sorted(records, key=lambda record: record.sequence)


def ack_event(store: EventStore, *, stream_id: str, event_id: str) -> EventRecord:
    record = get_event(store, stream_id=stream_id, event_id=event_id)
    updated = record.model_copy(update={"acked": True, "acked_at": _now()})
    store.put(event_namespace(stream_id), updated.event_id, updated.model_dump())
    return updated


def _item_value(item: object) -> dict[str, object]:
    value = getattr(item, "value", item)
    return value if isinstance(value, dict) else {}


def _event_id(*, stream_id: str, sequence: int, kind: str) -> str:
    digest = sha256(f"{stream_id}\0{sequence}\0{kind}".encode("utf-8")).hexdigest()
    return f"evt-{digest[:12]}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
