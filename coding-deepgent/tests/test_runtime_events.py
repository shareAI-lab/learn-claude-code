from __future__ import annotations

import pytest

from coding_deepgent.runtime import (
    InMemoryEventSink,
    QueuedRuntimeEventSink,
    RuntimeEvent,
)


def test_queued_runtime_event_sink_drains_pending_events_in_order() -> None:
    queued = QueuedRuntimeEventSink()
    queued.emit(RuntimeEvent(kind="first", message="one", session_id="session-1"))
    queued.emit(RuntimeEvent(kind="second", message="two", session_id="session-1"))
    concrete = InMemoryEventSink()

    queued.attach(concrete)

    assert queued.pending_count == 0
    assert [event.kind for event in concrete.snapshot()] == ["first", "second"]
    queued.emit(RuntimeEvent(kind="third", message="three", session_id="session-1"))
    assert [event.kind for event in concrete.snapshot()] == [
        "first",
        "second",
        "third",
    ]


def test_queued_runtime_event_sink_rejects_unsafe_duplicate_attachment() -> None:
    queued = QueuedRuntimeEventSink()
    concrete = InMemoryEventSink()
    queued.attach(concrete)
    queued.attach(concrete)

    with pytest.raises(RuntimeError, match="already attached"):
        queued.attach(InMemoryEventSink())
