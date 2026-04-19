from __future__ import annotations

from pathlib import Path

from coding_deepgent.frontend.runs import FrontendRunService
from coding_deepgent.settings import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        workdir=tmp_path / "workdir",
        session_dir=tmp_path / "sessions",
        model_name="gpt-test",
    )


def test_run_service_publishes_metadata_and_frontend_events(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()
    service = FrontendRunService(settings=settings, fake=True)

    record = service.start_run(thread_id="thread-1", prompt="hello")
    assert record.worker is not None
    record.worker.join(timeout=5)

    events = list(service.bridge.subscribe(record.run_id, heartbeat_interval=0.01))
    event_names = [entry.event for entry in events[:-1]]
    assert event_names[:3] == ["metadata", "session_started", "user_message"]
    assert "assistant_delta" in event_names
    assert "assistant_message" in event_names
    assert "run_finished" in event_names

    refreshed = service.run_manager.get(record.run_id)
    assert refreshed is not None
    assert refreshed.status == "completed"
