from __future__ import annotations

from coding_deepgent.memory.state_snapshot import (
    LONG_TERM_MEMORY_STATE_KEY,
    read_long_term_memory_snapshot,
)

from .contributions import (
    RecoveryBriefContribution,
    RecoveryBriefSection,
    RuntimeStateContribution,
)
from .records import LoadedSession


def runtime_state_contribution() -> RuntimeStateContribution:
    return RuntimeStateContribution(
        key=LONG_TERM_MEMORY_STATE_KEY,
        coerce=lambda state: (
            snapshot.model_dump()
            if (snapshot := read_long_term_memory_snapshot(state)) is not None
            else None
        ),
    )


def recovery_brief_contribution() -> RecoveryBriefContribution:
    def render(loaded_session: LoadedSession) -> RecoveryBriefSection:
        snapshot = read_long_term_memory_snapshot(loaded_session.state)
        lines = (
            ("- none",)
            if snapshot is None or not snapshot.entries
            else tuple(
                f"- [{entry.type}] {entry.summary} (key={entry.key})"
                for entry in snapshot.entries
            )
        )
        return RecoveryBriefSection(title="Long-term memory:", lines=lines)

    return RecoveryBriefContribution(name=LONG_TERM_MEMORY_STATE_KEY, render=render)
