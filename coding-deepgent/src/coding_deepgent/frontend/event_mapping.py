from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, cast

from coding_deepgent.runtime import RuntimeEvent
from coding_deepgent.tasks.store import TaskStore, list_tasks

from .protocol import (
    RuntimeEventPayload,
    TaskItemPayload,
    TaskSnapshotEvent,
    TodoItemPayload,
    TodoSnapshotEvent,
    ToolFailedEvent,
    ToolFinishedEvent,
    ToolStartedEvent,
)


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
