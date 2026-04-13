from __future__ import annotations

from collections.abc import Sequence

from coding_deepgent.memory.schemas import MemoryNamespace, MemoryRecord
from coding_deepgent.memory.store import MemoryStore, list_memory_records


def recall_memories(
    store: MemoryStore | None,
    *,
    namespace: MemoryNamespace = "project",
    query: str = "",
    limit: int = 5,
) -> list[MemoryRecord]:
    if store is None:
        return []

    records = list_memory_records(store, namespace)
    query_terms = {term.casefold() for term in query.split()}
    if query_terms:
        records = [
            record
            for record in records
            if query_terms & set(record.content.casefold().split())
        ]
    return records[:limit]


def render_memories(records: Sequence[MemoryRecord]) -> str | None:
    if not records:
        return None
    lines = ["Relevant long-term memory:"]
    lines.extend(f"- [{record.namespace}] {record.content}" for record in records)
    return "\n".join(lines)
