from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from collections.abc import Sequence
from typing import TYPE_CHECKING

from coding_deepgent.memory.schemas import MEMORY_TYPE_ORDER, MemoryRecord, MemoryType
from coding_deepgent.memory.store import MemoryEntry, MemoryStore, list_memory_entries

if TYPE_CHECKING:
    from coding_deepgent.memory.backend import DurableMemoryRecord

LONG_TERM_MEMORY_STATE_KEY = "long_term_memory"


class LongTermMemoryEntrySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1)
    type: MemoryType
    summary: str = Field(..., min_length=1)

    @field_validator("key", "summary")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value required")
        return value


class LongTermMemorySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[LongTermMemoryEntrySnapshot] = Field(default_factory=list)
    updated_at: str = Field(..., min_length=1)

    @field_validator("updated_at")
    @classmethod
    def _updated_at_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value required")
        return value


def build_long_term_memory_snapshot(
    store: MemoryStore | None,
    *,
    limit: int = 12,
) -> LongTermMemorySnapshot | None:
    if store is None:
        return None
    entries = [
        LongTermMemoryEntrySnapshot(
            key=entry.key,
            type=entry.record.type,
            summary=_memory_entry_summary(entry),
        )
        for memory_type in MEMORY_TYPE_ORDER
        for entry in list_memory_entries(store, memory_type)
    ][:limit]
    if not entries:
        return None
    return LongTermMemorySnapshot(
        entries=entries,
        updated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )


def build_long_term_memory_snapshot_from_records(
    records: Sequence[MemoryRecord],
    *,
    limit: int = 12,
) -> LongTermMemorySnapshot | None:
    entries = [
        LongTermMemoryEntrySnapshot(
            key=f"record-{index}",
            type=record.type,
            summary=_record_summary(record),
        )
        for index, record in enumerate(records[:limit], start=1)
    ]
    if not entries:
        return None
    return LongTermMemorySnapshot(
        entries=entries,
        updated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )


def build_long_term_memory_snapshot_from_durable_records(
    records: Sequence["DurableMemoryRecord"],
    *,
    limit: int = 12,
) -> LongTermMemorySnapshot | None:
    entries = [
        LongTermMemoryEntrySnapshot(
            key=record.id,
            type=record.record.type,
            summary=_record_summary(record.record),
        )
        for record in records[:limit]
    ]
    if not entries:
        return None
    return LongTermMemorySnapshot(
        entries=entries,
        updated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )


def read_long_term_memory_snapshot(
    state: Mapping[str, Any],
) -> LongTermMemorySnapshot | None:
    value = state.get(LONG_TERM_MEMORY_STATE_KEY)
    if not isinstance(value, dict):
        return None
    try:
        return LongTermMemorySnapshot.model_validate(value)
    except ValidationError:
        return None


def write_long_term_memory_snapshot(
    state: MutableMapping[str, Any],
    snapshot: LongTermMemorySnapshot | None,
) -> None:
    if snapshot is None:
        state.pop(LONG_TERM_MEMORY_STATE_KEY, None)
        return
    state[LONG_TERM_MEMORY_STATE_KEY] = snapshot.model_dump()


def _memory_entry_summary(entry: MemoryEntry) -> str:
    record = entry.record
    return _record_summary(record)


def _record_summary(record: MemoryRecord) -> str:
    if record.type == "feedback":
        return str(record.rule)
    if record.type == "project":
        return str(record.fact_or_decision)
    if record.type == "reference":
        return f"{record.label} -> {record.pointer}"
    return str(record.profile)
