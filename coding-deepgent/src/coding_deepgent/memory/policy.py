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
    "derivable_information",
    "relative_time",
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
DERIVABLE_INFORMATION_PHRASES = (
    "api endpoint",
    "api endpoints",
    "file list",
    "file path",
    "package.json",
    "readme.md",
    "src/",
    "tests/",
)
RELATIVE_TIME_PHRASES = (
    "today",
    "tomorrow",
    "yesterday",
    "next week",
    "this week",
    "next month",
    "this month",
    "next monday",
    "next tuesday",
    "next wednesday",
    "next thursday",
    "next friday",
    "next saturday",
    "next sunday",
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
    normalized = normalize_memory_content(record.search_text())
    if len(normalized.split()) <= 2:
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

    if record.type == "project" and any(
        phrase in normalized for phrase in DERIVABLE_INFORMATION_PHRASES
    ):
        return MemoryQualityDecision(
            allowed=False,
            category="derivable_information",
            reason="memory looks derivable from repository structure or code",
        )

    if record.type == "project" and any(
        phrase in normalized for phrase in RELATIVE_TIME_PHRASES
    ):
        return MemoryQualityDecision(
            allowed=False,
            category="relative_time",
            reason="project memory must use absolute dates instead of relative time",
        )

    dedupe_key = normalize_memory_content(record.identity_text())
    for existing in existing_records:
        if normalize_memory_content(existing.identity_text()) == dedupe_key:
            return MemoryQualityDecision(
                allowed=False,
                category="duplicate",
                reason=f"duplicate memory already exists in {record.type}",
            )

    return MemoryQualityDecision(
        allowed=True,
        category="accepted",
        reason="memory is durable reusable knowledge",
    )
