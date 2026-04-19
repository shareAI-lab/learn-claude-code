from __future__ import annotations

from coding_deepgent.frontend.stream_bridge import (
    END_SENTINEL,
    HEARTBEAT_SENTINEL,
    MemoryStreamBridge,
)


def test_stream_bridge_replays_events_after_last_event_id() -> None:
    bridge = MemoryStreamBridge()
    bridge.publish("run-1", "metadata", {"run_id": "run-1"})
    bridge.publish("run-1", "values", {"title": "one"})
    bridge.publish_end("run-1")

    replay = list(bridge.subscribe("run-1", last_event_id=""))
    assert [entry.event for entry in replay[:-1]] == ["metadata", "values"]
    assert replay[-1] is END_SENTINEL

    first_event_id = replay[0].id
    resumed = list(bridge.subscribe("run-1", last_event_id=first_event_id))
    assert [entry.event for entry in resumed[:-1]] == ["values"]
    assert resumed[-1] is END_SENTINEL


def test_stream_bridge_heartbeat_when_idle() -> None:
    bridge = MemoryStreamBridge()
    stream = bridge.subscribe("run-2", heartbeat_interval=0.01)
    assert next(stream) is HEARTBEAT_SENTINEL

