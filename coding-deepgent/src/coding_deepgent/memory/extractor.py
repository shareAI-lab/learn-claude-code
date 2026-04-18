from __future__ import annotations

import re
from collections.abc import Sequence

from coding_deepgent.memory.schemas import MemoryRecord
from coding_deepgent.memory.service import ExtractionCandidate

URL_RE = re.compile(r"https?://\S+")
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def extract_memory_candidates(candidate: ExtractionCandidate) -> list[MemoryRecord]:
    text = " ".join(candidate.text.split())
    lowered = text.casefold()
    records: list[MemoryRecord] = []

    if _looks_like_feedback(lowered):
        records.append(
            MemoryRecord(
                type="feedback",
                rule=_first_sentence(text),
                why="Auto-extracted from user/assistant interaction.",
                how_to_apply="Apply this guidance in future related actions unless a stronger project rule conflicts.",
                source="auto_extract",
            )
        )

    if URL_RE.search(text):
        records.append(
            MemoryRecord(
                type="reference",
                label="Auto-extracted external reference",
                pointer=URL_RE.search(text).group(0),  # type: ignore[union-attr]
                purpose="External resource mentioned during work.",
                how_to_apply="Use when later work refers to the same external system or document.",
                source="auto_extract",
            )
        )

    if _looks_like_project_fact(lowered):
        effective_date = DATE_RE.search(text)
        records.append(
            MemoryRecord(
                type="project",
                fact_or_decision=_first_sentence(text),
                why="Auto-extracted from a likely project decision or long-lived constraint.",
                how_to_apply="Treat as a project-level fact until contradicted by fresher evidence.",
                effective_date=effective_date.group(0) if effective_date else None,
                source="auto_extract",
            )
        )

    return _dedupe_records(records)


def _looks_like_feedback(lowered: str) -> bool:
    return any(
        phrase in lowered
        for phrase in (
            "do not ",
            "don't ",
            "must ",
            "before ",
            "prefer ",
            "always ",
        )
    )


def _looks_like_project_fact(lowered: str) -> bool:
    return any(
        phrase in lowered
        for phrase in (
            "because ",
            "deadline",
            "release",
            "migration",
            "we use ",
            "we are ",
        )
    )


def _first_sentence(text: str) -> str:
    return text.split(".")[0].strip() or text[:200].strip()


def _dedupe_records(records: Sequence[MemoryRecord]) -> list[MemoryRecord]:
    seen: set[tuple[str, str]] = set()
    result: list[MemoryRecord] = []
    for record in records:
        key = (record.type, record.identity_text())
        if key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result
