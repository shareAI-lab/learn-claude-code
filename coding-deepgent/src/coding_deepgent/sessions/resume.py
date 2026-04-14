from __future__ import annotations

from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
from typing import Any

from .ports import SessionStore
from .records import LoadedSession, SessionCompact, SessionEvidence

RESUME_CONTEXT_MESSAGE_PREFIX = (
    "Resumed session context. Use this brief as continuation context, not as a new user request."
)


@dataclass(frozen=True, slots=True)
class RecoveryBrief:
    session_id: str
    updated_at: str | None
    message_count: int
    active_todos: tuple[str, ...]
    recent_evidence: tuple[SessionEvidence, ...]
    recent_compacts: tuple[SessionCompact, ...]


def apply_resume_state(
    runtime_state: MutableMapping[str, Any],
    loaded_session: LoadedSession,
) -> None:
    runtime_state.clear()
    runtime_state.update(deepcopy(loaded_session.state))


def resume_session(
    store: SessionStore,
    *,
    session_id: str,
    workdir: Path,
    runtime_state: MutableMapping[str, Any],
    default_state_factory: Callable[[], dict[str, Any]] | None = None,
) -> LoadedSession:
    loaded_session = store.load_session(
        session_id=session_id,
        workdir=workdir,
        default_state_factory=default_state_factory,
    )
    apply_resume_state(runtime_state, loaded_session)
    return loaded_session


def build_recovery_brief(
    loaded_session: LoadedSession,
    *,
    evidence_limit: int = 5,
    compact_limit: int = 3,
) -> RecoveryBrief:
    active_todos = tuple(
        str(item.get("content", "")).strip()
        for item in loaded_session.state.get("todos", [])
        if isinstance(item, dict)
        and item.get("status") in {"pending", "in_progress"}
        and str(item.get("content", "")).strip()
    )
    return RecoveryBrief(
        session_id=loaded_session.summary.session_id,
        updated_at=loaded_session.summary.updated_at,
        message_count=loaded_session.summary.message_count,
        active_todos=active_todos,
        recent_evidence=tuple(loaded_session.evidence[-evidence_limit:]),
        recent_compacts=tuple(loaded_session.compacts[-compact_limit:]),
    )


def render_recovery_brief(brief: RecoveryBrief) -> str:
    lines = [
        f"Session: {brief.session_id}",
        f"Messages: {brief.message_count}",
        f"Updated: {brief.updated_at or 'unknown'}",
        "Active todos:",
    ]
    lines.extend(f"- {todo}" for todo in brief.active_todos)
    if not brief.active_todos:
        lines.append("- none")

    lines.append("Recent evidence:")
    lines.extend(
        f"- [{item.status}] {item.kind}: {item.summary}"
        for item in brief.recent_evidence
    )
    if not brief.recent_evidence:
        lines.append("- none")
    lines.append("Recent compacts:")
    lines.extend(
        f"- [{item.trigger}] {item.summary}"
        for item in brief.recent_compacts
    )
    if not brief.recent_compacts:
        lines.append("- none")
    return "\n".join(lines)


def build_resume_context_message(loaded_session: LoadedSession) -> dict[str, str]:
    return {
        "role": "system",
        "content": (
            f"{RESUME_CONTEXT_MESSAGE_PREFIX}\n\n"
            f"{render_recovery_brief(build_recovery_brief(loaded_session))}"
        ),
    }


def is_resume_context_message(message: dict[str, Any]) -> bool:
    return message.get("role") == "system" and str(
        message.get("content", "")
    ).startswith(RESUME_CONTEXT_MESSAGE_PREFIX)
