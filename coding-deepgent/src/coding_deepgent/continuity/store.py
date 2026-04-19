from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from coding_deepgent.event_stream import append_event

CONTINUITY_NAMESPACE = ("coding_deepgent_continuity",)
ContinuityStatus = Literal["current", "stale"]


class ContinuityStore(Protocol):
    def put(
        self, namespace: tuple[str, ...], key: str, value: dict[str, object]
    ) -> None: ...
    def get(self, namespace: tuple[str, ...], key: str) -> object | None: ...
    def search(self, namespace: tuple[str, ...]) -> Iterable[object]: ...


class ContinuityArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    session_id: str | None = None
    source: str = Field(default="manual", min_length=1)
    status: ContinuityStatus = "current"
    created_at: str
    updated_at: str


def save_artifact(
    store: ContinuityStore,
    *,
    title: str,
    content: str,
    session_id: str | None = None,
    source: str = "manual",
) -> ContinuityArtifact:
    now = _now()
    artifact = ContinuityArtifact(
        artifact_id=_artifact_id(title=title, created_at=now),
        title=title.strip(),
        content=content.strip(),
        session_id=session_id,
        source=source.strip(),
        created_at=now,
        updated_at=now,
    )
    store.put(CONTINUITY_NAMESPACE, artifact.artifact_id, artifact.model_dump())
    append_event(
        store,
        stream_id="continuity",
        kind="continuity_saved",
        payload={"artifact_id": artifact.artifact_id, "title": artifact.title},
    )
    return artifact


def get_artifact(store: ContinuityStore, artifact_id: str) -> ContinuityArtifact:
    item = store.get(CONTINUITY_NAMESPACE, artifact_id)
    if item is None:
        raise KeyError(f"Unknown continuity artifact: {artifact_id}")
    return ContinuityArtifact.model_validate(_item_value(item))


def list_artifacts(
    store: ContinuityStore,
    *,
    include_stale: bool = False,
) -> list[ContinuityArtifact]:
    records = [
        ContinuityArtifact.model_validate(_item_value(item))
        for item in store.search(CONTINUITY_NAMESPACE)
    ]
    if not include_stale:
        records = [record for record in records if record.status == "current"]
    return sorted(records, key=lambda record: record.artifact_id)


def mark_stale(store: ContinuityStore, artifact_id: str) -> ContinuityArtifact:
    artifact = get_artifact(store, artifact_id)
    updated = artifact.model_copy(update={"status": "stale", "updated_at": _now()})
    store.put(CONTINUITY_NAMESPACE, updated.artifact_id, updated.model_dump())
    append_event(
        store,
        stream_id="continuity",
        kind="continuity_stale",
        payload={"artifact_id": updated.artifact_id},
    )
    return updated


def _item_value(item: object) -> dict[str, object]:
    value = getattr(item, "value", item)
    return value if isinstance(value, dict) else {}


def _artifact_id(*, title: str, created_at: str) -> str:
    digest = sha256(f"{title}\0{created_at}".encode("utf-8")).hexdigest()
    return f"cont-{digest[:12]}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
