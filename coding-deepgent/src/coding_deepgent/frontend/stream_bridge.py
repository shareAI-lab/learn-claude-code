from __future__ import annotations

import threading
import time
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StreamEntry:
    id: str
    event: str
    data: Any


HEARTBEAT_SENTINEL = StreamEntry(id="", event="__heartbeat__", data=None)
END_SENTINEL = StreamEntry(id="", event="__end__", data=None)


@dataclass
class _RunStream:
    entries: list[StreamEntry] = field(default_factory=list)
    condition: threading.Condition = field(default_factory=threading.Condition)
    ended: bool = False
    start_offset: int = 0


class MemoryStreamBridge:
    """In-memory per-run event log for future SSE consumers."""

    def __init__(self, *, max_entries: int = 256) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._streams: dict[str, _RunStream] = {}
        self._counters: dict[str, int] = {}
        self._lock = threading.Lock()

    def publish(self, run_id: str, event: str, data: Any) -> None:
        stream = self._get_or_create_stream(run_id)
        entry = StreamEntry(id=self._next_id(run_id), event=event, data=data)
        with stream.condition:
            stream.entries.append(entry)
            if len(stream.entries) > self._max_entries:
                overflow = len(stream.entries) - self._max_entries
                del stream.entries[:overflow]
                stream.start_offset += overflow
            stream.condition.notify_all()

    def publish_end(self, run_id: str) -> None:
        stream = self._get_or_create_stream(run_id)
        with stream.condition:
            stream.ended = True
            stream.condition.notify_all()

    def subscribe(
        self,
        run_id: str,
        *,
        last_event_id: str | None = None,
        heartbeat_interval: float = 15.0,
    ) -> Generator[StreamEntry, None, None]:
        stream = self._get_or_create_stream(run_id)
        next_offset = self._resolve_start_offset(stream, last_event_id)
        while True:
            with stream.condition:
                if next_offset < stream.start_offset:
                    next_offset = stream.start_offset
                local_index = next_offset - stream.start_offset
                if 0 <= local_index < len(stream.entries):
                    entry = stream.entries[local_index]
                    next_offset += 1
                elif stream.ended:
                    entry = END_SENTINEL
                else:
                    notified = stream.condition.wait(timeout=heartbeat_interval)
                    if not notified:
                        entry = HEARTBEAT_SENTINEL
                    else:
                        continue
            yield entry
            if entry is END_SENTINEL:
                return

    def cleanup(self, run_id: str) -> None:
        with self._lock:
            self._streams.pop(run_id, None)
            self._counters.pop(run_id, None)

    def _get_or_create_stream(self, run_id: str) -> _RunStream:
        with self._lock:
            stream = self._streams.get(run_id)
            if stream is None:
                stream = _RunStream()
                self._streams[run_id] = stream
                self._counters[run_id] = 0
            return stream

    def _next_id(self, run_id: str) -> str:
        with self._lock:
            current = self._counters.get(run_id, 0)
            self._counters[run_id] = current + 1
        return f"{int(time.time() * 1000)}-{current}"

    def _resolve_start_offset(
        self, stream: _RunStream, last_event_id: str | None
    ) -> int:
        if last_event_id is None:
            return stream.start_offset
        for index, entry in enumerate(stream.entries):
            if entry.id == last_event_id:
                return stream.start_offset + index + 1
        return stream.start_offset

