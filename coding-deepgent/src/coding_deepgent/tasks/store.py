from __future__ import annotations

from hashlib import sha256
from typing import Iterable, Protocol

from coding_deepgent.tasks.schemas import (
    ALLOWED_TRANSITIONS,
    PlanArtifact,
    TERMINAL_TASK_STATUSES,
    TaskRecord,
    TaskStatus,
)

TASK_ROOT_NAMESPACE = "coding_deepgent_tasks"
PLAN_ROOT_NAMESPACE = "coding_deepgent_plans"


class TaskStore(Protocol):
    def put(
        self, namespace: tuple[str, ...], key: str, value: dict[str, object]
    ) -> None: ...
    def get(self, namespace: tuple[str, ...], key: str) -> object | None: ...
    def search(self, namespace: tuple[str, ...]) -> Iterable[object]: ...


def task_namespace() -> tuple[str, ...]:
    return (TASK_ROOT_NAMESPACE,)


def plan_namespace() -> tuple[str, ...]:
    return (PLAN_ROOT_NAMESPACE,)


def task_id_for(title: str, existing_count: int = 0) -> str:
    digest = sha256(f"{title}\0{existing_count}".encode("utf-8")).hexdigest()
    return f"task-{digest[:10]}"


def plan_id_for(title: str, existing_count: int = 0) -> str:
    digest = sha256(f"plan\0{title}\0{existing_count}".encode("utf-8")).hexdigest()
    return f"plan-{digest[:10]}"


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


def save_plan(store: TaskStore, record: PlanArtifact) -> PlanArtifact:
    store.put(plan_namespace(), record.id, record.model_dump())
    return record


def get_plan(store: TaskStore, plan_id: str) -> PlanArtifact:
    item = store.get(plan_namespace(), plan_id)
    if item is None:
        raise KeyError(f"Unknown plan: {plan_id}")
    return PlanArtifact.model_validate(_item_value(item))


def create_plan(
    store: TaskStore,
    *,
    title: str,
    content: str,
    verification: str,
    task_ids: list[str] | None = None,
    metadata: dict[str, str] | None = None,
) -> PlanArtifact:
    active_task_ids = task_ids or []
    _validate_dependencies_exist(store, active_task_ids)
    existing_count = sum(1 for _ in store.search(plan_namespace()))
    return save_plan(
        store,
        PlanArtifact(
            id=plan_id_for(title, existing_count),
            title=title,
            content=content,
            verification=verification,
            task_ids=active_task_ids,
            metadata=metadata or {},
        ),
    )


def create_task(
    store: TaskStore,
    *,
    title: str,
    description: str = "",
    depends_on: list[str] | None = None,
    owner: str | None = None,
    metadata: dict[str, str] | None = None,
) -> TaskRecord:
    active_depends_on = depends_on or []
    _validate_dependencies_exist(store, active_depends_on)
    existing_count = len(list_tasks(store, include_terminal=True))
    record = TaskRecord(
        id=task_id_for(title, existing_count),
        title=title,
        description=description,
        depends_on=active_depends_on,
        owner=owner,
        metadata=metadata or {},
    )
    return save_task(store, record)


def update_task(
    store: TaskStore,
    *,
    task_id: str,
    status: TaskStatus | None = None,
    depends_on: list[str] | None = None,
    owner: str | None = None,
    metadata: dict[str, str] | None = None,
) -> TaskRecord:
    record = get_task(store, task_id)
    updates: dict[str, object] = {}
    merged_metadata = record.metadata
    if metadata is not None:
        merged_metadata = {**record.metadata, **metadata}
    active_depends_on = depends_on if depends_on is not None else record.depends_on

    if status is not None:
        if status not in ALLOWED_TRANSITIONS[record.status]:
            raise ValueError(f"Invalid task transition: {record.status} -> {status}")
        if status == "blocked" and not active_depends_on and not merged_metadata.get(
            "blocked_reason"
        ):
            raise ValueError("blocked tasks require a dependency or blocked_reason")
        updates["status"] = status
    if depends_on is not None:
        _validate_task_dependencies(store, task_id=task_id, depends_on=depends_on)
        updates["depends_on"] = depends_on
    if owner is not None:
        updates["owner"] = owner
    if metadata is not None:
        updates["metadata"] = merged_metadata
    return save_task(store, record.model_copy(update=updates))


def is_task_ready(store: TaskStore, record: TaskRecord) -> bool:
    if record.status != "pending":
        return False
    return all(
        get_task(store, dependency).status == "completed"
        for dependency in record.depends_on
    )


def task_graph_needs_verification(store: TaskStore) -> bool:
    records = list_tasks(store, include_terminal=True)
    actionable = [
        record for record in records if record.status != "cancelled"
    ]
    if len(actionable) < 3:
        return False
    if any(record.status != "completed" for record in actionable):
        return False
    return not any(_is_verification_task(record) for record in actionable)


def validate_task_graph(store: TaskStore) -> None:
    records = list_tasks(store, include_terminal=True)
    ids = {record.id for record in records}
    for record in records:
        if record.id in record.depends_on:
            raise ValueError(f"Task {record.id} cannot depend on itself")
        missing = [task_id for task_id in record.depends_on if task_id not in ids]
        if missing:
            raise ValueError(f"Task {record.id} has unknown dependencies: {missing}")
    _detect_dependency_cycle(records)


def _validate_dependencies_exist(store: TaskStore, depends_on: list[str]) -> None:
    known = {record.id for record in list_tasks(store, include_terminal=True)}
    missing = [task_id for task_id in depends_on if task_id not in known]
    if missing:
        raise ValueError(f"Unknown task dependencies: {missing}")


def _validate_task_dependencies(
    store: TaskStore,
    *,
    task_id: str,
    depends_on: list[str],
) -> None:
    if task_id in depends_on:
        raise ValueError(f"Task {task_id} cannot depend on itself")
    _validate_dependencies_exist(store, depends_on)
    records = list_tasks(store, include_terminal=True)
    updated_records = [
        record.model_copy(update={"depends_on": depends_on})
        if record.id == task_id
        else record
        for record in records
    ]
    _detect_dependency_cycle(updated_records)


def _detect_dependency_cycle(records: list[TaskRecord]) -> None:
    graph = {record.id: set(record.depends_on) for record in records}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            raise ValueError(f"Task dependency cycle detected at {task_id}")
        visiting.add(task_id)
        for dependency in graph.get(task_id, set()):
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in graph:
        visit(task_id)


def _is_verification_task(record: TaskRecord) -> bool:
    text = " ".join(
        [
            record.title,
            record.description,
            record.metadata.get("type", ""),
            record.metadata.get("role", ""),
        ]
    ).casefold()
    return "verif" in text
