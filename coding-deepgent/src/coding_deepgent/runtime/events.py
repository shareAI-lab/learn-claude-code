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
