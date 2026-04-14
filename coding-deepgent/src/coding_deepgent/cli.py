from __future__ import annotations

import sys
from typing import Any

import typer
from click.exceptions import ClickException
from typer.main import get_command

from coding_deepgent import cli_service
from coding_deepgent.app import agent_loop
from coding_deepgent.logging_config import configure_logging
from coding_deepgent.renderers.text import (
    render_config_table,
    render_doctor_table,
    render_session_table,
)
from coding_deepgent.rendering import extract_text
from coding_deepgent.settings import build_openai_model

app = typer.Typer(
    add_completion=False,
    help="Run the coding-deepgent LangChain cc product agent.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Inspect resolved configuration.")
sessions_app = typer.Typer(help="Inspect or resume recorded sessions.")
app.add_typer(config_app, name="config")
app.add_typer(sessions_app, name="sessions")


def build_cli_runtime() -> cli_service.CliRuntime:
    return cli_service.build_cli_runtime(agent_loop)


def run_once(
    prompt: str,
    history: list[dict[str, object]] | None = None,
    session_state: dict[str, object] | None = None,
    session_id: str | None = None,
) -> str:
    return cli_service.run_once(
        prompt=prompt,
        run_agent=agent_loop,
        history=history,
        session_state=session_state,
        session_id=session_id,
        settings=build_cli_runtime().settings_loader(),
    )


def _emit_text(text: str) -> None:
    typer.echo(text or "(no response)")


def _run_prompt(
    prompt: str,
    *,
    history: list[dict[str, Any]] | None = None,
    session_state: dict[str, object] | None = None,
    session_id: str | None = None,
) -> None:
    runtime = build_cli_runtime()
    try:
        result = runtime.run_prompt(prompt, history, session_state, session_id)
    except RuntimeError as exc:  # pragma: no cover
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
    typer.echo(render_config_table(cli_service.config_rows(runtime.settings_loader())))


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
    compact_summary: str | None = typer.Option(
        None,
        "--compact-summary",
        help="Optional manual compact summary to use for continuation history.",
    ),
    generate_compact_summary: bool = typer.Option(
        False,
        "--generate-compact-summary",
        help="Generate a manual compact summary for continuation history.",
    ),
    compact_instructions: str | None = typer.Option(
        None,
        "--compact-instructions",
        help="Optional additional instructions for generated compact summary.",
    ),
    compact_keep_last: int = typer.Option(
        4,
        "--compact-keep-last",
        min=0,
        help="Number of recent messages to preserve after manual compaction.",
    ),
) -> None:
    runtime = build_cli_runtime()
    try:
        loaded = runtime.load_session(session_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc

    if prompt is None:
        if (
            compact_summary is not None
            or generate_compact_summary
            or compact_instructions is not None
        ):
            raise ClickException("compact options require --prompt.")
        typer.echo(cli_service.recovery_brief_text(loaded))
        typer.echo("Re-run with --prompt to continue.")
        raise typer.Exit()
    if compact_summary is not None and generate_compact_summary:
        raise ClickException(
            "--compact-summary and --generate-compact-summary are mutually exclusive."
        )
    if compact_instructions is not None and not generate_compact_summary:
        raise ClickException("--compact-instructions requires --generate-compact-summary.")

    try:
        if generate_compact_summary:
            history = cli_service.generated_compacted_continuation_history(
                loaded,
                summarizer=build_openai_model(runtime.settings_loader()),
                keep_last=compact_keep_last,
                custom_instructions=compact_instructions,
            )
        elif compact_summary is not None:
            history = cli_service.compacted_continuation_history(
                loaded,
                summary=compact_summary,
                keep_last=compact_keep_last,
            )
        else:
            history = cli_service.selected_continuation_history(loaded)
    except (RuntimeError, ValueError) as exc:
        raise ClickException(str(exc)) from exc

    _run_prompt(
        prompt,
        history=history,
        session_state=loaded.state,
        session_id=loaded.summary.session_id,
    )


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
