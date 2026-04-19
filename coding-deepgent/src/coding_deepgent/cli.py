from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import typer
from click.exceptions import ClickException
from typer.main import get_command

from coding_deepgent import cli_service
from coding_deepgent.frontend.bridge import run_stdio_bridge
from coding_deepgent.logging_config import configure_logging
from coding_deepgent.memory.backend import MemoryJobStatus, migrate_memory_schema
from coding_deepgent.memory.schemas import MemoryType
from coding_deepgent.renderers.text import (
    render_config_table,
    render_doctor_table,
    render_object_detail,
    render_plan_table,
    render_session_inspect_view,
    render_session_table,
    render_task_table,
)
from coding_deepgent.rendering import extract_text
from coding_deepgent.settings import build_openai_model
from coding_deepgent.sessions import ProjectionMode, build_session_inspect_view
from coding_deepgent.sessions.records import TranscriptProjection
from coding_deepgent.sessions.session_memory import write_session_memory_artifact

app = typer.Typer(
    add_completion=False,
    help="Run the coding-deepgent LangChain cc product agent.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Inspect resolved configuration.")
sessions_app = typer.Typer(help="Inspect or resume recorded sessions.")
tasks_app = typer.Typer(help="Inspect and control durable task records.")
plans_app = typer.Typer(help="Inspect and control durable plan artifacts.")
memory_app = typer.Typer(help="Manage durable long-term memory backend and jobs.")
app.add_typer(config_app, name="config")
app.add_typer(sessions_app, name="sessions")
app.add_typer(tasks_app, name="tasks")
app.add_typer(plans_app, name="plans")
app.add_typer(memory_app, name="memory")


def agent_loop(*args: Any, **kwargs: Any) -> str:
    from coding_deepgent.app import agent_loop

    return agent_loop(*args, **kwargs)


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


@tasks_app.command("list")
def tasks_list(
    include_terminal: bool = typer.Option(
        False,
        "--all",
        help="Include completed and cancelled tasks.",
    ),
) -> None:
    settings = build_cli_runtime().settings_loader()
    records = [
        record.model_dump()
        for record in cli_service.task_records(
            settings,
            include_terminal=include_terminal,
        )
    ]
    typer.echo(render_task_table(records))


@tasks_app.command("get")
def tasks_get(
    task_id: str = typer.Argument(..., help="Durable task identifier."),
) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        record = cli_service.task_record(settings, task_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Task", record.model_dump()))


@tasks_app.command("create")
def tasks_create(
    title: str = typer.Argument(..., help="Task title."),
    description: str = typer.Option("", "--description"),
    depends_on: list[str] | None = typer.Option(
        None,
        "--depends-on",
        help="Repeat to add dependency task ids.",
    ),
    owner: str | None = typer.Option(None, "--owner"),
    metadata: list[str] | None = typer.Option(
        None,
        "--metadata",
        help="Repeat as key=value.",
    ),
) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        record = cli_service.create_task_record(
            settings,
            title=title,
            description=description,
            depends_on=depends_on,
            owner=owner,
            metadata=_metadata_options(metadata),
        )
    except ValueError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Task", record.model_dump()))


@tasks_app.command("update")
def tasks_update(
    task_id: str = typer.Argument(..., help="Durable task identifier."),
    status: str | None = typer.Option(None, "--status"),
    depends_on: list[str] | None = typer.Option(
        None,
        "--depends-on",
        help="Repeat to replace dependencies.",
    ),
    owner: str | None = typer.Option(None, "--owner"),
    metadata: list[str] | None = typer.Option(
        None,
        "--metadata",
        help="Repeat as key=value.",
    ),
) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        record = cli_service.update_task_record(
            settings,
            task_id=task_id,
            status=status,
            depends_on=depends_on,
            owner=owner,
            metadata=_metadata_options(metadata) if metadata is not None else None,
        )
    except (KeyError, ValueError) as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Task", record.model_dump()))


@plans_app.command("list")
def plans_list() -> None:
    settings = build_cli_runtime().settings_loader()
    records = [record.model_dump() for record in cli_service.plan_records(settings)]
    typer.echo(render_plan_table(records))


@plans_app.command("get")
def plans_get(
    plan_id: str = typer.Argument(..., help="Durable plan identifier."),
) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        record = cli_service.plan_record(settings, plan_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Plan", record.model_dump()))


@plans_app.command("save")
def plans_save(
    title: str = typer.Argument(..., help="Plan title."),
    content: str = typer.Option(..., "--content", help="Plan content."),
    verification: str = typer.Option(
        ...,
        "--verification",
        help="Verification criteria.",
    ),
    task_ids: list[str] | None = typer.Option(
        None,
        "--task-id",
        help="Repeat to associate durable tasks.",
    ),
    metadata: list[str] | None = typer.Option(
        None,
        "--metadata",
        help="Repeat as key=value.",
    ),
) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        record = cli_service.create_plan_record(
            settings,
            title=title,
            content=content,
            verification=verification,
            task_ids=task_ids,
            metadata=_metadata_options(metadata),
        )
    except ValueError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Plan", record.model_dump()))


@sessions_app.command("inspect")
def sessions_inspect(
    session_id: str = typer.Argument(..., help="Session identifier to inspect."),
    projection_mode: str = typer.Option(
        "selected",
        "--projection",
        help="Projection to inspect: selected, raw, compact, or collapse.",
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        min=1,
        max=200,
        help="Maximum rows per inspect section.",
    ),
    no_recovery: bool = typer.Option(
        False,
        "--no-recovery",
        help="Hide the recovery brief section.",
    ),
    no_model: bool = typer.Option(
        False,
        "--no-model",
        help="Hide the model projection section.",
    ),
    no_raw: bool = typer.Option(
        False,
        "--no-raw",
        help="Hide the raw transcript visibility section.",
    ),
) -> None:
    runtime = build_cli_runtime()
    try:
        loaded = runtime.load_session(session_id)
        mode = _projection_mode(projection_mode)
        view = build_session_inspect_view(loaded, projection_mode=mode)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    except ValueError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(
        render_session_inspect_view(
            view,
            show_recovery=not no_recovery,
            show_model=not no_model,
            show_raw=not no_raw,
            limit=limit,
        )
    )


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


def _projection_mode(value: str) -> ProjectionMode:
    if value not in {"selected", "raw", "compact", "collapse"}:
        raise ValueError("projection must be one of: selected, raw, compact, collapse")
    return cast(ProjectionMode, value)


def _metadata_options(values: list[str] | None) -> dict[str, str]:
    if not values:
        return {}
    parsed: dict[str, str] = {}
    for item in values:
        key, separator, value = item.partition("=")
        key = key.strip()
        value = value.strip()
        if not separator or not key or not value:
            raise ValueError("metadata entries must use key=value with non-empty values")
        parsed[key] = value
    return parsed


@app.command("ui")
def ui(
    fake: bool = typer.Option(
        False,
        "--fake",
        help="Start the React/Ink CLI frontend with deterministic fake responses.",
    ),
) -> None:
    raise typer.Exit(_run_frontend_ui(fake=fake))


def _frontend_cli_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "frontend" / "cli"


def _run_frontend_ui(*, fake: bool = False) -> int:
    frontend_dir = _frontend_cli_dir()
    if not frontend_dir.exists():
        raise ClickException(f"Frontend CLI package not found: {frontend_dir}")
    if not (frontend_dir / "package.json").exists():
        raise ClickException(f"Frontend CLI package.json not found: {frontend_dir}")
    if not (frontend_dir / "node_modules").exists():
        raise ClickException(
            "Frontend CLI dependencies are not installed. "
            "Run `npm --prefix frontend/cli install` from `coding-deepgent/`."
        )
    script = "start:fake" if fake else "start"
    try:
        result = subprocess.run(["npm", "run", script], cwd=frontend_dir)
    except FileNotFoundError as exc:
        raise ClickException(
            "npm is required to start the React/Ink CLI frontend."
        ) from exc
    return int(result.returncode)


@app.command("ui-bridge")
def ui_bridge(
    fake: bool = typer.Option(
        False,
        "--fake",
        help="Run the frontend JSONL bridge with deterministic fake responses.",
    ),
) -> None:
    run_stdio_bridge(fake=fake)


def _load_ui_gateway_runtime():
    try:
        import uvicorn
        from coding_deepgent.frontend.gateway import create_app
    except ModuleNotFoundError as exc:
        raise ClickException(
            "ui-gateway requires optional web dependencies. Install with `pip install -e .[web]`."
        ) from exc
    return create_app, uvicorn.run


@app.command("ui-gateway")
def ui_gateway(
    fake: bool = typer.Option(
        False,
        "--fake",
        help="Start the frontend SSE gateway with deterministic fake responses.",
    ),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(2027, "--port", min=1, max=65535),
) -> None:
    create_app, uvicorn_run = _load_ui_gateway_runtime()
    uvicorn_run(create_app(fake=fake), host=host, port=port)


@memory_app.command("migrate")
def memory_migrate() -> None:
    from coding_deepgent.app import build_container

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
    from coding_deepgent.app import build_container

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
    from coding_deepgent.app import build_container

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
    from coding_deepgent.app import build_container

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
    from coding_deepgent.app import build_container

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


def ui_cli(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    return main(["ui", *args])


if __name__ == "__main__":  # pragma: no cover
    cli()
