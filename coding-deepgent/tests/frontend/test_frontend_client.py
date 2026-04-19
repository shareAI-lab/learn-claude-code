from __future__ import annotations

from pathlib import Path

from coding_deepgent.frontend.client import FrontendClient
from coding_deepgent.settings import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        workdir=tmp_path / "workdir",
        session_dir=tmp_path / "sessions",
        model_name="gpt-test",
    )


def test_frontend_client_stream_prompt_yields_fake_events(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()
    client = FrontendClient(settings=settings, fake=True)

    events = list(client.stream_prompt("hello"))

    assert [event.type for event in events] == [
        "session_started",
        "user_message",
        "tool_started",
        "assistant_delta",
        "assistant_delta",
        "tool_finished",
        "runtime_event",
        "todo_snapshot",
        "assistant_message",
        "recovery_brief",
        "run_finished",
    ]


def test_frontend_client_chat_returns_final_assistant_text(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.workdir.mkdir()
    client = FrontendClient(settings=settings, fake=True)

    result = client.chat("hello")

    assert result == "Fake response: hello"
