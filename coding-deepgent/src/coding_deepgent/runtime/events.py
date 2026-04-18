from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    kind: str
    message: str
    session_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RuntimeEventSink(Protocol):
    def emit(self, event: RuntimeEvent) -> None: ...


class NullEventSink:
    def emit(self, event: RuntimeEvent) -> None:
        del event


class InMemoryEventSink:
    def __init__(self) -> None:
        self._events: list[RuntimeEvent] = []

    def emit(self, event: RuntimeEvent) -> None:
        self._events.append(event)

    def snapshot(self) -> tuple[RuntimeEvent, ...]:
        return tuple(self._events)


class QueuedRuntimeEventSink:
    def __init__(
        self,
        sink: RuntimeEventSink | None = None,
        *,
        max_pending: int = 1024,
    ) -> None:
        if max_pending < 1:
            raise ValueError("max_pending must be positive")
        self._sink = sink
        self._pending: list[RuntimeEvent] = []
        self._max_pending = max_pending

    @property
    def attached(self) -> bool:
        return self._sink is not None

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def emit(self, event: RuntimeEvent) -> None:
        if self._sink is not None:
            self._sink.emit(event)
            return
        if len(self._pending) >= self._max_pending:
            raise RuntimeError("runtime event queue is full before sink attachment")
        self._pending.append(event)

    def attach(self, sink: RuntimeEventSink) -> None:
        if sink is self:
            raise ValueError("queued runtime event sink cannot attach to itself")
        if self._sink is sink:
            return
        if self._sink is not None:
            raise RuntimeError("runtime event sink is already attached")
        for event in self._pending:
            sink.emit(event)
        self._pending.clear()
        self._sink = sink

    def snapshot(self) -> tuple[RuntimeEvent, ...]:
        sink_snapshot = getattr(self._sink, "snapshot", None)
        if callable(sink_snapshot):
            return tuple(sink_snapshot())
        return tuple(self._pending)
