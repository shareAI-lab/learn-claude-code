from __future__ import annotations

from .contributions import RecoveryBriefContribution, RecoveryBriefSection
from .records import LoadedSession


def recovery_brief_contribution() -> RecoveryBriefContribution:
    def render(loaded_session: LoadedSession) -> RecoveryBriefSection | None:
        notifications = [
            item
            for item in loaded_session.evidence
            if item.kind == "subagent_notification"
        ][-3:]
        if not notifications:
            return None
        return RecoveryBriefSection(
            title="Subagent activity:",
            lines=tuple(
                f"- [{item.status}] {item.summary}" for item in notifications
            ),
        )

    return RecoveryBriefContribution(name="subagent_activity", render=render)
