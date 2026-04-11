from __future__ import annotations

import pytest

from coding_deepgent.state import default_session_state, normalize_plan_items


def test_default_session_state_matches_planning_contract() -> None:
    assert default_session_state() == {
        "items": [],
        "rounds_since_update": 0,
    }


def test_normalize_plan_items_rejects_multiple_in_progress_steps() -> None:
    with pytest.raises(ValueError, match="Only one plan item can be in_progress"):
        normalize_plan_items(
            [
                {"content": "Inspect repo", "status": "in_progress"},
                {"content": "Implement change", "status": "in_progress"},
            ]
        )


def test_normalize_plan_items_rejects_empty_content() -> None:
    with pytest.raises(ValueError, match="content required"):
        normalize_plan_items([{"content": "   ", "status": "pending"}])
