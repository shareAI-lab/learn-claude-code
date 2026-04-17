from __future__ import annotations

from typing import cast

from langchain.tools import ToolRuntime, tool

from coding_deepgent.memory.schemas import (
    DeleteMemoryInput,
    ListMemoryInput,
    MemoryRecord,
    MemoryType,
    SaveMemoryInput,
)
from coding_deepgent.memory.policy import evaluate_memory_quality
from coding_deepgent.memory.store import (
    delete_memory_record,
    list_memory_entries,
    list_memory_records,
    save_memory_record,
)


@tool(
    "save_memory",
    args_schema=SaveMemoryInput,
    description=(
        "Save durable long-term memory using one of four types: feedback, project, "
        "reference, or user. Save only non-derivable information that should remain "
        "useful across sessions. Do not save transient todos, current plans, task "
        "status, recovery notes, repository structure, duplicates, or relative dates."
    ),
)
def save_memory(
    type: str,
    runtime: ToolRuntime,
    source: str = "agent",
    profile: str | None = None,
    why_it_matters: str | None = None,
    rule: str | None = None,
    why: str | None = None,
    how_to_apply: str | None = None,
    fact_or_decision: str | None = None,
    effective_date: str | None = None,
    label: str | None = None,
    pointer: str | None = None,
    purpose: str | None = None,
) -> str:
    """Save structured long-term memory through the LangGraph store seam."""

    validated = SaveMemoryInput(
        type=cast(MemoryType, type),
        source=source,
        profile=profile,
        why_it_matters=why_it_matters,
        rule=rule,
        why=why,
        how_to_apply=how_to_apply,
        fact_or_decision=fact_or_decision,
        effective_date=effective_date,
        label=label,
        pointer=pointer,
        purpose=purpose,
        runtime=runtime,
    )
    store = runtime.store
    if store is None:
        return "Memory store is not configured; memory was not saved."
    record = MemoryRecord(
        type=validated.type,
        source=validated.source,
        profile=validated.profile,
        why_it_matters=validated.why_it_matters,
        rule=validated.rule,
        why=validated.why,
        how_to_apply=validated.how_to_apply,
        fact_or_decision=validated.fact_or_decision,
        effective_date=validated.effective_date,
        label=validated.label,
        pointer=validated.pointer,
        purpose=validated.purpose,
    )
    quality = evaluate_memory_quality(
        record, existing_records=list_memory_records(store, validated.type)
    )
    if not quality.allowed:
        return f"Memory not saved: {quality.reason}."

    key = save_memory_record(store, record)
    return f"Saved {validated.type} memory {key}."


@tool(
    "list_memory",
    args_schema=ListMemoryInput,
    description=(
        "List saved long-term memory entries. Optionally filter by one memory type. "
        "Use this before deleting or auditing memory."
    ),
)
def list_memory(
    runtime: ToolRuntime,
    type: str | None = None,
    limit: int = 20,
) -> str:
    store = runtime.store
    if store is None:
        return "Memory store is not configured; no memory entries are available."

    memory_types: tuple[MemoryType, ...] = (
        (cast(MemoryType, type),)
        if type is not None
        else ("feedback", "project", "reference", "user")
    )
    entries = [
        (memory_type, entry)
        for memory_type in memory_types
        for entry in list_memory_entries(store, memory_type)
    ][:limit]
    if not entries:
        return "No long-term memory entries found."

    lines = ["Long-term memory entries:"]
    for memory_type, entry in entries:
        lines.append(f"- [{memory_type}] {entry.key}: {_memory_entry_summary(entry.record)}")
    return "\n".join(lines)


@tool(
    "delete_memory",
    args_schema=DeleteMemoryInput,
    description=(
        "Delete one long-term memory entry by exact type and key. "
        "Use list_memory first to inspect keys."
    ),
)
def delete_memory(type: str, key: str, runtime: ToolRuntime) -> str:
    store = runtime.store
    if store is None:
        return "Memory store is not configured; memory was not deleted."
    deleted = delete_memory_record(store, memory_type=cast(MemoryType, type), key=key)
    if not deleted:
        return f"Memory not deleted: no {type} memory exists with key {key}."
    return f"Deleted {type} memory {key}."


def _memory_entry_summary(record: MemoryRecord) -> str:
    if record.type == "feedback":
        return str(record.rule)
    if record.type == "project":
        return str(record.fact_or_decision)
    if record.type == "reference":
        return f"{record.label} -> {record.pointer}"
    return str(record.profile)
