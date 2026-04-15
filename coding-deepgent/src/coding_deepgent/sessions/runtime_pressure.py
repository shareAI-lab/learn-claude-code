from __future__ import annotations

from collections import Counter

from .contributions import RecoveryBriefContribution, RecoveryBriefSection
from .records import LoadedSession

RUNTIME_PRESSURE_EVENT_KINDS = ("microcompact", "auto_compact", "reactive_compact")


def recovery_brief_contribution() -> RecoveryBriefContribution:
    def render(loaded_session: LoadedSession) -> RecoveryBriefSection | None:
        counts = Counter(
            str(item.metadata.get("event_kind"))
            for item in loaded_session.evidence
            if item.kind == "runtime_event"
            and isinstance(item.metadata, dict)
            and item.metadata.get("event_kind") in RUNTIME_PRESSURE_EVENT_KINDS
        )
        if not counts:
            return None
        lines = tuple(
            f"- {event_kind}: {counts.get(event_kind, 0)}"
            for event_kind in RUNTIME_PRESSURE_EVENT_KINDS
            if counts.get(event_kind, 0) > 0
        )
        return RecoveryBriefSection(title="Runtime pressure:", lines=lines or ("- none",))

    return RecoveryBriefContribution(name="runtime_pressure", render=render)
