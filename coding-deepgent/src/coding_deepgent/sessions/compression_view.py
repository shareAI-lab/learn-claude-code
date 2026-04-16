from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

from .records import LoadedSession, SessionCollapse, SessionCompact, SessionMessage

ProjectionMode = Literal["selected", "raw", "compact", "collapse"]
ProjectionSource = Literal[
    "raw",
    "compact_boundary",
    "compact_summary",
    "collapse_boundary",
    "collapse_summary",
]


@dataclass(frozen=True, slots=True)
class RawTranscriptMessageView:
    message_id: str
    created_at: str
    role: str
    content: str
    metadata: dict[str, Any] | None
    model_visible: bool
    hidden_by_event_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectionMessageView:
    role: str
    content: Any
    source: ProjectionSource
    message_id: str | None = None
    event_id: str | None = None
    covered_message_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CompressionTimelineEvent:
    event_id: str
    event_type: str
    created_at: str
    trigger: str | None
    summary: str
    affected_message_ids: tuple[str, ...] = ()
    affected_tool_call_ids: tuple[str, ...] = ()
    source: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CompressionView:
    raw_messages: tuple[RawTranscriptMessageView, ...]
    model_projection: tuple[ProjectionMessageView, ...]
    timeline: tuple[CompressionTimelineEvent, ...]
    projection_mode: ProjectionMode


def build_compression_view(
    loaded: LoadedSession,
    *,
    projection_mode: ProjectionMode = "selected",
) -> CompressionView:
    resolved_mode = _resolve_projection_mode(loaded, projection_mode)
    projection = _projection_messages(loaded, resolved_mode)
    hidden_by_message = _hidden_message_events(projection)
    return CompressionView(
        raw_messages=_raw_message_views(loaded.history, hidden_by_message),
        model_projection=projection,
        timeline=_timeline_events(loaded),
        projection_mode=resolved_mode,
    )


def _resolve_projection_mode(
    loaded: LoadedSession,
    projection_mode: ProjectionMode,
) -> ProjectionMode:
    if projection_mode != "selected":
        return projection_mode
    if loaded.collapsed_history_source.mode == "collapse":
        return "collapse"
    if loaded.compacted_history_source.mode == "compact":
        return "compact"
    return "raw"


def _projection_messages(
    loaded: LoadedSession,
    projection_mode: ProjectionMode,
) -> tuple[ProjectionMessageView, ...]:
    if projection_mode == "raw":
        return tuple(_raw_projection_message(message) for message in loaded.history)
    if projection_mode == "compact":
        compact_index = loaded.compacted_history_source.compact_index
        if compact_index is None:
            return tuple(_raw_projection_message(message) for message in loaded.history)
        return _compact_projection_messages(loaded, compact_index)
    if projection_mode == "collapse":
        spans = _selected_collapse_spans(loaded)
        if not spans:
            return tuple(_raw_projection_message(message) for message in loaded.history)
        return _collapse_projection_messages(loaded, spans)
    return tuple(_raw_projection_message(message) for message in loaded.history)


def _raw_projection_message(message: SessionMessage) -> ProjectionMessageView:
    return ProjectionMessageView(
        role=message.role,
        content=message.content,
        source="raw",
        message_id=message.message_id,
        metadata=deepcopy(message.metadata) if message.metadata is not None else None,
    )


def _compact_projection_messages(
    loaded: LoadedSession,
    compact_index: int,
) -> tuple[ProjectionMessageView, ...]:
    compact = loaded.compacts[compact_index]
    event_id = f"compact-{compact_index}"
    end_index = _message_index_by_id(loaded.history).get(compact.end_message_id, -1)
    affected = _covered_message_ids(loaded.history, compact)
    messages: list[ProjectionMessageView] = [
        ProjectionMessageView(
            role="system",
            content=_projection_content(loaded.compacted_history, 0),
            source="compact_boundary",
            event_id=event_id,
            covered_message_ids=affected,
            metadata=deepcopy(compact.metadata) if compact.metadata is not None else None,
        ),
        ProjectionMessageView(
            role="user",
            content=_projection_content(loaded.compacted_history, 1),
            source="compact_summary",
            event_id=event_id,
            covered_message_ids=affected,
        ),
    ]
    messages.extend(
        _raw_projection_message(message) for message in loaded.history[end_index + 1 :]
    )
    return tuple(messages)


def _collapse_projection_messages(
    loaded: LoadedSession,
    spans: list[tuple[int, int, int]],
) -> tuple[ProjectionMessageView, ...]:
    messages: list[ProjectionMessageView] = []
    cursor = 0
    for start_index, end_index, collapse_index in spans:
        messages.extend(
            _raw_projection_message(message)
            for message in loaded.history[cursor:start_index]
        )
        collapse = loaded.collapses[collapse_index]
        event_id = f"collapse-{collapse_index}"
        affected = _covered_message_ids(loaded.history, collapse)
        messages.extend(
            (
                ProjectionMessageView(
                    role="system",
                    content=_collapse_boundary_text(collapse),
                    source="collapse_boundary",
                    event_id=event_id,
                    covered_message_ids=affected,
                    metadata=(
                        deepcopy(collapse.metadata)
                        if collapse.metadata is not None
                        else None
                    ),
                ),
                ProjectionMessageView(
                    role="user",
                    content=collapse.summary,
                    source="collapse_summary",
                    event_id=event_id,
                    covered_message_ids=affected,
                ),
            )
        )
        cursor = end_index + 1
    messages.extend(_raw_projection_message(message) for message in loaded.history[cursor:])
    return tuple(messages)


def _timeline_events(loaded: LoadedSession) -> tuple[CompressionTimelineEvent, ...]:
    events: list[CompressionTimelineEvent] = []
    for index, compact in enumerate(loaded.compacts):
        event_id = f"compact-{index}"
        metadata = deepcopy(compact.metadata) if compact.metadata is not None else None
        events.append(
            CompressionTimelineEvent(
                event_id=event_id,
                event_type="compact",
                created_at=compact.created_at,
                trigger=compact.trigger,
                summary=compact.summary,
                affected_message_ids=_covered_message_ids(loaded.history, compact),
                source=_metadata_source(metadata),
                metadata=metadata,
            )
        )
    for index, collapse in enumerate(loaded.collapses):
        event_id = f"collapse-{index}"
        metadata = deepcopy(collapse.metadata) if collapse.metadata is not None else None
        events.append(
            CompressionTimelineEvent(
                event_id=event_id,
                event_type="collapse",
                created_at=collapse.created_at,
                trigger=collapse.trigger,
                summary=collapse.summary,
                affected_message_ids=_covered_message_ids(loaded.history, collapse),
                source=_metadata_source(metadata),
                metadata=metadata,
            )
        )
    for index, evidence in enumerate(loaded.evidence):
        if evidence.kind != "runtime_event":
            continue
        metadata = deepcopy(evidence.metadata) if evidence.metadata is not None else None
        events.append(
            CompressionTimelineEvent(
                event_id=f"runtime-event-{index}",
                event_type=_runtime_event_type(evidence.metadata),
                created_at=evidence.created_at,
                trigger=_metadata_text(evidence.metadata, "trigger"),
                summary=evidence.summary,
                affected_message_ids=_metadata_string_tuple(
                    evidence.metadata,
                    "affected_message_ids",
                ),
                affected_tool_call_ids=_metadata_string_tuple(
                    evidence.metadata,
                    "affected_tool_call_ids",
                ),
                source=_metadata_source(metadata),
                metadata=metadata,
            )
        )
    return tuple(sorted(events, key=lambda event: (event.created_at, event.event_id)))


def _raw_message_views(
    messages: list[SessionMessage],
    hidden_by_message: dict[str, tuple[str, ...]],
) -> tuple[RawTranscriptMessageView, ...]:
    return tuple(
        RawTranscriptMessageView(
            message_id=message.message_id,
            created_at=message.created_at,
            role=message.role,
            content=message.content,
            metadata=deepcopy(message.metadata) if message.metadata is not None else None,
            model_visible=message.message_id not in hidden_by_message,
            hidden_by_event_ids=hidden_by_message.get(message.message_id, ()),
        )
        for message in messages
    )


def _hidden_message_events(
    projection: tuple[ProjectionMessageView, ...],
) -> dict[str, tuple[str, ...]]:
    hidden: dict[str, list[str]] = {}
    for message in projection:
        if message.source == "raw" or message.event_id is None:
            continue
        for message_id in message.covered_message_ids:
            hidden.setdefault(message_id, [])
            if message.event_id not in hidden[message_id]:
                hidden[message_id].append(message.event_id)
    return {
        message_id: tuple(event_ids)
        for message_id, event_ids in hidden.items()
    }


def _selected_collapse_spans(
    loaded: LoadedSession,
) -> list[tuple[int, int, int]]:
    id_to_index = _message_index_by_id(loaded.history)
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


def _covered_message_ids(
    messages: list[SessionMessage],
    event: SessionCompact | SessionCollapse,
) -> tuple[str, ...]:
    if event.covered_message_ids is not None:
        return event.covered_message_ids
    index_by_id = _message_index_by_id(messages)
    start_index = index_by_id.get(event.start_message_id)
    end_index = index_by_id.get(event.end_message_id)
    if start_index is None or end_index is None or end_index < start_index:
        return ()
    return tuple(message.message_id for message in messages[start_index : end_index + 1])


def _message_index_by_id(messages: list[SessionMessage]) -> dict[str, int]:
    return {message.message_id: index for index, message in enumerate(messages)}


def _projection_content(messages: list[dict[str, Any]], index: int) -> Any:
    if index >= len(messages):
        return ""
    return deepcopy(messages[index].get("content", ""))


def _collapse_boundary_text(collapse: SessionCollapse) -> str:
    affected_count = len(collapse.covered_message_ids or ())
    return (
        "coding-deepgent collapse boundary: "
        f"trigger={collapse.trigger}; collapsed_messages={affected_count}"
    )


def _runtime_event_type(metadata: dict[str, Any] | None) -> str:
    value = _metadata_text(metadata, "event_kind")
    return value or "runtime_event"


def _metadata_source(metadata: dict[str, Any] | None) -> str | None:
    return _metadata_text(metadata, "source")


def _metadata_text(metadata: dict[str, Any] | None, key: str) -> str | None:
    if not isinstance(metadata, dict):
        return None
    value = metadata.get(key)
    return value if isinstance(value, str) and value else None


def _metadata_string_tuple(
    metadata: dict[str, Any] | None,
    key: str,
) -> tuple[str, ...]:
    if not isinstance(metadata, dict):
        return ()
    value = metadata.get(key)
    if isinstance(value, str) and value:
        return (value,)
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, str) and item)
    return ()
