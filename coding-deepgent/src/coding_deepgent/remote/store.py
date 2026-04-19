from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from coding_deepgent.event_stream import EventRecord, append_event, list_events

REMOTE_NAMESPACE = ("coding_deepgent_remote_sessions",)
RemoteStatus = Literal["active", "closed"]


class RemoteStore(Protocol):
    def put(
        self, namespace: tuple[str, ...], key: str, value: dict[str, object]
    ) -> None: ...
    def get(self, namespace: tuple[str, ...], key: str) -> object | None: ...
    def search(self, namespace: tuple[str, ...]) -> Iterable[object]: ...


class RemoteSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remote_id: str
    session_id: str = Field(..., min_length=1)
    client_name: str = Field(..., min_length=1)
    status: RemoteStatus = "active"
    last_sequence_sent: int = 0
    created_at: str
    updated_at: str


def register_remote_session(
    store: RemoteStore,
    *,
    session_id: str,
    client_name: str,
) -> RemoteSession:
    now = _now()
    remote = RemoteSession(
        remote_id=_remote_id(session_id=session_id, client_name=client_name, created_at=now),
        session_id=session_id.strip(),
        client_name=client_name.strip(),
        created_at=now,
        updated_at=now,
    )
    store.put(REMOTE_NAMESPACE, remote.remote_id, remote.model_dump())
    append_event(
        store,
        stream_id=f"remote:{remote.remote_id}",
        kind="remote_registered",
        payload=remote.model_dump(),
    )
    return remote


def get_remote_session(store: RemoteStore, remote_id: str) -> RemoteSession:
    item = store.get(REMOTE_NAMESPACE, remote_id)
    if item is None:
        raise KeyError(f"Unknown remote session: {remote_id}")
    return RemoteSession.model_validate(_item_value(item))


def list_remote_sessions(store: RemoteStore) -> list[RemoteSession]:
    return sorted(
        [
            RemoteSession.model_validate(_item_value(item))
            for item in store.search(REMOTE_NAMESPACE)
        ],
        key=lambda item: item.remote_id,
    )


def send_remote_control(
    store: RemoteStore,
    *,
    remote_id: str,
    command: str,
    payload: dict[str, Any] | None = None,
) -> EventRecord:
    remote = get_remote_session(store, remote_id)
    if remote.status != "active":
        raise ValueError("remote session is closed")
    return append_event(
        store,
        stream_id=f"remote:{remote.remote_id}",
        kind=f"control:{command.strip()}",
        payload=payload or {},
    )


def replay_remote_events(
    store: RemoteStore,
    *,
    remote_id: str,
    after_sequence: int | None = None,
) -> list[EventRecord]:
    remote = get_remote_session(store, remote_id)
    return list_events(
        store,
        stream_id=f"remote:{remote.remote_id}",
        after_sequence=after_sequence,
        include_internal=False,
    )


def close_remote_session(store: RemoteStore, remote_id: str) -> RemoteSession:
    remote = get_remote_session(store, remote_id)
    updated = remote.model_copy(update={"status": "closed", "updated_at": _now()})
    store.put(REMOTE_NAMESPACE, updated.remote_id, updated.model_dump())
    append_event(
        store,
        stream_id=f"remote:{updated.remote_id}",
        kind="remote_closed",
        payload={"remote_id": updated.remote_id},
    )
    return updated


def _item_value(item: object) -> dict[str, object]:
    value = getattr(item, "value", item)
    return value if isinstance(value, dict) else {}


def _remote_id(*, session_id: str, client_name: str, created_at: str) -> str:
    digest = sha256(f"{session_id}\0{client_name}\0{created_at}".encode("utf-8")).hexdigest()
    return f"remote-{digest[:12]}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
