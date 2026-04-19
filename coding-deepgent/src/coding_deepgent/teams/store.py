from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from coding_deepgent.event_stream import append_event

TEAM_NAMESPACE = ("coding_deepgent_teams",)
TeamStatus = Literal["planning", "running", "completed", "cancelled"]


class TeamStore(Protocol):
    def put(
        self, namespace: tuple[str, ...], key: str, value: dict[str, object]
    ) -> None: ...
    def get(self, namespace: tuple[str, ...], key: str) -> object | None: ...
    def search(self, namespace: tuple[str, ...]) -> Iterable[object]: ...


class TeamRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: str
    title: str = Field(..., min_length=1)
    coordinator: str = Field(default="coordinator", min_length=1)
    status: TeamStatus = "planning"
    worker_ids: list[str] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    progress: list[str] = Field(default_factory=list)
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


def create_team(
    store: TeamStore,
    *,
    title: str,
    coordinator: str = "coordinator",
    task_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> TeamRun:
    now = _now()
    team = TeamRun(
        team_id=_team_id(title=title, created_at=now),
        title=title.strip(),
        coordinator=coordinator.strip(),
        task_ids=task_ids or [],
        metadata=metadata or {},
        created_at=now,
        updated_at=now,
    )
    return _save(store, team, event_kind="team_created")


def get_team(store: TeamStore, team_id: str) -> TeamRun:
    item = store.get(TEAM_NAMESPACE, team_id)
    if item is None:
        raise KeyError(f"Unknown team: {team_id}")
    return TeamRun.model_validate(_item_value(item))


def list_teams(store: TeamStore) -> list[TeamRun]:
    return sorted(
        [TeamRun.model_validate(_item_value(item)) for item in store.search(TEAM_NAMESPACE)],
        key=lambda team: team.team_id,
    )


def assign_worker(store: TeamStore, *, team_id: str, worker_id: str) -> TeamRun:
    team = get_team(store, team_id)
    workers = team.worker_ids if worker_id in team.worker_ids else [*team.worker_ids, worker_id]
    return _save(
        store,
        team.model_copy(
            update={"worker_ids": workers, "status": "running", "updated_at": _now()}
        ),
        event_kind="team_worker_assigned",
    )


def update_progress(store: TeamStore, *, team_id: str, message: str) -> TeamRun:
    team = get_team(store, team_id)
    return _save(
        store,
        team.model_copy(
            update={"progress": [*team.progress, message.strip()], "updated_at": _now()}
        ),
        event_kind="team_progress",
    )


def complete_team(
    store: TeamStore,
    *,
    team_id: str,
    summary: str,
    status: TeamStatus = "completed",
) -> TeamRun:
    if status not in {"completed", "cancelled"}:
        raise ValueError("team completion status must be completed or cancelled")
    team = get_team(store, team_id)
    return _save(
        store,
        team.model_copy(
            update={"status": status, "summary": summary.strip(), "updated_at": _now()}
        ),
        event_kind=f"team_{status}",
    )


def _save(store: TeamStore, team: TeamRun, *, event_kind: str) -> TeamRun:
    store.put(TEAM_NAMESPACE, team.team_id, team.model_dump())
    append_event(
        store,
        stream_id=f"team:{team.team_id}",
        kind=event_kind,
        payload={"team_id": team.team_id, "status": team.status},
    )
    return team


def _item_value(item: object) -> dict[str, object]:
    value = getattr(item, "value", item)
    return value if isinstance(value, dict) else {}


def _team_id(*, title: str, created_at: str) -> str:
    digest = sha256(f"{title}\0{created_at}".encode("utf-8")).hexdigest()
    return f"team-{digest[:12]}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
