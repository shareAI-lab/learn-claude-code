from __future__ import annotations


def thread_id_for_session(session_id: str) -> str:
    return session_id


def thread_config_for_session(session_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id_for_session(session_id)}}
