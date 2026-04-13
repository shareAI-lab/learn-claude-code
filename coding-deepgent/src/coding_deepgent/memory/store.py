from __future__ import annotations

from hashlib import sha256
from typing import Iterable, Protocol

from coding_deepgent.memory.schemas import MemoryNamespace, MemoryRecord

MEMORY_ROOT_NAMESPACE = "coding_deepgent_memory"


class MemoryStore(Protocol):
    def put(
        self, namespace: tuple[str, ...], key: str, value: dict[str, object]
    ) -> None: ...
    def search(self, namespace: tuple[str, ...]) -> Iterable[object]: ...


def memory_namespace(namespace: MemoryNamespace) -> tuple[str, ...]:
    return (MEMORY_ROOT_NAMESPACE, namespace)


def memory_key(record: MemoryRecord) -> str:
    digest = sha256(f"{record.namespace}\0{record.content}".encode("utf-8")).hexdigest()
    return digest[:16]


def save_memory_record(store: MemoryStore, record: MemoryRecord) -> str:
    key = memory_key(record)
    store.put(memory_namespace(record.namespace), key, record.model_dump())
    return key


def list_memory_records(
    store: MemoryStore, namespace: MemoryNamespace
) -> list[MemoryRecord]:
    records: list[MemoryRecord] = []
    for item in store.search(memory_namespace(namespace)):
        value = getattr(item, "value", item)
        if isinstance(value, dict) and value:
            records.append(MemoryRecord.model_validate(value))
    return records
