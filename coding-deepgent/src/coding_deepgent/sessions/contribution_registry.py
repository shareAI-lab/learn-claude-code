from __future__ import annotations

from .contributions import (
    CompactAssistContribution,
    CompactSummaryUpdateContribution,
    RecoveryBriefContribution,
    RuntimeStateContribution,
)
from .session_memory import (
    compact_assist_contribution,
    compact_summary_update_contribution,
    recovery_brief_contribution,
    runtime_state_contribution,
)

RUNTIME_STATE_CONTRIBUTIONS: tuple[RuntimeStateContribution, ...] = (
    runtime_state_contribution(),
)

RECOVERY_BRIEF_CONTRIBUTIONS: tuple[RecoveryBriefContribution, ...] = (
    recovery_brief_contribution(),
)

COMPACT_ASSIST_CONTRIBUTIONS: tuple[CompactAssistContribution, ...] = (
    compact_assist_contribution(),
)

COMPACT_SUMMARY_UPDATE_CONTRIBUTIONS: tuple[
    CompactSummaryUpdateContribution, ...
] = (
    compact_summary_update_contribution(),
)
