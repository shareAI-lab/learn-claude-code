from __future__ import annotations

from hashlib import sha256
from typing import Iterable, Protocol

from coding_deepgent.tasks.schemas import (
    ALLOWED_TRANSITIONS,
    TERMINAL_TASK_STATUSES,
    TaskRecord,
    TaskStatus,
)

TASK_ROOT_NAMESPACE = "coding_deepgent_tasks"


class TaskStore(Protocol):
    def put(
        self, namespace: tuple[str, ...], key: str, value: dict[str, object]
    ) -> None: ...
    def get(self, namespace: tuple[str, ...], key: str) -> object | None: ...
    def search(self, namespace: tuple[str, ...]) -> Iterable[object]: ...


def task_namespace() -> tuple[str, ...]:
    return (TASK_ROOT_NAMESPACE,)


def task_id_for(title: str, existing_count: int = 0) -> str:
    digest = sha256(f"{title}\0{existing_count}".encode("utf-8")).hexdigest()
    return f"task-{digest[:10]}"


def _item_value(item: object) -> dict[str, object]:
    value = getattr(item, "value", item)
    return value if isinstance(value, dict) else {}


def list_tasks(store: TaskStore, *, include_terminal: bool = False) -> list[TaskRecord]:
    records = [
        TaskRecord.model_validate(_item_value(item))
        for item in store.search(task_namespace())
    ]
    if not include_terminal:
        records = [
            record for record in records if record.status not in TERMINAL_TASK_STATUSES
        ]
    return sorted(records, key=lambda record: record.id)


def get_task(store: TaskStore, task_id: str) -> TaskRecord:
    item = store.get(task_namespace(), task_id)
    if item is None:
        raise KeyError(f"Unknown task: {task_id}")
    return TaskRecord.model_validate(_item_value(item))


def save_task(store: TaskStore, record: TaskRecord) -> TaskRecord:
    store.put(task_namespace(), record.id, record.model_dump())
    return record


def create_task(
    store: TaskStore,
    *,
    title: str,
    description: str = "",
    depends_on: list[str] | None = None,
    owner: str | None = None,
    metadata: dict[str, str] | None = None,
) -> TaskRecord:
    existing_count = len(list_tasks(store, include_terminal=True))
    record = TaskRecord(
        id=task_id_for(title, existing_count),
        title=title,
        description=description,
        depends_on=depends_on or [],
        owner=owner,
        metadata=metadata or {},
    )
    return save_task(store, record)


def update_task(
    store: TaskStore,
    *,
    task_id: str,
    status: TaskStatus | None = None,
    owner: str | None = None,
    metadata: dict[str, str] | None = None,
) -> TaskRecord:
    record = get_task(store, task_id)
    updates: dict[str, object] = {}
    if status is not None:
        if status not in ALLOWED_TRANSITIONS[record.status]:
            raise ValueError(f"Invalid task transition: {record.status} -> {status}")
        updates["status"] = status
    if owner is not None:
        updates["owner"] = owner
    if metadata is not None:
        updates["metadata"] = {**record.metadata, **metadata}
    return save_task(store, record.model_copy(update=updates))


def is_task_ready(store: TaskStore, record: TaskRecord) -> bool:
    if record.status != "pending":
        return False
    return all(
        get_task(store, dependency).status == "completed"
        for dependency in record.depends_on
    )
