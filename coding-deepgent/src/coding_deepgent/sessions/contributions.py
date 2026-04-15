from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .records import LoadedSession


@dataclass(frozen=True, slots=True)
class RuntimeStateContribution:
    key: str
    coerce: Callable[[Mapping[str, Any]], object | None]


@dataclass(frozen=True, slots=True)
class RecoveryBriefSection:
    title: str
    lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecoveryBriefContribution:
    name: str
    render: Callable[[LoadedSession], RecoveryBriefSection | None]


@dataclass(frozen=True, slots=True)
class CompactAssistContribution:
    name: str
    render: Callable[[LoadedSession], str | None]


@dataclass(frozen=True, slots=True)
class CompactSummaryUpdateContribution:
    name: str
    update: Callable[[LoadedSession, str], bool]


def coerce_runtime_state_contributions(
    state: Mapping[str, Any],
    contributions: Sequence[RuntimeStateContribution],
) -> dict[str, object]:
    coerced: dict[str, object] = {}
    for contribution in contributions:
        value = contribution.coerce(state)
        if value is not None:
            coerced[contribution.key] = value
    return coerced


def build_recovery_brief_sections(
    loaded_session: LoadedSession,
    contributions: Sequence[RecoveryBriefContribution],
) -> tuple[RecoveryBriefSection, ...]:
    sections: list[RecoveryBriefSection] = []
    for contribution in contributions:
        section = contribution.render(loaded_session)
        if section is not None:
            sections.append(section)
    return tuple(sections)


def compact_assist_text(
    loaded_session: LoadedSession,
    contributions: Sequence[CompactAssistContribution],
) -> str | None:
    parts: list[str] = []
    for contribution in contributions:
        text = contribution.render(loaded_session)
        if text and text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts) if parts else None


def apply_compact_summary_update_contributions(
    loaded_session: LoadedSession,
    *,
    summary: str,
    contributions: Sequence[CompactSummaryUpdateContribution],
) -> tuple[str, ...]:
    updated: list[str] = []
    for contribution in contributions:
        if contribution.update(loaded_session, summary):
            updated.append(contribution.name)
    return tuple(updated)
