from __future__ import annotations

from coding_deepgent.agent_runtime_service import session_payload, update_session_state


def test_session_payload_preserves_session_memory_artifact() -> None:
    payload = session_payload(
        {
            "todos": [],
            "rounds_since_update": 0,
            "session_memory": {
                "content": "Keep repo focus.",
                "source": "manual",
                "message_count": 1,
                "updated_at": "2026-04-15T00:00:00Z",
            },
        }
    )

    assert payload["session_memory"] == {
        "content": "Keep repo focus.",
        "source": "manual",
        "message_count": 1,
        "updated_at": "2026-04-15T00:00:00Z",
    }


def test_update_session_state_preserves_session_memory_artifact() -> None:
    state = {"todos": [], "rounds_since_update": 0}

    update_session_state(
        state,
        {
            "todos": [],
            "rounds_since_update": 1,
            "session_memory": {
                "content": "Keep repo focus.",
                "source": "live_compact",
                "message_count": 2,
                "updated_at": "2026-04-15T00:00:00Z",
            },
        },
    )

    assert state["session_memory"] == {
        "content": "Keep repo focus.",
        "source": "live_compact",
        "message_count": 2,
        "updated_at": "2026-04-15T00:00:00Z",
    }
