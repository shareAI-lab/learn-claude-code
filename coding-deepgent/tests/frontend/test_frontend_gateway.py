from __future__ import annotations

from pathlib import Path
import threading
import time

from fastapi.testclient import TestClient

from coding_deepgent.frontend.gateway import create_app
from coding_deepgent.frontend.producer import PromptRunResult
from coding_deepgent.settings import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        workdir=tmp_path / "workdir",
        session_dir=tmp_path / "sessions",
        model_name="gpt-test",
    )


def test_gateway_health_endpoint(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()

    with TestClient(create_app(fake=True, settings=settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "coding-deepgent-frontend-gateway",
    }


def test_gateway_serves_minimal_web_ui(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()

    with TestClient(create_app(fake=True, settings=settings)) as client:
        response = client.get("/ui")

    assert response.status_code == 200
    assert "<title>coding-deepgent web ui</title>" in response.text
    assert 'id="prompt"' in response.text
    assert "/api/runs" in response.text


def test_gateway_run_stream_returns_sse_events(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()

    with TestClient(create_app(fake=True, settings=settings)) as client:
        with client.stream("POST", "/api/runs/stream", json={"prompt": "hello"}) as response:
            content_location = response.headers["Content-Location"]
            lines = [line for line in response.iter_lines() if line]

    assert response.status_code == 200
    assert content_location.startswith("/api/runs/")
    assert any("event: metadata" in line for line in lines)
    assert any("event: assistant_delta" in line for line in lines)
    assert any("event: run_finished" in line for line in lines)
    assert any("event: end" in line for line in lines)


def test_gateway_rejects_concurrent_run_on_same_thread(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()
    release = threading.Event()

    def slow_runner(
        prompt,
        history,
        session_state,
        session_id,
        assistant_message_id,
        emit,
    ) -> PromptRunResult:
        del history, session_state, session_id, assistant_message_id, emit
        release.wait(timeout=2)
        return PromptRunResult(text=f"done {prompt}")

    with TestClient(create_app(settings=settings, prompt_runner=slow_runner)) as client:
        response_one = client.post("/api/runs", json={"prompt": "first", "thread_id": "thread-1"})
        time.sleep(0.05)
        response_two = client.post("/api/runs", json={"prompt": "second", "thread_id": "thread-1"})
        release.set()

    assert response_one.status_code == 200
    assert response_two.status_code == 409
