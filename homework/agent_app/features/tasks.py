import json
import re
import threading
import uuid
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path


TASK_ID_PATTERN = re.compile(r"^task_[A-Za-z0-9_-]+$")


TASK_TOOL_SCHEMAS = [
    {"name": "create_task", "description": "Create a new task with optinal blockedBy dependencies.",
     "input_schema": {"type": "object", "properties": {"subject": {"type": "string"}, "description": {"type": "string"}, "blockedBy": {"type": "array", "items": {"type": "string"}}}, "required": ["subject"]}},
    {"name": "list_tasks",
     "description": "List all tasks with status, owner, and denpendencies.",
     "input_schema": {"type": "object", "properties": {},
                      "required": []}},
    {"name": "get_task",
     "description": "Get full details of a specific task by ID.",
     "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}},
                      "required": ["task_id"]}},
    {"name": "claim_task",
     "description": "Claim a pending task. Sets owner, changes status to in_progress.",
     "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}},
                      "required": ["task_id"]}},
    {"name": "complete_task",
     "description": "Complete an in-progress task. Reports unblocked downstream tasks.",
     "input_schema": {"type": "object",
                      "properties": {"task_id": {"type": "string"}},
                      "required": ["task_id"]}},
]


def register_task_tools(registry, task_store) -> None:
    """Register task-board tools using the supplied task-store handlers."""
    if isinstance(task_store, Mapping):
        handlers = task_store
    else:
        def current_store():
            return task_store() if callable(task_store) else task_store

        handlers = {
            "create_task": lambda **kwargs: _run_create_task_tool(
                current_store(), **kwargs
            ),
            "list_tasks": lambda: _run_list_tasks_tool(current_store()),
            "get_task": lambda task_id: _run_task_operation(
                current_store(), "read", task_id, get_task
            ),
            "claim_task": lambda task_id: _run_task_operation(
                current_store(), "claim", task_id, claim_task
            ),
            "complete_task": lambda task_id: _run_task_operation(
                current_store(), "complete", task_id, complete_task
            ),
        }
    for schema in TASK_TOOL_SCHEMAS:
        registry.register(schema, handlers[schema["name"]])


def _run_create_task_tool(
    store, subject: str, description: str = "", blockedBy: list[str] | None = None
) -> str:
    task = create_task(store, subject, description, blockedBy)
    dependencies = f" (blocked by: {', '.join(blockedBy)})" if blockedBy else ""
    print(f"  \033[34m[create] {task.subject}{dependencies}\033[0m")
    return f"Created {task.id}: {task.subject}{dependencies}"


def _run_list_tasks_tool(store) -> str:
    stored_tasks = list_tasks(store)
    if not stored_tasks:
        return "No tasks. Use create_task to add some."
    lines = []
    for task in stored_tasks:
        icon = {"pending": "○", "in_progress": "●", "completed": "✓"}.get(
            task.status, "?"
        )
        dependencies = f" (blocked by: {', '.join(task.blockedBy)})"
        owner = f"[{task.owner}]" if task.owner else ""
        lines.append(
            f"  {icon} {task.id}: {task.subject} "
            f"[{task.status}]{owner}{dependencies}"
        )
    return "\n".join(lines)


def _run_task_operation(store, operation: str, task_id: str, callback) -> str:
    try:
        return callback(store, task_id)
    except (OSError, ValueError, TypeError) as exc:
        return f"Error: cannot {operation} task {task_id}: {exc}"


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
