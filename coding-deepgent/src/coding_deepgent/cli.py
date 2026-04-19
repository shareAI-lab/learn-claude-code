from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import typer
from click.exceptions import ClickException
from typer.main import get_command

from coding_deepgent import cli_service
from coding_deepgent.acceptance import circle1_acceptance_checks, circle2_acceptance_checks
from coding_deepgent.frontend.bridge import run_stdio_bridge
from coding_deepgent.logging_config import configure_logging
from coding_deepgent.memory.backend import MemoryJobStatus, migrate_memory_schema
from coding_deepgent.memory.schemas import MemoryType
from coding_deepgent.renderers.text import (
    render_acceptance_table,
    render_config_table,
    render_doctor_table,
    render_evidence_table,
    render_extension_table,
    render_object_detail,
    render_plan_table,
    render_session_history_table,
    render_session_inspect_view,
    render_session_projection_table,
    render_session_table,
    render_session_timeline_table,
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
skills_app = typer.Typer(help="Inspect and validate local skills.")
mcp_app = typer.Typer(help="Inspect and validate local MCP configuration.")
hooks_app = typer.Typer(help="Inspect supported local hook events.")
plugins_app = typer.Typer(help="Inspect and validate local plugin manifests.")
acceptance_app = typer.Typer(help="Run deterministic acceptance harnesses.")
events_app = typer.Typer(help="Inspect and control replayable local events.")
workers_app = typer.Typer(help="Inspect and control durable local workers.")
mailbox_app = typer.Typer(help="Send and acknowledge local mailbox messages.")
teams_app = typer.Typer(help="Inspect and control local team runs.")
remote_app = typer.Typer(help="Record local remote-control sessions and replay events.")
lifecycle_app = typer.Typer(help="Manage local extension lifecycle state.")
continuity_app = typer.Typer(help="Manage cross-day continuity artifacts.")
memory_app = typer.Typer(help="Manage durable long-term memory backend and jobs.")
app.add_typer(config_app, name="config")
app.add_typer(sessions_app, name="sessions")
app.add_typer(tasks_app, name="tasks")
app.add_typer(plans_app, name="plans")
app.add_typer(skills_app, name="skills")
app.add_typer(mcp_app, name="mcp")
app.add_typer(hooks_app, name="hooks")
app.add_typer(plugins_app, name="plugins")
app.add_typer(acceptance_app, name="acceptance")
app.add_typer(events_app, name="events")
app.add_typer(workers_app, name="workers")
app.add_typer(mailbox_app, name="mailbox")
app.add_typer(teams_app, name="teams")
app.add_typer(remote_app, name="remote")
app.add_typer(lifecycle_app, name="extension-lifecycle")
app.add_typer(continuity_app, name="continuity")
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


@skills_app.command("list")
def skills_list() -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_extension_table("Skills", cli_service.skill_rows(settings)))


@skills_app.command("inspect")
def skills_inspect(name: str = typer.Argument(..., help="Skill name.")) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        detail = cli_service.skill_detail(settings, name)
    except (KeyError, ValueError) as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Skill", detail))


@skills_app.command("validate")
def skills_validate() -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        rows = cli_service.skill_rows(settings)
    except (OSError, ValueError) as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_extension_table("Skills", rows))


@skills_app.command("debug")
def skills_debug(name: str = typer.Argument(..., help="Skill name.")) -> None:
    skills_inspect(name)


@mcp_app.command("list")
def mcp_list() -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_extension_table("MCP Servers", cli_service.mcp_rows(settings)))


@mcp_app.command("inspect")
def mcp_inspect(name: str = typer.Argument(..., help="MCP server name.")) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        detail = cli_service.mcp_detail(settings, name)
    except (KeyError, ValueError) as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("MCP Server", detail))


@mcp_app.command("validate")
def mcp_validate() -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        rows = cli_service.mcp_rows(settings)
    except (OSError, ValueError) as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_extension_table("MCP Servers", rows))


@mcp_app.command("debug")
def mcp_debug(name: str = typer.Argument(..., help="MCP server name.")) -> None:
    mcp_inspect(name)


@hooks_app.command("list")
def hooks_list() -> None:
    typer.echo(render_extension_table("Hooks", cli_service.hook_rows()))


@hooks_app.command("inspect")
def hooks_inspect(name: str = typer.Argument(..., help="Hook event name.")) -> None:
    try:
        detail = cli_service.hook_detail(name)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Hook", detail))


@hooks_app.command("validate")
def hooks_validate() -> None:
    typer.echo(render_extension_table("Hooks", cli_service.hook_rows()))


@hooks_app.command("debug")
def hooks_debug(name: str = typer.Argument(..., help="Hook event name.")) -> None:
    hooks_inspect(name)


@plugins_app.command("list")
def plugins_list() -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_extension_table("Plugins", cli_service.plugin_rows(settings)))


@plugins_app.command("inspect")
def plugins_inspect(name: str = typer.Argument(..., help="Plugin name.")) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        detail = cli_service.plugin_detail(settings, name)
    except (KeyError, ValueError) as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Plugin", detail))


@plugins_app.command("validate")
def plugins_validate() -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        rows = cli_service.validate_plugins(settings)
    except (OSError, ValueError) as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_extension_table("Plugins", rows))


@plugins_app.command("debug")
def plugins_debug(name: str = typer.Argument(..., help="Plugin name.")) -> None:
    plugins_inspect(name)


@acceptance_app.command("circle1")
def acceptance_circle1() -> None:
    settings = build_cli_runtime().settings_loader()
    rows = [
        {
            "name": check.name,
            "status": check.status,
            "detail": check.detail,
        }
        for check in circle1_acceptance_checks(settings)
    ]
    typer.echo(render_acceptance_table(rows, title="Circle 1 Acceptance"))


@acceptance_app.command("circle2")
def acceptance_circle2() -> None:
    settings = build_cli_runtime().settings_loader()
    rows = [
        {
            "name": check.name,
            "status": check.status,
            "detail": check.detail,
        }
        for check in circle2_acceptance_checks(settings)
    ]
    typer.echo(render_acceptance_table(rows, title="Circle 2 Acceptance"))


@events_app.command("list")
def events_list(
    stream_id: str = typer.Argument(..., help="Event stream identifier."),
    include_internal: bool = typer.Option(False, "--internal"),
) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(
        render_extension_table(
            "Events",
            cli_service.event_rows(
                settings,
                stream_id=stream_id,
                include_internal=include_internal,
            ),
        )
    )


@events_app.command("append")
def events_append(
    stream_id: str = typer.Argument(...),
    kind: str = typer.Argument(...),
) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_object_detail("Event", cli_service.append_event_row(settings, stream_id=stream_id, kind=kind)))


@events_app.command("ack")
def events_ack(stream_id: str = typer.Argument(...), event_id: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.ack_event_row(settings, stream_id=stream_id, event_id=event_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Event", payload))


@workers_app.command("list")
def workers_list(include_terminal: bool = typer.Option(False, "--all")) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(
        render_extension_table(
            "Workers",
            cli_service.worker_rows(settings, include_terminal=include_terminal),
        )
    )


@workers_app.command("create")
def workers_create(
    kind: str = typer.Argument("local"),
    session_id: str = typer.Option("default", "--session-id"),
) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_object_detail("Worker", cli_service.create_worker_row(settings, kind=kind, session_id=session_id)))


@workers_app.command("heartbeat")
def workers_heartbeat(worker_id: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.heartbeat_worker_row(settings, worker_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Worker", payload))


@workers_app.command("stop")
def workers_stop(worker_id: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.stop_worker_row(settings, worker_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Worker", payload))


@workers_app.command("complete")
def workers_complete(
    worker_id: str = typer.Argument(...),
    status: str = typer.Option("completed", "--status"),
    summary: str | None = typer.Option(None, "--summary"),
) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.complete_worker_row(
            settings,
            worker_id,
            status=status,
            summary=summary,
        )
    except (KeyError, ValueError) as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Worker", payload))


@mailbox_app.command("list")
def mailbox_list(recipient: str | None = typer.Option(None, "--recipient")) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_extension_table("Mailbox", cli_service.mailbox_rows(settings, recipient=recipient)))


@mailbox_app.command("send")
def mailbox_send(
    recipient: str = typer.Argument(...),
    subject: str = typer.Argument(...),
    body: str = typer.Argument(...),
    sender: str = typer.Option("user", "--sender"),
    delivery_key: str | None = typer.Option(None, "--delivery-key"),
) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(
        render_object_detail(
            "Mailbox Message",
            cli_service.send_mailbox_row(
                settings,
                sender=sender,
                recipient=recipient,
                subject=subject,
                body=body,
                delivery_key=delivery_key,
            ),
        )
    )


@mailbox_app.command("ack")
def mailbox_ack(message_id: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.ack_mailbox_row(settings, message_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Mailbox Message", payload))


@teams_app.command("list")
def teams_list() -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_extension_table("Teams", cli_service.team_rows(settings)))


@teams_app.command("create")
def teams_create(title: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_object_detail("Team", cli_service.create_team_row(settings, title=title)))


@teams_app.command("assign")
def teams_assign(team_id: str = typer.Argument(...), worker_id: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.assign_team_worker_row(settings, team_id=team_id, worker_id=worker_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Team", payload))


@teams_app.command("progress")
def teams_progress(team_id: str = typer.Argument(...), message: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.progress_team_row(settings, team_id=team_id, message=message)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Team", payload))


@teams_app.command("complete")
def teams_complete(team_id: str = typer.Argument(...), summary: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.complete_team_row(settings, team_id=team_id, summary=summary)
    except (KeyError, ValueError) as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Team", payload))


@remote_app.command("list")
def remote_list() -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_extension_table("Remote Sessions", cli_service.remote_rows(settings)))


@remote_app.command("register")
def remote_register(
    session_id: str = typer.Argument(...),
    client_name: str = typer.Argument(...),
) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_object_detail("Remote Session", cli_service.register_remote_row(settings, session_id=session_id, client_name=client_name)))


@remote_app.command("control")
def remote_control(remote_id: str = typer.Argument(...), command: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.remote_control_row(settings, remote_id=remote_id, command=command)
    except (KeyError, ValueError) as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Remote Event", payload))


@remote_app.command("replay")
def remote_replay(remote_id: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        rows = cli_service.remote_replay_rows(settings, remote_id=remote_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_extension_table("Remote Events", rows))


@remote_app.command("close")
def remote_close(remote_id: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.close_remote_row(settings, remote_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Remote Session", payload))


@lifecycle_app.command("list")
def lifecycle_list() -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_extension_table("Extension Lifecycle", cli_service.lifecycle_rows(settings)))


@lifecycle_app.command("register")
def lifecycle_register(
    name: str = typer.Argument(...),
    kind: str = typer.Argument(...),
    source: str = typer.Argument(...),
) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.register_lifecycle_row(settings, name=name, kind=kind, source=source)
    except ValueError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Extension", payload))


@lifecycle_app.command("enable")
def lifecycle_enable(extension_id: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_object_detail("Extension", cli_service.set_lifecycle_enabled(settings, extension_id, enabled=True)))


@lifecycle_app.command("disable")
def lifecycle_disable(extension_id: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_object_detail("Extension", cli_service.set_lifecycle_enabled(settings, extension_id, enabled=False)))


@lifecycle_app.command("update")
def lifecycle_update(extension_id: str = typer.Argument(...), version: str | None = typer.Option(None, "--version")) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_object_detail("Extension", cli_service.update_lifecycle_row(settings, extension_id, version=version)))


@lifecycle_app.command("rollback")
def lifecycle_rollback(extension_id: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_object_detail("Extension", cli_service.rollback_lifecycle_row(settings, extension_id)))


@continuity_app.command("list")
def continuity_list(include_stale: bool = typer.Option(False, "--all")) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_extension_table("Continuity", cli_service.continuity_rows(settings, include_stale=include_stale)))


@continuity_app.command("save")
def continuity_save(
    title: str = typer.Argument(...),
    content: str = typer.Argument(...),
    session_id: str | None = typer.Option(None, "--session-id"),
) -> None:
    settings = build_cli_runtime().settings_loader()
    typer.echo(render_object_detail("Continuity", cli_service.save_continuity_row(settings, title=title, content=content, session_id=session_id)))


@continuity_app.command("show")
def continuity_show(artifact_id: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.continuity_detail(settings, artifact_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Continuity", payload))


@continuity_app.command("stale")
def continuity_stale(artifact_id: str = typer.Argument(...)) -> None:
    settings = build_cli_runtime().settings_loader()
    try:
        payload = cli_service.stale_continuity_row(settings, artifact_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    typer.echo(render_object_detail("Continuity", payload))


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


@sessions_app.command("history")
def sessions_history(
    session_id: str = typer.Argument(..., help="Session identifier to inspect."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
) -> None:
    runtime = build_cli_runtime()
    try:
        loaded = runtime.load_session(session_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    view = build_session_inspect_view(loaded, projection_mode="raw")
    typer.echo(render_session_history_table(view, limit=limit))


@sessions_app.command("projection")
def sessions_projection(
    session_id: str = typer.Argument(..., help="Session identifier to inspect."),
    projection_mode: str = typer.Option(
        "selected",
        "--projection",
        help="Projection to inspect: selected, raw, compact, or collapse.",
    ),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
) -> None:
    runtime = build_cli_runtime()
    try:
        loaded = runtime.load_session(session_id)
        mode = _projection_mode(projection_mode)
    except (KeyError, ValueError) as exc:
        raise ClickException(str(exc)) from exc
    view = build_session_inspect_view(loaded, projection_mode=mode)
    typer.echo(render_session_projection_table(view, limit=limit))


@sessions_app.command("timeline")
def sessions_timeline(
    session_id: str = typer.Argument(..., help="Session identifier to inspect."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
) -> None:
    runtime = build_cli_runtime()
    try:
        loaded = runtime.load_session(session_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    view = build_session_inspect_view(loaded)
    typer.echo(render_session_timeline_table(view, limit=limit))


@sessions_app.command("evidence")
def sessions_evidence(
    session_id: str = typer.Argument(..., help="Session identifier to inspect."),
    kind: str | None = typer.Option(None, "--kind", help="Optional evidence kind."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
) -> None:
    runtime = build_cli_runtime()
    try:
        loaded = runtime.load_session(session_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    rows = cli_service.session_evidence_rows(loaded, kind=kind)
    typer.echo(render_evidence_table("Session Evidence", rows, limit=limit))


@sessions_app.command("events")
def sessions_events(
    session_id: str = typer.Argument(..., help="Session identifier to inspect."),
    event_kind: str | None = typer.Option(
        None,
        "--event-kind",
        help="Optional runtime event kind metadata filter.",
    ),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
) -> None:
    runtime = build_cli_runtime()
    try:
        loaded = runtime.load_session(session_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    rows = cli_service.session_evidence_rows(
        loaded,
        kind="runtime_event",
        event_kind=event_kind,
    )
    typer.echo(render_evidence_table("Runtime Events", rows, limit=limit))


@sessions_app.command("permissions")
def sessions_permissions(
    session_id: str = typer.Argument(..., help="Session identifier to inspect."),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
) -> None:
    runtime = build_cli_runtime()
    try:
        loaded = runtime.load_session(session_id)
    except KeyError as exc:
        raise ClickException(str(exc)) from exc
    rows = cli_service.permission_evidence_rows(loaded)
    typer.echo(render_evidence_table("Permission And Hook Events", rows, limit=limit))


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
