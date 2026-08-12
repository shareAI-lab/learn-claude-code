import json
import re
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path


TASK_ID_PATTERN = re.compile(r"^task_[A-Za-z0-9_-]+$")


def register_task_tools(registry, schemas: dict, handlers: dict) -> None:
    """Register task-board tools using the supplied task-store handlers."""
    for name in (
        "create_task", "list_tasks", "get_task", "claim_task", "complete_task",
    ):
        registry.register(schemas[name], handlers.get(name))


@dataclass
class Task:
    id: str
    subject: str
    description: str
    status: str
    owner: str | None
    blockedBy: list[str]
    worktree: str | None = None


@dataclass(slots=True)
class TaskStore:
    root: Path
    lock: threading.Lock = field(default_factory=threading.Lock)


def task_path(store: TaskStore, task_id: str) -> Path:
    if not isinstance(task_id, str) or not TASK_ID_PATTERN.fullmatch(task_id):
        raise ValueError(f"Invalid task id: {task_id!r}")
    root = store.root.resolve()
    path = (root / f"{task_id}.json").resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Task path escapes task directory: {task_id!r}")
    return path


def _save_task_unlocked(store: TaskStore, task: Task) -> None:
    path = task_path(store, task.id)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp_path.write_text(
            json.dumps(asdict(task), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def create_task(
    store: TaskStore,
    subject: str,
    description: str = "",
    blockedBy: list[str] | None = None,
) -> Task:
    with store.lock:
        store.root.mkdir(parents=True, exist_ok=True)
        while True:
            task_id = f"task_{uuid.uuid4().hex}"
            if not task_path(store, task_id).exists():
                break
        task = Task(
            id=task_id,
            subject=subject,
            description=description,
            status="pending",
            owner=None,
            blockedBy=blockedBy or [],
        )
        _save_task_unlocked(store, task)
        return task


def save_task(store: TaskStore, task: Task):
    with store.lock:
        store.root.mkdir(parents=True, exist_ok=True)
        _save_task_unlocked(store, task)


def load_task(store: TaskStore, task_id: str) -> Task:
    data = json.loads(task_path(store, task_id).read_text(encoding="utf-8"))
    return Task(**data)


def list_tasks(store: TaskStore) -> list[Task]:
    tasks = []
    if not store.root.exists():
        return tasks
    for path in sorted(store.root.glob("task_*.json")):
        try:
            tasks.append(Task(**json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError, TypeError) as error:
            print(f"[task warning] ignored {path.name}: {error}")
    return tasks


def get_task(store: TaskStore, task_id: str) -> str:
    return json.dumps(asdict(load_task(store, task_id)), indent=2, ensure_ascii=False)


def can_start(store: TaskStore, task_id: str) -> bool:
    task = load_task(store, task_id)
    for dependency_id in task.blockedBy:
        if not task_path(store, dependency_id).exists():
            return False
        if load_task(store, dependency_id).status != "completed":
            return False
    return True


def claim_task(store: TaskStore, task_id: str, owner: str = "agent") -> str:
    with store.lock:
        task = load_task(store, task_id)
        if task.status != "pending":
            return f"Task {task_id} is {task.status}, cannot claim"
        if task.owner:
            return f"Task {task_id} already owned by {task.owner}"
        if not can_start(store, task_id):
            dependencies = [
                dependency_id
                for dependency_id in task.blockedBy
                if (
                    not task_path(store, dependency_id).exists()
                    or load_task(store, dependency_id).status != "completed"
                )
            ]
            return f"Blocked by: {dependencies}"
        task.owner = owner
        task.status = "in_progress"
        _save_task_unlocked(store, task)
    print(f"  \033[36m[claim] {task.subject} → in_progress (owner: {owner})\033[0m")
    return f"Claimed {task.id} ({task.subject})"


def complete_task(store: TaskStore, task_id: str) -> str:
    with store.lock:
        task = load_task(store, task_id)
        if task.status != "in_progress":
            return f"Task {task_id} is {task.status}, cannot complete"
        task.status = "completed"
        _save_task_unlocked(store, task)
    unblocked = [
        candidate.subject
        for candidate in list_tasks(store)
        if candidate.status == "pending" and candidate.blockedBy and can_start(store, candidate.id)
    ]
    print(f"  \033[32m[complete] {task.subject} ✓\033[0m")
    message = f"Completed {task.id} ({task.subject})"
    if unblocked:
        message += f"\nUnblocked: {', '.join(unblocked)}"
        print(f"  \033[33m[unblocked] {', '.join(unblocked)}\033[0m")
    return message
