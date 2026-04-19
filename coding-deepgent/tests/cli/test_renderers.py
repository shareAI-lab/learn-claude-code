from __future__ import annotations

from coding_deepgent.renderers.text import (
    render_config_table,
    render_doctor_table,
    render_session_table,
)


def test_render_config_table_contains_key_value_rows() -> None:
    output = render_config_table(
        [
            ("workdir", "/tmp/work"),
            ("openai_api_key", "<set>"),
        ]
    )

    assert "Configuration" in output
    assert "workdir" in output
    assert "/tmp/work" in output
    assert "openai_api_key" in output
    assert "<set>" in output


def test_render_session_table_handles_empty_and_rows() -> None:
    assert render_session_table([]) == "No sessions recorded yet."

    output = render_session_table(
        [
            {
                "session_id": "session-1",
                "updated_at": "2026-04-13T00:00:00Z",
                "message_count": 3,
                "workdir": "/tmp/work",
            }
        ]
    )

    assert "Sessions" in output
    assert "session-1" in output
    assert "2026-04-13T00:00:00Z" in output
    assert "/tmp/work" in output


def test_render_doctor_table_lists_check_statuses() -> None:
    output = render_doctor_table(
        [
            {"name": "typer", "status": "installed", "detail": "CLI command surface."},
            {
                "name": "openai_api_key",
                "status": "<set>",
                "detail": "Required for live calls.",
            },
        ]
    )

    assert "Doctor" in output
    assert "typer" in output
    assert "installed" in output
    assert "openai_api_key" in output
    assert "<set>" in output
