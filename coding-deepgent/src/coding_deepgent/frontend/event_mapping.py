from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Literal, cast

from coding_deepgent.runtime import RuntimeEvent
from coding_deepgent.sessions import LoadedSession, build_session_inspect_view
from coding_deepgent.subagents.background import BACKGROUND_SUBAGENT_MANAGER
from coding_deepgent.tasks.store import TaskStore, list_tasks

from .protocol import (
    BackgroundSubagentItemPayload,
    BackgroundSubagentSnapshotEvent,
    ContextSnapshotEvent,
    RuntimeEventPayload,
    SubagentItemPayload,
    SubagentSnapshotEvent,
    TaskItemPayload,
    TaskSnapshotEvent,
    TodoItemPayload,
    TodoSnapshotEvent,
    ToolFailedEvent,
    ToolFinishedEvent,
    ToolStartedEvent,
)

ContextProjectionMode = Literal["raw", "compact", "collapse"]


def todo_snapshot_from_state(state: Mapping[str, Any]) -> TodoSnapshotEvent:
    raw_items = state.get("todos", [])
    items: list[TodoItemPayload] = []
    if isinstance(raw_items, list):
        for raw in raw_items:
            if not isinstance(raw, Mapping):
                continue
            content = raw.get("content")
            status = raw.get("status")
            if not isinstance(content, str) or status not in {
                "pending",
                "in_progress",
                "completed",
            }:
                continue
            active_form = raw.get("activeForm")
            items.append(
                TodoItemPayload(
                    content=content,
                    status=status,
                    activeForm=active_form if isinstance(active_form, str) else None,
                )
            )
    return TodoSnapshotEvent(items=items)


def task_snapshot_from_store(store: object | None) -> TaskSnapshotEvent:
    if store is None:
        return TaskSnapshotEvent(items=[])
    try:
        records = list_tasks(cast(TaskStore, store))
    except Exception:
        return TaskSnapshotEvent(items=[])
    return TaskSnapshotEvent(
        items=[
            TaskItemPayload(
                id=record.id,
                content=record.title,
                status=record.status,
                owner=record.owner,
            )
            for record in records
        ]
    )


def context_snapshot_from_loaded(loaded: LoadedSession) -> ContextSnapshotEvent:
    view = build_session_inspect_view(loaded)
    latest_event = view.timeline[-1].event_type if view.timeline else None
    return ContextSnapshotEvent(
        projection_mode=cast(ContextProjectionMode, view.projection_mode),
        history_messages=len(view.raw_messages),
        model_messages=len(view.model_projection),
        visible_messages=view.visible_raw_count,
        hidden_messages=view.hidden_raw_count,
        compact_count=view.compact_count,
        collapse_count=view.collapse_count,
        session_memory_status=view.session_memory.status,
        latest_event=latest_event,
    )


def subagent_snapshot_from_loaded(
    loaded: LoadedSession,
    *,
    limit: int = 5,
) -> SubagentSnapshotEvent:
    messages = loaded.sidechain_messages[-limit:] if limit > 0 else []
    return SubagentSnapshotEvent(
        total=len(loaded.sidechain_messages),
        items=[
            SubagentItemPayload(
                created_at=message.created_at,
                agent_type=message.agent_type,
                role=message.role,
                content=message.content[:500],
                subagent_thread_id=message.subagent_thread_id,
            )
            for message in messages
        ],
    )


def background_subagent_snapshot_from_runtime(
    runtime: object,
    *,
    include_terminal: bool = True,
    limit: int = 8,
) -> BackgroundSubagentSnapshotEvent:
    try:
        runs = BACKGROUND_SUBAGENT_MANAGER.list_runs(
            runtime=cast(Any, runtime),
            include_terminal=include_terminal,
        )
    except Exception:
        return BackgroundSubagentSnapshotEvent(total=0, items=[])
    selected = runs[-limit:] if limit > 0 else ()
    return BackgroundSubagentSnapshotEvent(
        total=len(runs),
        items=[
            BackgroundSubagentItemPayload(
                run_id=run.run_id,
                status=run.status,
                mode=run.mode,
                agent_type=run.agent_type,
                progress_summary=run.progress_summary,
                pending_inputs=len(run.pending_inputs),
                total_invocations=run.total_invocations,
            )
            for run in selected
        ],
    )


def runtime_events_to_frontend(
    events: Iterable[RuntimeEvent],
) -> list[RuntimeEventPayload | ToolStartedEvent | ToolFinishedEvent | ToolFailedEvent]:
    mapped: list[
        RuntimeEventPayload | ToolStartedEvent | ToolFinishedEvent | ToolFailedEvent
    ] = []
    for event in events:
        metadata = dict(event.metadata)
        source = metadata.get("source")
        phase = metadata.get("phase")
        tool_name = metadata.get("tool")
        tool_call_id = metadata.get("tool_call_id")
        if source == "tool_guard" and isinstance(tool_name, str):
            mapped.extend(
                _tool_guard_event(
                    phase=str(phase or event.kind),
                    tool_name=tool_name,
                    tool_call_id=str(tool_call_id or f"{event.session_id}:{event.kind}"),
                    message=event.message,
                )
            )
            continue
        mapped.append(
            RuntimeEventPayload(
                kind=event.kind,
                message=event.message,
                metadata=_safe_metadata(metadata),
            )
        )
    return mapped


def _tool_guard_event(
    *,
    phase: str,
    tool_name: str,
    tool_call_id: str,
    message: str,
) -> list[ToolStartedEvent | ToolFinishedEvent | ToolFailedEvent]:
    if phase == "allowed":
        return [
            ToolStartedEvent(
                tool_call_id=tool_call_id,
                name=tool_name,
                summary=message,
            )
        ]
    if phase == "completed":
        return [
            ToolFinishedEvent(
                tool_call_id=tool_call_id,
                name=tool_name,
                preview=message,
            )
        ]
    if phase in {"failed", "permission_denied", "permission_ask", "feedback_blocked"}:
        return [
            ToolFailedEvent(
                tool_call_id=tool_call_id,
                name=tool_name,
                error=message,
            )
        ]
    return []


def _safe_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, str | int | float | bool) or value is None:
            safe[str(key)] = value
    return safe
