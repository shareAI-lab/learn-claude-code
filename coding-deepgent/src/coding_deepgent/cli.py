from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import typer
from click.exceptions import ClickException
from typer.main import get_command

from coding_deepgent.app import agent_loop
from coding_deepgent.config import ProjectSettings, load_settings
from coding_deepgent.logging_config import configure_logging, safe_environment_snapshot
from coding_deepgent.renderers.text import (
    render_config_table,
    render_doctor_table,
    render_session_table,
)
from coding_deepgent.rendering import extract_text

app = typer.Typer(
    add_completion=False,
    help="Run the coding-deepgent LangChain cc product agent.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Inspect resolved configuration.")
sessions_app = typer.Typer(help="Inspect or resume recorded sessions.")
app.add_typer(config_app, name="config")
app.add_typer(sessions_app, name="sessions")


@dataclass(frozen=True)
class SessionSummary:
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
    settings_loader: Callable[[], ProjectSettings]
    list_sessions: Callable[[], Sequence[SessionSummary]]
    load_session: Callable[[str], list[dict[str, Any]]]
    run_prompt: Callable[[str, list[dict[str, Any]] | None], str]
    doctor_checks: Callable[[], Sequence[DoctorCheck]]


def default_session_dir() -> Path:
    configured = os.getenv("CODING_DEEPGENT_SESSION_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return load_settings().workdir / ".coding-deepgent" / "sessions"


def _dependency_status(module_name: str) -> str:
    return "installed" if importlib.util.find_spec(module_name) else "missing"


def _doctor_checks() -> Sequence[DoctorCheck]:
    settings = load_settings()
    safe_env = safe_environment_snapshot(os.environ)
    return [
        DoctorCheck(
            "openai_api_key",
            safe_env["OPENAI_API_KEY"],
            "Required only for live run commands.",
        ),
        DoctorCheck("model_name", "resolved", settings.model_name),
        DoctorCheck("workdir", "ready", str(settings.workdir)),
        DoctorCheck("session_dir", "ready", str(default_session_dir())),
        DoctorCheck("typer", _dependency_status("typer"), "CLI command surface."),
        DoctorCheck(
            "rich", _dependency_status("rich"), "Terminal rendering dependency."
        ),
        DoctorCheck(
            "structlog",
            _dependency_status("structlog"),
            "Structured local logging dependency.",
        ),
    ]


def _empty_sessions() -> Sequence[SessionSummary]:
    return []


def _missing_session(session_id: str) -> list[dict[str, Any]]:
    raise KeyError(f"Unknown session: {session_id}")


def build_cli_runtime() -> CliRuntime:
    return CliRuntime(
        settings_loader=load_settings,
        list_sessions=_empty_sessions,
        load_session=_missing_session,
        run_prompt=run_once,
        doctor_checks=_doctor_checks,
    )


def run_once(prompt: str, history: list[dict[str, Any]] | None = None) -> str:
    transcript = history if history is not None else []
    transcript.append({"role": "user", "content": prompt})
    return agent_loop(transcript)


def _emit_text(text: str) -> None:
    typer.echo(text or "(no response)")


def _config_rows(settings: ProjectSettings) -> list[tuple[str, str]]:
    safe_env = safe_environment_snapshot(os.environ)
    return [
        ("workdir", str(settings.workdir)),
        ("model_name", settings.model_name),
        ("openai_base_url", safe_env["OPENAI_BASE_URL"]),
        ("openai_api_key", safe_env["OPENAI_API_KEY"]),
        ("session_dir", str(default_session_dir())),
    ]


def _run_prompt(prompt: str, *, history: list[dict[str, Any]] | None = None) -> None:
    runtime = build_cli_runtime()
    try:
        result = runtime.run_prompt(prompt, history)
    except RuntimeError as exc:  # pragma: no cover - defensive CLI guard
        raise ClickException(str(exc)) from exc
    _emit_text(extract_text(result))


@app.callback(invoke_without_command=True)
def root(
    prompt: str | None = typer.Option(
        None, "--prompt", help="Run one prompt and exit."
    ),
) -> None:
    if prompt is not None:
        _run_prompt(prompt)
        raise typer.Exit()


@app.command("run")
def run_command(
    prompt: str = typer.Argument(..., help="Prompt to send to the agent."),
) -> None:
    _run_prompt(prompt)


@config_app.command("show")
def config_show() -> None:
    runtime = build_cli_runtime()
    typer.echo(render_config_table(_config_rows(runtime.settings_loader())))


@sessions_app.command("list")
def sessions_list() -> None:
    runtime = build_cli_runtime()
    sessions = [
        {
            "session_id": session.session_id,
            "updated_at": session.updated_at,
            "message_count": session.message_count,
            "workdir": session.workdir,
        }
        for session in runtime.list_sessions()
    ]
    typer.echo(render_session_table(sessions))


@sessions_app.command("resume")
def sessions_resume(
    session_id: str = typer.Argument(..., help="Session identifier to resume."),
    prompt: str | None = typer.Option(
        None, "--prompt", help="Optional prompt to continue the session."
    ),
) -> None:
    runtime = build_cli_runtime()
    try:
        history = runtime.load_session(session_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc

    if prompt is None:
        typer.echo(
            f"Loaded session {session_id} with {len(history)} messages. Re-run with --prompt to continue."
        )
        raise typer.Exit()

    _run_prompt(prompt, history=history)


@app.command("doctor")
def doctor() -> None:
    configure_logging()
    runtime = build_cli_runtime()
    checks = [
        {"name": check.name, "status": check.status, "detail": check.detail}
        for check in runtime.doctor_checks()
    ]
    typer.echo(render_doctor_table(checks))


def main(argv: list[str] | None = None) -> int:
    command = get_command(app)
    try:
        command.main(
            args=argv or [], prog_name="coding-deepgent", standalone_mode=False
        )
    except ClickException as exc:
        exc.show()
        return exc.exit_code
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        return 0
    return 0


def cli(argv: list[str] | None = None) -> int:
    return main(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":  # pragma: no cover
    cli()
