from __future__ import annotations

import pytest

from coding_deepgent.state import default_session_state, normalize_todos


def test_default_session_state_matches_todowrite_contract() -> None:
    assert default_session_state() == {
        "todos": [],
        "rounds_since_update": 0,
    }


def test_normalize_todos_rejects_multiple_in_progress_todos() -> None:
    with pytest.raises(ValueError, match="Only one todo item can be in_progress"):
        normalize_todos(
            [
                {"content": "Inspect repo", "status": "in_progress", "activeForm": "Inspecting"},
                {"content": "Implement change", "status": "in_progress", "activeForm": "Implementing"},
            ]
        )


def test_normalize_todos_rejects_empty_content() -> None:
    with pytest.raises(ValueError, match="value required"):
        normalize_todos([{"content": "   ", "status": "pending", "activeForm": "Waiting"}])
