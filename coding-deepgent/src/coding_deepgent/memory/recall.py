from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from coding_deepgent.memory.schemas import MEMORY_TYPE_ORDER, MemoryRecord, MemoryType
from coding_deepgent.memory.service import MemoryService
from coding_deepgent.memory.store import MemoryStore, list_memory_records


def recall_memories(
    store: MemoryStore | None,
    *,
    service: MemoryService | None = None,
    project_scope: str = "default",
    agent_scope: str | None = None,
    memory_type: MemoryType | None = None,
    query: str = "",
    limit: int = 5,
) -> list[MemoryRecord]:
    if service is None and store is None:
        return []

    selected_types = (memory_type,) if memory_type is not None else MEMORY_TYPE_ORDER
    if service is not None:
        records = [
            durable.record
            for selected_type in selected_types
            for durable in service.list_records(
                project_scope=project_scope,
                memory_type=selected_type,
                agent_scope=agent_scope,
                limit=limit,
            )
        ]
    else:
        assert store is not None
        records = [
            record
            for selected_type in selected_types
            for record in list_memory_records(store, selected_type)
        ]
    query_terms = {term.casefold() for term in query.split()}
    if query_terms:
        records = [
            record
            for record in records
            if query_terms & set(record.search_text().casefold().split())
        ]
    records.sort(key=lambda record: (record.priority, record.identity_text()))
    return records[:limit]


def render_memories(records: Sequence[MemoryRecord]) -> str | None:
    if not records:
        return None

    grouped: dict[MemoryType, list[MemoryRecord]] = defaultdict(list)
    for record in records:
        grouped[record.type].append(record)

    lines = ["Relevant long-term memory:"]
    for memory_type in MEMORY_TYPE_ORDER:
        if memory_type not in grouped:
            continue
        lines.append(_type_heading(memory_type))
        for record in grouped[memory_type]:
            lines.extend(_render_record_lines(record))
    return "\n".join(lines)


def _type_heading(memory_type: MemoryType) -> str:
    headings: dict[MemoryType, str] = {
        "feedback": "Feedback memory:",
        "project": "Project memory:",
        "reference": "Reference memory:",
        "user": "User memory:",
    }
    return headings[memory_type]


def _render_record_lines(record: MemoryRecord) -> list[str]:
    if record.type == "feedback":
        return [
            f"- Rule: {record.rule}",
            f"  Why: {record.why}",
            f"  How to apply: {record.how_to_apply}",
        ]
    if record.type == "project":
        lines = [
            f"- Decision: {record.fact_or_decision}",
            f"  Why: {record.why}",
            f"  How to apply: {record.how_to_apply}",
        ]
        if record.effective_date is not None:
            lines.append(f"  Effective date: {record.effective_date}")
        return lines
    if record.type == "reference":
        return [
            f"- Label: {record.label}",
            f"  Pointer: {record.pointer}",
            f"  Purpose: {record.purpose}",
            f"  How to apply: {record.how_to_apply}",
        ]
    return [
        f"- Profile: {record.profile}",
        f"  Why it matters: {record.why_it_matters}",
        f"  How to apply: {record.how_to_apply}",
    ]
