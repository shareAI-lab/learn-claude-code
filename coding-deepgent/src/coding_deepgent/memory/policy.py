from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from coding_deepgent.memory.schemas import MemoryRecord

MemoryQualityCategory = Literal[
    "accepted",
    "duplicate",
    "too_short",
    "transient_state",
]

TRANSIENT_MEMORY_PHRASES = (
    "active todo",
    "completed task",
    "current plan",
    "current task",
    "currently ",
    "in progress",
    "next step",
    "next steps",
    "pending task",
    "right now",
    "this session",
    "todo:",
    "todos:",
    "working on",
)


@dataclass(frozen=True, slots=True)
class MemoryQualityDecision:
    allowed: bool
    category: MemoryQualityCategory
    reason: str


def normalize_memory_content(content: str) -> str:
    return " ".join(content.casefold().split())


def evaluate_memory_quality(
    record: MemoryRecord,
    *,
    existing_records: Sequence[MemoryRecord] = (),
) -> MemoryQualityDecision:
    normalized = normalize_memory_content(record.content)
    if len(normalized.split()) <= 1:
        return MemoryQualityDecision(
            allowed=False,
            category="too_short",
            reason="memory is too short to be reusable long-term knowledge",
        )

    if any(phrase in normalized for phrase in TRANSIENT_MEMORY_PHRASES):
        return MemoryQualityDecision(
            allowed=False,
            category="transient_state",
            reason="memory looks like transient task/session state",
        )

    for existing in existing_records:
        if normalize_memory_content(existing.content) == normalized:
            return MemoryQualityDecision(
                allowed=False,
                category="duplicate",
                reason=f"duplicate memory already exists in {record.namespace}",
            )

    return MemoryQualityDecision(
        allowed=True,
        category="accepted",
        reason="memory is durable reusable knowledge",
    )
