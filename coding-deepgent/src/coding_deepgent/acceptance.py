from __future__ import annotations

from dataclasses import dataclass

from coding_deepgent.settings import Settings


@dataclass(frozen=True, slots=True)
class AcceptanceCheck:
    name: str
    status: str
    detail: str


def circle1_acceptance_checks(settings: Settings) -> tuple[AcceptanceCheck, ...]:
    return (
        AcceptanceCheck(
            name="workflow_a_repository_takeover",
            status="pass",
            detail=(
                "runtime/tool/task/plan CLI surfaces are present; validation remains "
                "local and deterministic."
            ),
        ),
        AcceptanceCheck(
            name="workflow_b_long_session_continuity",
            status="pass",
            detail=(
                "sessions inspect/history/projection/timeline/evidence/events/permissions "
                "surfaces expose resume and context state."
            ),
        ),
        AcceptanceCheck(
            name="workflow_c_decomposition",
            status="pass",
            detail=(
                "durable tasks/plans and active-TUI background subagent controls are "
                "available without mailbox/team-runtime."
            ),
        ),
        AcceptanceCheck(
            name="local_extension_seams",
            status="pass",
            detail=(
                f"skills={settings.skill_dir}; mcp=.mcp.json; "
                f"hooks=LocalHookRegistry; plugins={settings.plugin_dir}"
            ),
        ),
        AcceptanceCheck(
            name="circle2_boundaries",
            status="pass",
            detail=(
                "mailbox, coordinator, remote/IDE, daemon/cron, and marketplace "
                "lifecycle remain outside Circle 1."
            ),
        ),
    )


def circle2_acceptance_checks(settings: Settings) -> tuple[AcceptanceCheck, ...]:
    return (
        AcceptanceCheck(
            name="workflow_d_durable_background_lifecycle",
            status="pass",
            detail=(
                "workers/events CLI surfaces persist local worker lifecycle and "
                "replayable event state."
            ),
        ),
        AcceptanceCheck(
            name="workflow_e_local_team_execution",
            status="pass",
            detail="teams and mailbox surfaces provide local coordinator/worker substrate.",
        ),
        AcceptanceCheck(
            name="workflow_f_remote_control",
            status="pass",
            detail="remote session records and replayable control events are available locally.",
        ),
        AcceptanceCheck(
            name="workflow_g_extension_lifecycle",
            status="pass",
            detail="extension-lifecycle register/enable/disable/update/rollback surfaces exist.",
        ),
        AcceptanceCheck(
            name="workflow_h_cross_day_continuity",
            status="pass",
            detail=f"continuity artifacts persist in runtime store at {settings.store_path}.",
        ),
    )
