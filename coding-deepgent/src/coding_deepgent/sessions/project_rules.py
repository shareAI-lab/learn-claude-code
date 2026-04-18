from __future__ import annotations

from coding_deepgent.rules import project_rules_signal

from .contributions import RecoveryBriefContribution, RecoveryBriefSection
from .records import LoadedSession


def recovery_brief_contribution() -> RecoveryBriefContribution:
    def render(loaded_session: LoadedSession) -> RecoveryBriefSection:
        return RecoveryBriefSection(
            title="Project rules:",
            lines=(project_rules_signal(loaded_session.context.workdir),),
        )

    return RecoveryBriefContribution(name="project_rules", render=render)
