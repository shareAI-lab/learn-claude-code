from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence, cast

from langchain.agents import create_agent

from coding_deepgent import bootstrap
from coding_deepgent.compact import (
    compact_metadata,
    compact_messages_with_summary,
    generate_compact_summary,
)
from coding_deepgent.continuity import (
    get_artifact,
    list_artifacts,
    mark_stale,
    save_artifact,
)
from coding_deepgent.event_stream import (
    ack_event,
    append_event,
    list_events,
)
from coding_deepgent.extension_lifecycle import (
    disable_extension,
    enable_extension,
    list_extensions,
    register_extension,
    rollback_extension,
    update_extension,
)
from coding_deepgent.extension_lifecycle.store import ExtensionKind
from coding_deepgent.logging_config import safe_environment_snapshot
from coding_deepgent.mailbox import (
    ack_message,
    list_messages,
    send_message,
)
from coding_deepgent.mcp import langchain_mcp_adapters_available, load_local_mcp_config
from coding_deepgent.plugins import PluginRegistry, discover_local_plugins
from coding_deepgent.remote import (
    close_remote_session,
    list_remote_sessions,
    register_remote_session,
    replay_remote_events,
    send_remote_control,
)
from coding_deepgent.settings import Settings, load_settings
from coding_deepgent.settings import build_openai_model as build_model
from coding_deepgent.skills import discover_local_skills
from coding_deepgent.hooks import HookEventName
from coding_deepgent.teams import (
    assign_worker,
    complete_team,
    create_team,
    list_teams,
    update_progress,
)
from coding_deepgent.tasks import (
    PlanArtifact,
    TaskStatus,
    TaskRecord,
    create_plan,
    create_task,
    get_plan,
    get_task,
    list_plans,
    list_tasks,
    update_task,
)
from coding_deepgent.tasks.store import TaskStore
from coding_deepgent.worker_runtime import (
    complete_worker,
    create_worker,
    heartbeat_worker,
    list_workers,
    request_worker_stop,
)
from coding_deepgent.worker_runtime.store import WorkerStatus
from coding_deepgent.sessions import (
    LoadedSession,
    SessionLoadError,
    SessionMessage,
    SessionEvidence,
    TranscriptProjection,
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
        [
            str,
            list[dict[str, Any]] | None,
            dict[str, Any] | None,
            str | None,
            TranscriptProjection | None,
        ],
        str,
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
        DoctorCheck("store_backend", "resolved", settings.store_backend),
        DoctorCheck("store_path", "ready", str(settings.store_path)),
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


def session_evidence_rows(
    loaded: LoadedSession,
    *,
    kind: str | None = None,
    event_kind: str | None = None,
) -> list[dict[str, Any]]:
    rows = [_evidence_row(item) for item in loaded.evidence]
    if kind is not None:
        rows = [row for row in rows if row["kind"] == kind]
    if event_kind is not None:
        rows = [
            row
            for row in rows
            if isinstance(row.get("metadata"), dict)
            and row["metadata"].get("event_kind") == event_kind
        ]
    return rows


def permission_evidence_rows(loaded: LoadedSession) -> list[dict[str, Any]]:
    rows = session_evidence_rows(loaded, kind="runtime_event")
    return [
        row
        for row in rows
        if isinstance(row.get("metadata"), dict)
        and row["metadata"].get("event_kind") in {"permission_denied", "hook_blocked"}
    ]


def _evidence_row(item: SessionEvidence) -> dict[str, Any]:
    return {
        "kind": item.kind,
        "summary": item.summary,
        "status": item.status,
        "created_at": item.created_at,
        "subject": item.subject,
        "metadata": item.metadata or {},
    }


def skill_rows(settings: Settings) -> list[dict[str, Any]]:
    return [
        {
            "name": skill.metadata.name,
            "status": "valid",
            "description": skill.metadata.description,
            "path": str(skill.path),
        }
        for skill in discover_local_skills(
            workdir=settings.workdir,
            skill_dir=settings.skill_dir,
        )
    ]


def skill_detail(settings: Settings, name: str) -> dict[str, Any]:
    for row in skill_rows(settings):
        if row["name"] == name:
            return row
    raise KeyError(f"Unknown skill: {name}")


def mcp_rows(settings: Settings) -> list[dict[str, Any]]:
    loaded = load_local_mcp_config(workdir=settings.workdir)
    if loaded is None:
        return []
    return [
        {
            "name": name,
            "status": "configured",
            "description": f"{server.transport}",
            "path": str(loaded.path),
        }
        for name, server in loaded.config.mcpServers.items()
    ]


def mcp_detail(settings: Settings, name: str) -> dict[str, Any]:
    loaded = load_local_mcp_config(workdir=settings.workdir)
    if loaded is None:
        raise KeyError(f"Unknown MCP server: {name}")
    server = loaded.config.mcpServers.get(name)
    if server is None:
        raise KeyError(f"Unknown MCP server: {name}")
    return {
        "name": name,
        "status": "configured",
        "transport": server.transport,
        "command": server.command,
        "args": list(server.args),
        "url": server.url,
        "path": str(loaded.path),
        "adapter_available": langchain_mcp_adapters_available(),
    }


def hook_rows() -> list[dict[str, Any]]:
    events: tuple[HookEventName, ...] = (
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "PermissionDenied",
        "PreCompact",
        "PostCompact",
    )
    return [
        {
            "name": event,
            "status": "supported",
            "description": "local sync hook event",
            "path": "runtime LocalHookRegistry",
        }
        for event in events
    ]


def hook_detail(name: str) -> dict[str, Any]:
    for row in hook_rows():
        if row["name"] == name:
            return row
    raise KeyError(f"Unknown hook event: {name}")


def plugin_rows(settings: Settings) -> list[dict[str, Any]]:
    return [
        {
            "name": plugin.manifest.name,
            "status": "valid",
            "description": plugin.manifest.description,
            "path": str(plugin.path),
        }
        for plugin in discover_local_plugins(
            workdir=settings.workdir,
            plugin_dir=settings.plugin_dir,
        )
    ]


def plugin_detail(settings: Settings, name: str) -> dict[str, Any]:
    for plugin in discover_local_plugins(
        workdir=settings.workdir,
        plugin_dir=settings.plugin_dir,
    ):
        if plugin.manifest.name == name:
            return {
                "name": plugin.manifest.name,
                "description": plugin.manifest.description,
                "version": plugin.manifest.version,
                "skills": list(plugin.manifest.skills),
                "tools": list(plugin.manifest.tools),
                "resources": list(plugin.manifest.resources),
                "agents": list(plugin.manifest.agents),
                "path": str(plugin.path),
            }
    raise KeyError(f"Unknown plugin: {name}")


def validate_plugins(settings: Settings) -> list[dict[str, Any]]:
    plugins = discover_local_plugins(
        workdir=settings.workdir,
        plugin_dir=settings.plugin_dir,
    )
    registry = PluginRegistry(plugins)
    container = _build_container_for_settings(settings)
    known_tools = set(container.capability_registry().names())
    known_skills = {
        row["name"]
        for row in skill_rows(settings)
        if isinstance(row.get("name"), str)
    }
    registry.validate(known_tools=known_tools, known_skills=known_skills)
    return [
        {
            "name": item.plugin_name,
            "status": "valid",
            "description": f"tools={len(item.tools)} skills={len(item.skills)} resources={len(item.resources)} agents={len(item.agents)}",
            "path": "",
        }
        for item in registry.declarations()
    ]


def event_rows(
    settings: Settings,
    *,
    stream_id: str,
    include_internal: bool = False,
) -> list[dict[str, Any]]:
    return [
        {
            "name": event.event_id,
            "status": event.kind,
            "description": f"seq={event.sequence} acked={event.acked}",
            "path": event.stream_id,
        }
        for event in list_events(
            cast(Any, _runtime_store(settings)),
            stream_id=stream_id,
            include_internal=include_internal,
        )
    ]


def append_event_row(settings: Settings, *, stream_id: str, kind: str) -> dict[str, Any]:
    event = append_event(
        cast(Any, _runtime_store(settings)),
        stream_id=stream_id,
        kind=kind,
    )
    return {
        "event_id": event.event_id,
        "stream_id": event.stream_id,
        "sequence": event.sequence,
        "kind": event.kind,
    }


def ack_event_row(settings: Settings, *, stream_id: str, event_id: str) -> dict[str, Any]:
    event = ack_event(
        cast(Any, _runtime_store(settings)),
        stream_id=stream_id,
        event_id=event_id,
    )
    return event.model_dump()


def worker_rows(settings: Settings, *, include_terminal: bool = False) -> list[dict[str, Any]]:
    return [
        {
            "name": worker.worker_id,
            "status": worker.status,
            "description": f"{worker.kind} session={worker.session_id} stop={worker.stop_requested}",
            "path": worker.owner or "-",
        }
        for worker in list_workers(
            cast(Any, _runtime_store(settings)),
            include_terminal=include_terminal,
        )
    ]


def create_worker_row(settings: Settings, *, kind: str, session_id: str = "default") -> dict[str, Any]:
    return create_worker(
        cast(Any, _runtime_store(settings)),
        kind=kind,
        session_id=session_id,
    ).model_dump()


def heartbeat_worker_row(settings: Settings, worker_id: str) -> dict[str, Any]:
    return heartbeat_worker(cast(Any, _runtime_store(settings)), worker_id).model_dump()


def stop_worker_row(settings: Settings, worker_id: str) -> dict[str, Any]:
    return request_worker_stop(cast(Any, _runtime_store(settings)), worker_id).model_dump()


def complete_worker_row(
    settings: Settings,
    worker_id: str,
    *,
    status: str,
    summary: str | None = None,
) -> dict[str, Any]:
    return complete_worker(
        cast(Any, _runtime_store(settings)),
        worker_id,
        status=cast(WorkerStatus, status),
        result_summary=summary,
    ).model_dump()


def mailbox_rows(settings: Settings, *, recipient: str | None = None) -> list[dict[str, Any]]:
    return [
        {
            "name": message.message_id,
            "status": message.status,
            "description": f"{message.sender} -> {message.recipient}: {message.subject}",
            "path": message.delivery_key or "-",
        }
        for message in list_messages(cast(Any, _runtime_store(settings)), recipient=recipient)
    ]


def send_mailbox_row(
    settings: Settings,
    *,
    sender: str,
    recipient: str,
    subject: str,
    body: str,
    delivery_key: str | None = None,
) -> dict[str, Any]:
    return send_message(
        cast(Any, _runtime_store(settings)),
        sender=sender,
        recipient=recipient,
        subject=subject,
        body=body,
        delivery_key=delivery_key,
    ).model_dump()


def ack_mailbox_row(settings: Settings, message_id: str) -> dict[str, Any]:
    return ack_message(cast(Any, _runtime_store(settings)), message_id).model_dump()


def team_rows(settings: Settings) -> list[dict[str, Any]]:
    return [
        {
            "name": team.team_id,
            "status": team.status,
            "description": f"{team.title} workers={len(team.worker_ids)}",
            "path": team.coordinator,
        }
        for team in list_teams(cast(Any, _runtime_store(settings)))
    ]


def create_team_row(settings: Settings, *, title: str) -> dict[str, Any]:
    return create_team(cast(Any, _runtime_store(settings)), title=title).model_dump()


def assign_team_worker_row(settings: Settings, *, team_id: str, worker_id: str) -> dict[str, Any]:
    return assign_worker(
        cast(Any, _runtime_store(settings)),
        team_id=team_id,
        worker_id=worker_id,
    ).model_dump()


def progress_team_row(settings: Settings, *, team_id: str, message: str) -> dict[str, Any]:
    return update_progress(
        cast(Any, _runtime_store(settings)),
        team_id=team_id,
        message=message,
    ).model_dump()


def complete_team_row(settings: Settings, *, team_id: str, summary: str) -> dict[str, Any]:
    return complete_team(
        cast(Any, _runtime_store(settings)),
        team_id=team_id,
        summary=summary,
    ).model_dump()


def remote_rows(settings: Settings) -> list[dict[str, Any]]:
    return [
        {
            "name": remote.remote_id,
            "status": remote.status,
            "description": f"session={remote.session_id} client={remote.client_name}",
            "path": f"last_seq={remote.last_sequence_sent}",
        }
        for remote in list_remote_sessions(cast(Any, _runtime_store(settings)))
    ]


def register_remote_row(settings: Settings, *, session_id: str, client_name: str) -> dict[str, Any]:
    return register_remote_session(
        cast(Any, _runtime_store(settings)),
        session_id=session_id,
        client_name=client_name,
    ).model_dump()


def remote_control_row(settings: Settings, *, remote_id: str, command: str) -> dict[str, Any]:
    return send_remote_control(
        cast(Any, _runtime_store(settings)),
        remote_id=remote_id,
        command=command,
    ).model_dump()


def remote_replay_rows(settings: Settings, *, remote_id: str) -> list[dict[str, Any]]:
    return [
        {
            "name": event.event_id,
            "status": event.kind,
            "description": f"seq={event.sequence}",
            "path": event.stream_id,
        }
        for event in replay_remote_events(cast(Any, _runtime_store(settings)), remote_id=remote_id)
    ]


def close_remote_row(settings: Settings, remote_id: str) -> dict[str, Any]:
    return close_remote_session(cast(Any, _runtime_store(settings)), remote_id).model_dump()


def lifecycle_rows(settings: Settings) -> list[dict[str, Any]]:
    return [
        {
            "name": item.extension_id,
            "status": item.status,
            "description": f"{item.kind}:{item.name}",
            "path": item.source,
        }
        for item in list_extensions(cast(Any, _runtime_store(settings)))
    ]


def register_lifecycle_row(
    settings: Settings,
    *,
    name: str,
    kind: str,
    source: str,
) -> dict[str, Any]:
    return register_extension(
        cast(Any, _runtime_store(settings)),
        name=name,
        kind=cast(ExtensionKind, kind),
        source=source,
    ).model_dump()


def set_lifecycle_enabled(settings: Settings, extension_id: str, *, enabled: bool) -> dict[str, Any]:
    store = cast(Any, _runtime_store(settings))
    return (
        enable_extension(store, extension_id)
        if enabled
        else disable_extension(store, extension_id)
    ).model_dump()


def update_lifecycle_row(settings: Settings, extension_id: str, *, version: str | None) -> dict[str, Any]:
    return update_extension(
        cast(Any, _runtime_store(settings)),
        extension_id,
        version=version,
    ).model_dump()


def rollback_lifecycle_row(settings: Settings, extension_id: str) -> dict[str, Any]:
    return rollback_extension(cast(Any, _runtime_store(settings)), extension_id).model_dump()


def continuity_rows(settings: Settings, *, include_stale: bool = False) -> list[dict[str, Any]]:
    return [
        {
            "name": item.artifact_id,
            "status": item.status,
            "description": item.title,
            "path": item.session_id or "-",
        }
        for item in list_artifacts(cast(Any, _runtime_store(settings)), include_stale=include_stale)
    ]


def save_continuity_row(
    settings: Settings,
    *,
    title: str,
    content: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    return save_artifact(
        cast(Any, _runtime_store(settings)),
        title=title,
        content=content,
        session_id=session_id,
    ).model_dump()


def continuity_detail(settings: Settings, artifact_id: str) -> dict[str, Any]:
    return get_artifact(cast(Any, _runtime_store(settings)), artifact_id).model_dump()


def stale_continuity_row(settings: Settings, artifact_id: str) -> dict[str, Any]:
    return mark_stale(cast(Any, _runtime_store(settings)), artifact_id).model_dump()


def task_records(
    settings: Settings,
    *,
    include_terminal: bool = False,
) -> list[TaskRecord]:
    return list_tasks(
        cast(TaskStore, _runtime_store(settings)),
        include_terminal=include_terminal,
    )


def task_record(settings: Settings, task_id: str) -> TaskRecord:
    return get_task(cast(TaskStore, _runtime_store(settings)), task_id)


def create_task_record(
    settings: Settings,
    *,
    title: str,
    description: str = "",
    depends_on: list[str] | None = None,
    owner: str | None = None,
    metadata: dict[str, str] | None = None,
) -> TaskRecord:
    return create_task(
        cast(TaskStore, _runtime_store(settings)),
        title=title,
        description=description,
        depends_on=depends_on,
        owner=owner,
        metadata=metadata,
    )


def update_task_record(
    settings: Settings,
    *,
    task_id: str,
    status: str | None = None,
    depends_on: list[str] | None = None,
    owner: str | None = None,
    metadata: dict[str, str] | None = None,
) -> TaskRecord:
    return update_task(
        cast(TaskStore, _runtime_store(settings)),
        task_id=task_id,
        status=cast(TaskStatus | None, status),
        depends_on=depends_on,
        owner=owner,
        metadata=metadata,
    )


def plan_records(settings: Settings) -> list[PlanArtifact]:
    return list_plans(cast(TaskStore, _runtime_store(settings)))


def plan_record(settings: Settings, plan_id: str) -> PlanArtifact:
    return get_plan(cast(TaskStore, _runtime_store(settings)), plan_id)


def create_plan_record(
    settings: Settings,
    *,
    title: str,
    content: str,
    verification: str,
    task_ids: list[str] | None = None,
    metadata: dict[str, str] | None = None,
) -> PlanArtifact:
    return create_plan(
        cast(TaskStore, _runtime_store(settings)),
        title=title,
        content=content,
        verification=verification,
        task_ids=task_ids,
        metadata=metadata,
    )


def run_once(
    *,
    settings: Settings,
    prompt: str,
    run_agent: Callable[..., str],
    history: list[dict[str, Any]] | None = None,
    session_state: dict[str, Any] | None = None,
    session_id: str | None = None,
    transcript_projection: TranscriptProjection | None = None,
) -> str:
    return run_prompt_with_recording(
        settings=settings,
        prompt=prompt,
        run_agent=run_agent,
        history=history,
        session_state=session_state,
        session_id=session_id,
        transcript_projection=transcript_projection,
    )


def recovery_brief_text(loaded: LoadedSession) -> str:
    return render_recovery_brief(build_recovery_brief(loaded))


def _conversation_messages(messages: Sequence[SessionMessage]) -> list[dict[str, Any]]:
    return [message.as_conversation_dict() for message in messages]


def _project_transcript_projection(
    messages: list[dict[str, Any]],
    entry_ids: list[tuple[str, ...]],
) -> TranscriptProjection:
    projected_messages: list[dict[str, Any]] = []
    projected_ids: list[tuple[str, ...]] = []
    for message, ids in zip(messages, entry_ids, strict=True):
        normalized = {"role": message.get("role", "user"), "content": message.get("content", "")}
        if "metadata" in message:
            normalized["metadata"] = message["metadata"]
        if projected_messages and projected_messages[-1].get("role") == normalized.get("role") and isinstance(projected_messages[-1].get("content"), str) and isinstance(normalized.get("content"), str) and set(projected_messages[-1].keys()) == {"role", "content"} and set(normalized.keys()) == {"role", "content"}:
            projected_messages[-1]["content"] = (
                f"{projected_messages[-1]['content']}\n\n{normalized['content']}"
            )
            projected_ids[-1] = (*projected_ids[-1], *ids)
            continue
        projected_messages.append(normalized)
        projected_ids.append(ids)
    return TranscriptProjection(entries=tuple(projected_ids))


def continuation_projection(loaded: LoadedSession) -> TranscriptProjection:
    messages = continuation_history(loaded)
    return _project_transcript_projection(
        messages,
        [()] + [(message.message_id,) for message in loaded.history],
    )


def selected_continuation_projection(loaded: LoadedSession) -> TranscriptProjection:
    if loaded.collapsed_history_source.mode == "collapse":
        return _collapsed_projection(loaded, selected_continuation_history(loaded))
    if loaded.compacted_history_source.mode != "compact":
        return continuation_projection(loaded)
    compact = loaded.compacts[loaded.compacted_history_source.compact_index or 0]
    return _compacted_projection_from_end_message_id(
        loaded,
        end_message_id=compact.end_message_id,
        messages=selected_continuation_history(loaded),
    )


def compacted_history_projection(
    loaded: LoadedSession,
    history: list[dict[str, Any]],
) -> TranscriptProjection:
    if len(history) < 3:
        return continuation_projection(loaded)
    boundary = compact_metadata(history[1])
    if boundary is None:
        return continuation_projection(loaded)
    end_message_id = boundary.get("end_message_id")
    if not isinstance(end_message_id, str) or not end_message_id.strip():
        return continuation_projection(loaded)
    return _compacted_projection_from_end_message_id(
        loaded,
        end_message_id=end_message_id.strip(),
        messages=history,
    )


def _compacted_projection_from_end_message_id(
    loaded: LoadedSession,
    *,
    end_message_id: str,
    messages: list[dict[str, Any]],
) -> TranscriptProjection:
    message_index_by_id = {
        message.message_id: index for index, message in enumerate(loaded.history)
    }
    end_index = message_index_by_id.get(end_message_id, -1)
    tail_entries = [
        (message.message_id,) for message in loaded.history[end_index + 1 :]
    ]
    return _project_transcript_projection(
        messages,
        [(), (), *([()] if len(messages) > 2 else []), *tail_entries],
    )


def continuation_history(loaded: LoadedSession) -> list[dict[str, Any]]:
    return [
        build_resume_context_message(loaded),
        *_conversation_messages(loaded.history),
    ]


def selected_continuation_history(loaded: LoadedSession) -> list[dict[str, Any]]:
    if loaded.collapsed_history_source.mode == "collapse":
        return [
            build_resume_context_message(loaded),
            *[dict(message) for message in loaded.collapsed_history],
        ]
    return [
        build_resume_context_message(loaded),
        *[dict(message) for message in loaded.compacted_history],
    ]


def _collapsed_projection(
    loaded: LoadedSession,
    messages: list[dict[str, Any]],
) -> TranscriptProjection:
    selected = _selected_collapse_spans(loaded)
    if not selected:
        return continuation_projection(loaded)
    entries: list[tuple[str, ...]] = []
    cursor = 0
    for start_index, end_index, _collapse_index in selected:
        entries.extend(
            (message.message_id,) for message in loaded.history[cursor:start_index]
        )
        entries.extend(((), ()))
        cursor = end_index + 1
    entries.extend((message.message_id,) for message in loaded.history[cursor:])
    return _project_transcript_projection(messages, [(), *entries])


def _selected_collapse_spans(
    loaded: LoadedSession,
) -> list[tuple[int, int, int]]:
    id_to_index = {
        message.message_id: index for index, message in enumerate(loaded.history)
    }
    selected: list[tuple[int, int, int]] = []
    covered_indexes: set[int] = set()
    for collapse_index in range(len(loaded.collapses) - 1, -1, -1):
        collapse = loaded.collapses[collapse_index]
        start_index = id_to_index.get(collapse.start_message_id)
        end_index = id_to_index.get(collapse.end_message_id)
        if start_index is None or end_index is None or end_index < start_index:
            continue
        covered_slice = tuple(
            message.message_id
            for message in loaded.history[start_index : end_index + 1]
        )
        if (
            collapse.covered_message_ids is not None
            and collapse.covered_message_ids != covered_slice
        ):
            continue
        span_indexes = set(range(start_index, end_index + 1))
        if covered_indexes & span_indexes:
            continue
        covered_indexes.update(span_indexes)
        selected.append((start_index, end_index, collapse_index))
    return sorted(selected, key=lambda item: item[0])


def compacted_continuation_history(
    loaded: LoadedSession,
    *,
    summary: str,
    keep_last: int = 4,
) -> list[dict[str, Any]]:
    artifact = compact_messages_with_summary(
        _conversation_messages(loaded.history),
        summary=summary,
        keep_last=keep_last,
    )
    covered_messages = list(loaded.history[: artifact.summarized_message_count])
    if covered_messages:
        artifact.messages[0]["metadata"]["coding_deepgent_compact"]["start_message_id"] = covered_messages[0].message_id
        artifact.messages[0]["metadata"]["coding_deepgent_compact"]["end_message_id"] = covered_messages[-1].message_id
        artifact.messages[0]["metadata"]["coding_deepgent_compact"]["covered_message_ids"] = [
            message.message_id for message in covered_messages
        ]
    return [
        build_resume_context_message(loaded),
        *artifact.messages,
    ]


def compacted_continuation_projection(
    loaded: LoadedSession,
    *,
    summary: str,
    keep_last: int = 4,
) -> TranscriptProjection:
    artifact = compact_messages_with_summary(
        _conversation_messages(loaded.history),
        summary=summary,
        keep_last=keep_last,
    )
    tail_entries = [
        (message.message_id,)
        for message in loaded.history[artifact.summarized_message_count :]
    ]
    messages = [
        build_resume_context_message(loaded),
        *artifact.messages,
    ]
    return _project_transcript_projection(
        messages,
        [(), (), (), *tail_entries],
    )


def generated_compacted_continuation_history(
    loaded: LoadedSession,
    *,
    summarizer: Any,
    keep_last: int = 4,
    custom_instructions: str | None = None,
) -> list[dict[str, Any]]:
    summary = generate_compact_summary(
        _conversation_messages(loaded.history),
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
        run_prompt=lambda prompt, history, session_state, session_id, transcript_projection: run_once(
            settings=active_settings_loader(),
            prompt=prompt,
            run_agent=run_agent,
            history=history,
            session_state=session_state,
            session_id=session_id,
            transcript_projection=transcript_projection,
        ),
        doctor_checks=lambda: doctor_checks(active_settings_loader()),
    )


def _runtime_store(settings: Settings) -> object:
    container = _build_container_for_settings(settings)
    store = container.runtime.store()
    if store is None:
        raise RuntimeError("Runtime store is not configured")
    return store


def _build_container_for_settings(settings: Settings):
    container = bootstrap.build_container(
        settings_loader=lambda: settings,
        model_factory=build_model,
        create_agent_factory=create_agent,
    )
    bootstrap.validate_container_startup(container=container)
    return container
