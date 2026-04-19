from __future__ import annotations

from coding_deepgent.frontend.adapters.sse import format_sse, sse_consumer
from coding_deepgent.frontend.stream_bridge import MemoryStreamBridge


def test_format_sse_includes_event_data_and_id() -> None:
    frame = format_sse("values", {"title": "hello"}, event_id="evt-1")

    assert "event: values" in frame
    assert 'data: {"title": "hello"}' in frame
    assert "id: evt-1" in frame


def test_sse_consumer_formats_bridge_entries() -> None:
    bridge = MemoryStreamBridge()
    bridge.publish("run-1", "metadata", {"run_id": "run-1"})
    bridge.publish("run-1", "values", {"title": "hello"})
    bridge.publish_end("run-1")

    frames = list(sse_consumer(bridge, "run-1", heartbeat_interval=0.01))

    assert frames[0].startswith("event: metadata")
    assert frames[1].startswith("event: values")
    assert frames[-1].startswith("event: end")
