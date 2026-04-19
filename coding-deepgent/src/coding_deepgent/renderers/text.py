from __future__ import annotations

from collections.abc import Mapping, Sequence
from io import StringIO
import json
from typing import Any

from rich import box
from rich.console import Console
from rich.table import Table

from coding_deepgent.sessions.inspection import SessionInspectView

_RENDER_WIDTH = 140


def _render_table(table: Table) -> str:
    stream = StringIO()
    console = Console(
        file=stream,
        color_system=None,
        force_terminal=False,
        record=True,
        width=_RENDER_WIDTH,
    )
    console.print(table)
    return console.export_text(styles=False).rstrip()


def render_config_table(rows: Sequence[tuple[str, str]]) -> str:
    table = Table(title="Configuration", box=box.SIMPLE_HEAVY, show_header=False)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    for key, value in rows:
        table.add_row(key, value)
    return _render_table(table)


def render_session_table(sessions: Sequence[Mapping[str, Any]]) -> str:
    if not sessions:
        return "No sessions recorded yet."

    table = Table(title="Sessions", box=box.SIMPLE_HEAVY)
    table.add_column("Session", style="cyan", no_wrap=True)
    table.add_column("Updated", no_wrap=True)
    table.add_column("Messages", justify="right", no_wrap=True)
    table.add_column("Workdir")
    for session in sessions:
        table.add_row(
            str(session.get("session_id", "unknown")),
            str(session.get("updated_at", "-")),
            str(session.get("message_count", 0)),
            str(session.get("workdir", "-")),
        )
    return _render_table(table)


def render_doctor_table(checks: Sequence[Mapping[str, Any]]) -> str:
    table = Table(title="Doctor", box=box.SIMPLE_HEAVY)
    table.add_column("Check", style="cyan", no_wrap=True, overflow="fold")
    table.add_column("Status", no_wrap=True, overflow="fold")
    table.add_column("Detail", overflow="fold")
    for check in checks:
        table.add_row(
            str(check.get("name", "unknown")),
            str(check.get("status", "unknown")),
            str(check.get("detail", "")),
        )
    return _render_table(table)


def render_task_table(tasks: Sequence[Mapping[str, Any]]) -> str:
    if not tasks:
        return "No tasks recorded."
    table = Table(title="Tasks", box=box.SIMPLE_HEAVY)
    table.add_column("Task", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Ready", no_wrap=True)
    table.add_column("Owner", no_wrap=True)
    table.add_column("Depends On")
    table.add_column("Title")
    for task in tasks:
        metadata = task.get("metadata", {})
        ready = "-"
        if isinstance(metadata, Mapping):
            ready = str(metadata.get("ready", "-"))
        depends_on = task.get("depends_on", [])
        depends_text = ", ".join(str(item) for item in depends_on) if isinstance(depends_on, Sequence) and not isinstance(depends_on, str) else "-"
        table.add_row(
            str(task.get("id", "unknown")),
            str(task.get("status", "-")),
            ready,
            str(task.get("owner", "-") or "-"),
            depends_text or "-",
            str(task.get("title", "")),
        )
    return _render_table(table)


def render_plan_table(plans: Sequence[Mapping[str, Any]]) -> str:
    if not plans:
        return "No plans recorded."
    table = Table(title="Plans", box=box.SIMPLE_HEAVY)
    table.add_column("Plan", style="cyan", no_wrap=True)
    table.add_column("Title")
    table.add_column("Tasks")
    table.add_column("Verification")
    for plan in plans:
        task_ids = plan.get("task_ids", [])
        tasks_text = ", ".join(str(item) for item in task_ids) if isinstance(task_ids, Sequence) and not isinstance(task_ids, str) else "-"
        table.add_row(
            str(plan.get("id", "unknown")),
            str(plan.get("title", "")),
            tasks_text or "-",
            _preview(plan.get("verification", "")),
        )
    return _render_table(table)


def render_subagent_table(runs: Sequence[Mapping[str, Any]]) -> str:
    if not runs:
        return "No background subagent runs recorded."
    table = Table(title="Subagents", box=box.SIMPLE_HEAVY)
    table.add_column("Run", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Mode", no_wrap=True)
    table.add_column("Agent", no_wrap=True)
    table.add_column("Pending", justify="right", no_wrap=True)
    table.add_column("Calls", justify="right", no_wrap=True)
    table.add_column("Progress")
    for run in runs:
        pending_inputs = run.get("pending_inputs", [])
        pending_count = (
            len(pending_inputs)
            if isinstance(pending_inputs, Sequence) and not isinstance(pending_inputs, str)
            else 0
        )
        table.add_row(
            str(run.get("run_id", "unknown")),
            str(run.get("status", "-")),
            str(run.get("mode", "-")),
            str(run.get("agent_type", "-")),
            str(pending_count),
            str(run.get("total_invocations", 0)),
            _preview(run.get("progress_summary", "")),
        )
    return _render_table(table)


def render_object_detail(title: str, payload: Mapping[str, Any]) -> str:
    table = Table(title=title, box=box.SIMPLE_HEAVY, show_header=False)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value")
    for key in sorted(payload):
        table.add_row(str(key), _preview(payload[key], limit=500))
    return _render_table(table)


def render_session_inspect_view(
    view: SessionInspectView,
    *,
    show_recovery: bool = True,
    show_model: bool = True,
    show_raw: bool = True,
    limit: int = 20,
) -> str:
    lines: list[str] = ["Session Inspect", ""]
    lines.extend(
        [
            f"session_id: {view.session_id}",
            f"workdir: {view.workdir}",
            f"transcript: {view.transcript_path}",
            f"created_at: {view.created_at or '-'}",
            f"updated_at: {view.updated_at or '-'}",
            (
                "counts: "
                f"messages={view.message_count} "
                f"evidence={view.evidence_count} "
                f"compacts={view.compact_count} "
                f"collapses={view.collapse_count} "
                f"sidechain={view.sidechain_count}"
            ),
            (
                "projection: "
                f"mode={view.projection_mode} "
                f"model_messages={len(view.model_projection)} "
                f"raw_visible={view.visible_raw_count} "
                f"raw_hidden={view.hidden_raw_count}"
            ),
            _session_memory_line(view),
        ]
    )
    if show_recovery:
        lines.extend(("", "Recovery Brief", _indent(view.recovery_brief)))
    lines.extend(("", "Compression Timeline"))
    lines.extend(_timeline_lines(view, limit=limit))
    if show_model:
        lines.extend(("", "Model Projection"))
        lines.extend(_projection_lines(view, limit=limit))
    if show_raw:
        lines.extend(("", "Raw Transcript Visibility"))
        lines.extend(_raw_lines(view, limit=limit))
    return "\n".join(lines).rstrip()


def render_session_history_table(
    view: SessionInspectView,
    *,
    limit: int = 50,
) -> str:
    return "\n".join(["Raw Transcript Visibility", *_raw_lines(view, limit=limit)])


def render_session_projection_table(
    view: SessionInspectView,
    *,
    limit: int = 50,
) -> str:
    return "\n".join(
        [
            f"Model Projection ({view.projection_mode})",
            *_projection_lines(view, limit=limit),
        ]
    )


def render_session_timeline_table(
    view: SessionInspectView,
    *,
    limit: int = 50,
) -> str:
    return "\n".join(["Compression Timeline", *_timeline_lines(view, limit=limit)])


def render_evidence_table(
    title: str,
    evidence: Sequence[Mapping[str, Any]],
    *,
    limit: int = 50,
) -> str:
    if not evidence:
        return f"No {title.lower()} recorded."
    table = Table(title=title, box=box.SIMPLE_HEAVY)
    table.add_column("Created", no_wrap=True)
    table.add_column("Kind", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Subject", no_wrap=True)
    table.add_column("Summary")
    for item in evidence[:limit]:
        table.add_row(
            str(item.get("created_at", "-")),
            str(item.get("kind", "-")),
            str(item.get("status", "-")),
            str(item.get("subject", "-") or "-"),
            _preview(item.get("summary", "")),
        )
    rendered = _render_table(table)
    if len(evidence) > limit:
        rendered = f"{rendered}\n... {len(evidence) - limit} more"
    return rendered


def render_extension_table(
    title: str,
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not rows:
        return f"No {title.lower()} recorded."
    table = Table(title=title, box=box.SIMPLE_HEAVY)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Description")
    table.add_column("Path")
    for row in rows:
        table.add_row(
            str(row.get("name", "unknown")),
            str(row.get("status", "-")),
            _preview(row.get("description", "")),
            str(row.get("path", "-")),
        )
    return _render_table(table)


def render_acceptance_table(rows: Sequence[Mapping[str, Any]]) -> str:
    table = Table(title="Circle 1 Acceptance", box=box.SIMPLE_HEAVY)
    table.add_column("Check", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Detail")
    for row in rows:
        table.add_row(
            str(row.get("name", "unknown")),
            str(row.get("status", "unknown")),
            str(row.get("detail", "")),
        )
    return _render_table(table)


def _session_memory_line(view: SessionInspectView) -> str:
    memory = view.session_memory
    if memory.status == "missing":
        return (
            "session_memory: missing "
            f"(messages={memory.current_message_count}; "
            f"tokens~={memory.estimated_token_count}; tools={memory.tool_call_count})"
        )
    return (
        f"session_memory: {memory.status} "
        f"source={memory.source or '-'} "
        f"artifact_messages={memory.artifact_message_count} "
        f"current_messages={memory.current_message_count} "
        f"tokens~={memory.estimated_token_count} "
        f"tools={memory.tool_call_count} "
        f"preview={_preview(memory.content)}"
    )


def _timeline_lines(view: SessionInspectView, *, limit: int) -> list[str]:
    if not view.timeline:
        return ["- none"]
    rows = []
    for event in view.timeline[:limit]:
        affected = ",".join(event.affected_message_ids) or "-"
        tools = ",".join(event.affected_tool_call_ids) or "-"
        rows.append(
            "- "
            f"{event.event_id} {event.event_type} "
            f"trigger={event.trigger or '-'} "
            f"source={event.source or '-'} "
            f"messages={affected} "
            f"tools={tools} "
            f"summary={_preview(event.summary)}"
        )
    return _with_limit(rows, len(view.timeline), limit)


def _projection_lines(view: SessionInspectView, *, limit: int) -> list[str]:
    if not view.model_projection:
        return ["- none"]
    rows = []
    for index, message in enumerate(view.model_projection[:limit]):
        source_id = message.message_id or message.event_id or "-"
        covered = ",".join(message.covered_message_ids) or "-"
        rows.append(
            "- "
            f"#{index} role={message.role} source={message.source} "
            f"id={source_id} covers={covered} "
            f"preview={_preview(message.content)}"
        )
    return _with_limit(rows, len(view.model_projection), limit)


def _raw_lines(view: SessionInspectView, *, limit: int) -> list[str]:
    if not view.raw_messages:
        return ["- none"]
    rows = []
    for message in view.raw_messages[:limit]:
        visibility = "visible" if message.model_visible else "hidden"
        hidden_by = ",".join(message.hidden_by_event_ids) or "-"
        rows.append(
            "- "
            f"{message.message_id} role={message.role} {visibility} "
            f"hidden_by={hidden_by} preview={_preview(message.content)}"
        )
    return _with_limit(rows, len(view.raw_messages), limit)


def _with_limit(rows: list[str], total: int, limit: int) -> list[str]:
    if total > limit:
        rows.append(f"- ... {total - limit} more")
    return rows


def _indent(text: str) -> str:
    return "\n".join(f"  {line}" if line else "" for line in text.splitlines())


def _preview(value: Any, *, limit: int = 120) -> str:
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=True, sort_keys=True)
        except TypeError:
            text = str(value)
    text = " ".join(text.split())
    if len(text) > limit:
        return f"{text[: limit - 3]}..."
    return text
