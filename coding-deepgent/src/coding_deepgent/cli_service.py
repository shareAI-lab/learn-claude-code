from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from coding_deepgent.compact import (
    compact_messages_with_summary,
    generate_compact_summary,
)
from coding_deepgent.logging_config import safe_environment_snapshot
from coding_deepgent.settings import Settings, load_settings
from coding_deepgent.sessions import (
    LoadedSession,
    SessionLoadError,
    build_recovery_brief,
    build_resume_context_message,
    render_recovery_brief,
)
from coding_deepgent.sessions.contribution_registry import (
    COMPACT_ASSIST_CONTRIBUTIONS,
    COMPACT_SUMMARY_UPDATE_CONTRIBUTIONS,
)
from coding_deepgent.sessions.contributions import (
    apply_compact_summary_update_contributions,
    compact_assist_text,
)
from coding_deepgent.sessions.service import (
    list_recorded_sessions,
    load_recorded_session,
    run_prompt_with_recording,
)


@dataclass(frozen=True)
class SessionSummaryView:
    session_id: str
    updated_at: str
    message_count: int
    workdir: str


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class CliRuntime:
    settings_loader: Callable[[], Settings]
    list_sessions: Callable[[], Sequence[SessionSummaryView]]
    load_session: Callable[[str], LoadedSession]
    run_prompt: Callable[
        [str, list[dict[str, Any]] | None, dict[str, Any] | None, str | None], str
    ]
    doctor_checks: Callable[[], Sequence[DoctorCheck]]


def default_session_dir(settings: Settings) -> Path:
    configured = os.getenv("CODING_DEEPGENT_SESSION_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return settings.session_dir


def dependency_status(module_name: str) -> str:
    return "installed" if importlib.util.find_spec(module_name) else "missing"


def doctor_checks(settings: Settings) -> Sequence[DoctorCheck]:
    safe_env = safe_environment_snapshot(os.environ)
    return [
        DoctorCheck(
            "openai_api_key",
            safe_env["OPENAI_API_KEY"],
            "Required only for live run commands.",
        ),
        DoctorCheck("model_name", "resolved", settings.model_name),
        DoctorCheck("workdir", "ready", str(settings.workdir)),
        DoctorCheck("session_dir", "ready", str(default_session_dir(settings))),
        DoctorCheck("typer", dependency_status("typer"), "CLI command surface."),
        DoctorCheck("rich", dependency_status("rich"), "Terminal rendering dependency."),
        DoctorCheck(
            "structlog",
            dependency_status("structlog"),
            "Structured local logging dependency.",
        ),
    ]


def recorded_sessions(settings: Settings) -> Sequence[SessionSummaryView]:
    return [
        SessionSummaryView(
            session_id=summary.session_id,
            updated_at=summary.updated_at or "unknown",
            message_count=summary.message_count,
            workdir=str(summary.workdir),
        )
        for summary in list_recorded_sessions(settings)
    ]


def load_session(settings: Settings, session_id: str) -> LoadedSession:
    try:
        return load_recorded_session(settings, session_id)
    except SessionLoadError as exc:
        raise KeyError(str(exc)) from exc


def run_once(
    *,
    settings: Settings,
    prompt: str,
    run_agent: Callable[..., str],
    history: list[dict[str, Any]] | None = None,
    session_state: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> str:
    return run_prompt_with_recording(
        settings=settings,
        prompt=prompt,
        run_agent=run_agent,
        history=history,
        session_state=session_state,
        session_id=session_id,
    )


def recovery_brief_text(loaded: LoadedSession) -> str:
    return render_recovery_brief(build_recovery_brief(loaded))


def continuation_history(loaded: LoadedSession) -> list[dict[str, Any]]:
    return [
        build_resume_context_message(loaded),
        *(dict(message) for message in loaded.history),
    ]


def selected_continuation_history(loaded: LoadedSession) -> list[dict[str, Any]]:
    return [
        build_resume_context_message(loaded),
        *[dict(message) for message in loaded.compacted_history],
    ]


def compacted_continuation_history(
    loaded: LoadedSession,
    *,
    summary: str,
    keep_last: int = 4,
) -> list[dict[str, Any]]:
    artifact = compact_messages_with_summary(
        [dict(message) for message in loaded.history],
        summary=summary,
        keep_last=keep_last,
    )
    return [
        build_resume_context_message(loaded),
        *artifact.messages,
    ]


def generated_compacted_continuation_history(
    loaded: LoadedSession,
    *,
    summarizer: Any,
    keep_last: int = 4,
    custom_instructions: str | None = None,
) -> list[dict[str, Any]]:
    summary = generate_compact_summary(
        [dict(message) for message in loaded.history],
        summarizer,
        custom_instructions=custom_instructions,
        assist_context=compact_assist_text(loaded, COMPACT_ASSIST_CONTRIBUTIONS),
    )
    apply_compact_summary_update_contributions(
        loaded,
        summary=summary,
        contributions=COMPACT_SUMMARY_UPDATE_CONTRIBUTIONS,
    )
    return compacted_continuation_history(
        loaded,
        summary=summary,
        keep_last=keep_last,
    )


def config_rows(settings: Settings) -> list[tuple[str, str]]:
    safe_env = safe_environment_snapshot(os.environ)
    return [
        ("workdir", str(settings.workdir)),
        ("model_name", settings.model_name),
        ("openai_base_url", safe_env["OPENAI_BASE_URL"]),
        ("openai_api_key", safe_env["OPENAI_API_KEY"]),
        ("session_dir", str(default_session_dir(settings))),
    ]


def build_cli_runtime(
    run_agent: Callable[..., str],
    *,
    settings_loader: Callable[[], Settings] | None = None,
) -> CliRuntime:
    active_settings_loader = settings_loader or load_settings
    return CliRuntime(
        settings_loader=active_settings_loader,
        list_sessions=lambda: recorded_sessions(active_settings_loader()),
        load_session=lambda session_id: load_session(
            active_settings_loader(), session_id
        ),
        run_prompt=lambda prompt, history, session_state, session_id: run_once(
            settings=active_settings_loader(),
            prompt=prompt,
            run_agent=run_agent,
            history=history,
            session_state=session_state,
            session_id=session_id,
        ),
        doctor_checks=lambda: doctor_checks(active_settings_loader()),
    )
