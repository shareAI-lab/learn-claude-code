from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from coding_deepgent.event_stream import append_event

EXTENSION_NAMESPACE = ("coding_deepgent_extension_lifecycle",)
ExtensionKind = Literal["skill", "mcp", "hook", "plugin"]
ExtensionStatus = Literal["installed", "enabled", "disabled", "failed"]


class ExtensionStore(Protocol):
    def put(
        self, namespace: tuple[str, ...], key: str, value: dict[str, object]
    ) -> None: ...
    def get(self, namespace: tuple[str, ...], key: str) -> object | None: ...
    def search(self, namespace: tuple[str, ...]) -> Iterable[object]: ...


class ExtensionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extension_id: str
    name: str = Field(..., min_length=1)
    kind: ExtensionKind
    source: str = Field(..., min_length=1)
    version: str | None = None
    status: ExtensionStatus = "installed"
    previous_status: ExtensionStatus | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


def register_extension(
    store: ExtensionStore,
    *,
    name: str,
    kind: ExtensionKind,
    source: str,
    version: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ExtensionRecord:
    existing = _find_by_name_kind(store, name=name, kind=kind)
    if existing is not None:
        return existing
    now = _now()
    record = ExtensionRecord(
        extension_id=_extension_id(name=name, kind=kind, created_at=now),
        name=name.strip(),
        kind=kind,
        source=source.strip(),
        version=version,
        metadata=metadata or {},
        created_at=now,
        updated_at=now,
    )
    return _save(store, record, event_kind="extension_registered")


def get_extension(store: ExtensionStore, extension_id: str) -> ExtensionRecord:
    item = store.get(EXTENSION_NAMESPACE, extension_id)
    if item is None:
        raise KeyError(f"Unknown extension: {extension_id}")
    return ExtensionRecord.model_validate(_item_value(item))


def list_extensions(store: ExtensionStore) -> list[ExtensionRecord]:
    return sorted(
        [
            ExtensionRecord.model_validate(_item_value(item))
            for item in store.search(EXTENSION_NAMESPACE)
        ],
        key=lambda item: item.extension_id,
    )


def enable_extension(store: ExtensionStore, extension_id: str) -> ExtensionRecord:
    record = get_extension(store, extension_id)
    return _transition(store, record, status="enabled", event_kind="extension_enabled")


def disable_extension(store: ExtensionStore, extension_id: str) -> ExtensionRecord:
    record = get_extension(store, extension_id)
    return _transition(store, record, status="disabled", event_kind="extension_disabled")


def update_extension(
    store: ExtensionStore,
    extension_id: str,
    *,
    version: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ExtensionRecord:
    record = get_extension(store, extension_id)
    updated = record.model_copy(
        update={
            "version": version if version is not None else record.version,
            "metadata": {**record.metadata, **(metadata or {})},
            "updated_at": _now(),
        }
    )
    return _save(store, updated, event_kind="extension_updated")


def rollback_extension(store: ExtensionStore, extension_id: str) -> ExtensionRecord:
    record = get_extension(store, extension_id)
    if record.previous_status is None:
        return record
    return _transition(
        store,
        record,
        status=record.previous_status,
        event_kind="extension_rollback",
    )


def _transition(
    store: ExtensionStore,
    record: ExtensionRecord,
    *,
    status: ExtensionStatus,
    event_kind: str,
) -> ExtensionRecord:
    return _save(
        store,
        record.model_copy(
            update={
                "status": status,
                "previous_status": record.status,
                "updated_at": _now(),
            }
        ),
        event_kind=event_kind,
    )


def _save(
    store: ExtensionStore,
    record: ExtensionRecord,
    *,
    event_kind: str,
) -> ExtensionRecord:
    store.put(EXTENSION_NAMESPACE, record.extension_id, record.model_dump())
    append_event(
        store,
        stream_id=f"extension:{record.extension_id}",
        kind=event_kind,
        payload={"extension_id": record.extension_id, "status": record.status},
    )
    return record


def _find_by_name_kind(
    store: ExtensionStore,
    *,
    name: str,
    kind: ExtensionKind,
) -> ExtensionRecord | None:
    for record in list_extensions(store):
        if record.name == name and record.kind == kind:
            return record
    return None


def _item_value(item: object) -> dict[str, object]:
    value = getattr(item, "value", item)
    return value if isinstance(value, dict) else {}


def _extension_id(*, name: str, kind: str, created_at: str) -> str:
    digest = sha256(f"{name}\0{kind}\0{created_at}".encode("utf-8")).hexdigest()
    return f"ext-{digest[:12]}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
