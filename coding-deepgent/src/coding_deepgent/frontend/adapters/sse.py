from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

from coding_deepgent.frontend.stream_bridge import (
    END_SENTINEL,
    HEARTBEAT_SENTINEL,
    MemoryStreamBridge,
)


def format_sse(event: str, data: Any, *, event_id: str | None = None) -> str:
    payload = json.dumps(data, default=str, ensure_ascii=False)
    parts = [f"event: {event}", f"data: {payload}"]
    if event_id:
        parts.append(f"id: {event_id}")
    parts.append("")
    parts.append("")
    return "\n".join(parts)


def sse_consumer(
    bridge: MemoryStreamBridge,
    run_id: str,
    *,
    last_event_id: str | None = None,
    heartbeat_interval: float = 15.0,
) -> Generator[str, None, None]:
    for entry in bridge.subscribe(
        run_id, last_event_id=last_event_id, heartbeat_interval=heartbeat_interval
    ):
        if entry is HEARTBEAT_SENTINEL:
            yield ": heartbeat\n\n"
            continue
        if entry is END_SENTINEL:
            yield format_sse("end", None, event_id=entry.id or None)
            return
        yield format_sse(entry.event, entry.data, event_id=entry.id or None)
