from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Protocol

from coding_deepgent.memory.schemas import MemoryRecord, MemoryType

MEMORY_ROOT_NAMESPACE = "coding_deepgent_memory"


class MemoryStore(Protocol):
    def put(
        self, namespace: tuple[str, ...], key: str, value: dict[str, object]
    ) -> None: ...
    def delete(self, namespace: tuple[str, ...], key: str) -> None: ...
    def search(self, namespace: tuple[str, ...]) -> Iterable[object]: ...


def memory_namespace(memory_type: MemoryType) -> tuple[str, ...]:
    return (MEMORY_ROOT_NAMESPACE, memory_type)


def memory_key(record: MemoryRecord) -> str:
    digest = sha256(f"{record.type}\0{record.identity_text()}".encode("utf-8")).hexdigest()
    return digest[:16]


def save_memory_record(store: MemoryStore, record: MemoryRecord) -> str:
    key = memory_key(record)
    store.put(memory_namespace(record.type), key, record.model_dump())
    return key


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    key: str
    record: MemoryRecord


def list_memory_records(
    store: MemoryStore, memory_type: MemoryType
) -> list[MemoryRecord]:
    return [entry.record for entry in list_memory_entries(store, memory_type)]


def list_memory_entries(
    store: MemoryStore, memory_type: MemoryType
) -> list[MemoryEntry]:
    records: list[MemoryEntry] = []
    for item in store.search(memory_namespace(memory_type)):
        value = getattr(item, "value", item)
        key = getattr(item, "key", None)
        if isinstance(value, dict) and value and isinstance(key, str):
            records.append(
                MemoryEntry(key=key, record=MemoryRecord.model_validate(value))
            )
    return records


def delete_memory_record(store: MemoryStore, *, memory_type: MemoryType, key: str) -> bool:
    existing_keys = {entry.key for entry in list_memory_entries(store, memory_type)}
    if key not in existing_keys:
        return False
    store.delete(memory_namespace(memory_type), key)
    return True
