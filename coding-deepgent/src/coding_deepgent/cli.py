from __future__ import annotations

import sys
from typing import Any

import typer
from click.exceptions import ClickException
from typer.main import get_command
from typing import cast

from coding_deepgent import cli_service
from coding_deepgent.app import agent_loop, build_container
from coding_deepgent.logging_config import configure_logging
from coding_deepgent.memory.backend import MemoryJobStatus, migrate_memory_schema
from coding_deepgent.memory.schemas import MemoryType
from coding_deepgent.renderers.text import (
    render_config_table,
    render_doctor_table,
    render_session_table,
)
from coding_deepgent.rendering import extract_text
from coding_deepgent.settings import build_openai_model
from coding_deepgent.sessions.records import TranscriptProjection
from coding_deepgent.sessions.session_memory import write_session_memory_artifact

app = typer.Typer(
    add_completion=False,
    help="Run the coding-deepgent LangChain cc product agent.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Inspect resolved configuration.")
sessions_app = typer.Typer(help="Inspect or resume recorded sessions.")
memory_app = typer.Typer(help="Manage durable long-term memory backend and jobs.")
app.add_typer(config_app, name="config")
app.add_typer(sessions_app, name="sessions")
app.add_typer(memory_app, name="memory")


def build_cli_runtime() -> cli_service.CliRuntime:
    return cli_service.build_cli_runtime(agent_loop)


def run_once(
    prompt: str,
    history: list[dict[str, object]] | None = None,
    session_state: dict[str, object] | None = None,
    session_id: str | None = None,
    transcript_projection: TranscriptProjection | None = None,
) -> str:
    return cli_service.run_once(
        prompt=prompt,
        run_agent=agent_loop,
        history=history,
        session_state=session_state,
        session_id=session_id,
        transcript_projection=transcript_projection,
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
    transcript_projection: TranscriptProjection | None = None,
) -> None:
    runtime = build_cli_runtime()
    try:
        result = runtime.run_prompt(
            prompt,
            history,
            session_state,
            session_id,
            transcript_projection,
        )
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
    session_memory: str | None = typer.Option(
        None,
        "--session-memory",
        help="Optional explicit session-memory artifact to persist and use for this resumed run.",
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
            session_memory is not None
            or
            compact_summary is not None
            or generate_compact_summary
            or compact_instructions is not None
        ):
            raise ClickException("session continuation options require --prompt.")
        typer.echo(cli_service.recovery_brief_text(loaded))
        typer.echo("Re-run with --prompt to continue.")
        raise typer.Exit()
    if session_memory is not None:
        try:
            write_session_memory_artifact(
                loaded.state,
                content=session_memory,
                message_count=loaded.summary.message_count,
            )
        except ValueError as exc:
            raise ClickException(str(exc)) from exc
    if compact_summary is not None and generate_compact_summary:
        raise ClickException(
            "--compact-summary and --generate-compact-summary are mutually exclusive."
        )
    if compact_instructions is not None and not generate_compact_summary:
        raise ClickException("--compact-instructions requires --generate-compact-summary.")

    try:
        transcript_projection = None
        if generate_compact_summary:
            history = cli_service.generated_compacted_continuation_history(
                loaded,
                summarizer=build_openai_model(runtime.settings_loader()),
                keep_last=compact_keep_last,
                custom_instructions=compact_instructions,
            )
            transcript_projection = cli_service.compacted_history_projection(
                loaded,
                history,
            )
        elif compact_summary is not None:
            history = cli_service.compacted_continuation_history(
                loaded,
                summary=compact_summary,
                keep_last=compact_keep_last,
            )
            transcript_projection = cli_service.compacted_history_projection(
                loaded,
                history,
            )
        else:
            history = cli_service.selected_continuation_history(loaded)
            transcript_projection = cli_service.selected_continuation_projection(
                loaded
            )
    except (RuntimeError, ValueError) as exc:
        raise ClickException(str(exc)) from exc

    _run_prompt(
        prompt,
        history=history,
        session_state=loaded.state,
        session_id=loaded.summary.session_id,
        transcript_projection=transcript_projection,
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


@memory_app.command("migrate")
def memory_migrate() -> None:
    container = build_container()
    migrate_memory_schema(container.memory_backend.engine())
    typer.echo("Memory backend schema is ready.")


@memory_app.command("jobs")
def memory_jobs(
    status: str | None = typer.Option(
        None, "--status", help="Optional job status filter."
    ),
    agent_scope: str | None = typer.Option(
        None, "--agent-scope", help="Optional agent scope filter."
    ),
    job_type: str | None = typer.Option(
        None, "--job-type", help="Optional job type filter."
    ),
    limit: int = typer.Option(20, "--limit", min=1, max=100),
) -> None:
    container = build_container()
    settings = build_cli_runtime().settings_loader()
    status_filter = MemoryJobStatus(status) if status is not None else None
    jobs = container.memory_backend.service().list_jobs(
        project_scope=str(settings.workdir),
        agent_scope=agent_scope,
        job_type=job_type,
        status=status_filter,
        limit=limit,
    )
    if not jobs:
        typer.echo("No memory jobs found.")
        raise typer.Exit()
    for job in jobs:
        typer.echo(
            f"{job.id} {job.job_type} {job.status.value} scope={job.agent_scope or 'global'} dedupe={job.dedupe_key}"
        )


@memory_app.command("records")
def memory_records(
    memory_type: str | None = typer.Option(
        None, "--type", help="Optional memory type filter."
    ),
    agent_scope: str | None = typer.Option(
        None, "--agent-scope", help="Optional agent scope filter."
    ),
    limit: int = typer.Option(20, "--limit", min=1, max=100),
) -> None:
    container = build_container()
    settings = build_cli_runtime().settings_loader()
    records = container.memory_backend.service().list_records(
        project_scope=str(settings.workdir),
        memory_type=cast(MemoryType, memory_type) if memory_type is not None else None,
        agent_scope=agent_scope,
        limit=limit,
    )
    if not records:
        typer.echo("No memory records found.")
        raise typer.Exit()
    for record in records:
        typer.echo(
            f"{record.id} {record.record.type} scope={record.agent_scope or 'global'} status={record.status.value} source={record.source}"
        )


@memory_app.command("agent-scopes")
def memory_agent_scopes() -> None:
    container = build_container()
    settings = build_cli_runtime().settings_loader()
    scopes = container.memory_backend.service().list_agent_scopes(
        project_scope=str(settings.workdir)
    )
    if not scopes:
        typer.echo("No agent memory scopes found.")
        raise typer.Exit()
    for scope in scopes:
        typer.echo(scope)


@memory_app.command("worker-run-once")
def memory_worker_run_once() -> None:
    container = build_container()
    job = container.memory_backend.service().process_next_job()
    if job is None:
        typer.echo("No memory job available.")
        raise typer.Exit()
    typer.echo(f"Processed memory job {job.id} -> {job.status.value}")


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
