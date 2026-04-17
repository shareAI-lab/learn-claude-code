from __future__ import annotations

from .contributions import (
    CompactAssistContribution,
    CompactSummaryUpdateContribution,
    RecoveryBriefContribution,
    RuntimeStateContribution,
)
from .long_term_memory import (
    recovery_brief_contribution as long_term_memory_recovery_brief_contribution,
    runtime_state_contribution as long_term_memory_runtime_state_contribution,
)
from .session_memory import (
    compact_assist_contribution,
    compact_summary_update_contribution,
    recovery_brief_contribution,
    runtime_state_contribution,
)
from .runtime_pressure import recovery_brief_contribution as runtime_pressure_recovery_brief_contribution

RUNTIME_STATE_CONTRIBUTIONS: tuple[RuntimeStateContribution, ...] = (
    long_term_memory_runtime_state_contribution(),
    runtime_state_contribution(),
)

RECOVERY_BRIEF_CONTRIBUTIONS: tuple[RecoveryBriefContribution, ...] = (
    long_term_memory_recovery_brief_contribution(),
    recovery_brief_contribution(),
    runtime_pressure_recovery_brief_contribution(),
)

COMPACT_ASSIST_CONTRIBUTIONS: tuple[CompactAssistContribution, ...] = (
    compact_assist_contribution(),
)

COMPACT_SUMMARY_UPDATE_CONTRIBUTIONS: tuple[
    CompactSummaryUpdateContribution, ...
] = (
    compact_summary_update_contribution(),
)
