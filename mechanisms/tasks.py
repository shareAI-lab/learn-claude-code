"""
mechanisms/tasks.py — Task System mechanism, sourced from s12 (the origin lesson).

First-appearance rule: the lesson that INTRODUCES a concept shows it inline;
later lessons import the abstraction. So s12 inlines its own Task System (6
fields, simple claim_task); s13-s16 import this module verbatim; s17 imports
the base but overrides ``claim_task`` locally (s17 teaches the owner-check +
missing-deps enhancement); s18-s20 import the base ``Task`` (which carries an
optional ``worktree`` slot, unused by s12-s17) and also override ``claim_task``
with the same enhancement s17 introduced.

Design — module-level functions + an ``init_tasks(workdir)`` call that binds
``TASKS_DIR`` (mirroring how each lesson already treats ``WORKDIR`` as a
module-level global set at startup). Functions late-bind ``TASKS_DIR`` at
call time, so the import order is: ``from mechanisms.tasks import ...`` then
``init_tasks(WORKDIR)``.

The ``worktree`` field on ``Task`` is an optional forward-compatible slot:
s12-s17 never set it (it stays ``None``); s18-s20 set it via
``bind_task_to_worktree``. It is NOT taught in s12 — s12's inline ``Task``
omits this field. It lives here so that ``load_task`` / ``list_tasks`` round-trip
worktree-bearing JSON without each lesson re-implementing the dataclass.
"""

import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path

TASKS_DIR: Path | None = None  # bound by init_tasks()


def init_tasks(workdir: Path) -> Path:
    """Bind ``TASKS_DIR`` to *workdir* / .tasks (idempotent). Call once at startup."""
    global TASKS_DIR
    TASKS_DIR = workdir / ".tasks"
    TASKS_DIR.mkdir(exist_ok=True)
    return TASKS_DIR


def task_path(task_id: str) -> Path:
    return TASKS_DIR / f"{task_id}.json"


@dataclass
class Task:
    id: str
    subject: str
    description: str
    status: str          # pending | in_progress | completed
    owner: str | None    # Agent name (multi-agent scenarios)
    blockedBy: list[str] # Dependency task IDs
    # Optional forward-compatible slot. s12-s17 leave this None; s18-s20 set it
    # via bind_task_to_worktree. NOT taught in s12 (s12's inline Task omits it);
    # included here so load_task/list_tasks round-trip worktree-bearing JSON.
    worktree: str | None = None


def create_task(subject: str, description: str = "",
                blockedBy: list[str] | None = None) -> Task:
    task = Task(
        id=f"task_{int(time.time())}_{random.randint(0, 9999):04d}",
        subject=subject,
        description=description,
        status="pending",
        owner=None,
        blockedBy=blockedBy or [],
    )
    save_task(task)
    return task


def save_task(task: Task):
    task_path(task.id).write_text(json.dumps(asdict(task), indent=2))


def load_task(task_id: str) -> Task:
    return Task(**json.loads(task_path(task_id).read_text()))


def list_tasks() -> list[Task]:
    return [Task(**json.loads(p.read_text()))
            for p in sorted(TASKS_DIR.glob("task_*.json"))]


def get_task(task_id: str) -> str:
    """Return full task details as a JSON string."""
    task = load_task(task_id)
    return json.dumps(asdict(task), indent=2)


# Alias used by s18-s20's tool schemas (they name the tool get_task_json).
# Function body identical to get_task; kept as a separate name for clarity.
def get_task_json(task_id: str) -> str:
    return get_task(task_id)


def can_start(task_id: str) -> bool:
    """Check if all blockedBy dependencies are completed.

    Missing dependencies are treated as blocked.
    """
    task = load_task(task_id)
    for dep_id in task.blockedBy:
        if not task_path(dep_id).exists():
            return False
        if load_task(dep_id).status != "completed":
            return False
    return True


def claim_task(task_id: str, owner: str = "agent") -> str:
    task = load_task(task_id)
    if task.status != "pending":
        return f"Task {task_id} is {task.status}, cannot claim"
    if not can_start(task_id):
        deps = [d for d in task.blockedBy
                if not task_path(d).exists() or load_task(d).status != "completed"]
        return f"Blocked by: {deps}"
    task.owner = owner
    task.status = "in_progress"
    save_task(task)
    print(f"  \033[36m[claim] {task.subject} → in_progress (owner: {owner})\033[0m")
    return f"Claimed {task.id} ({task.subject})"


def complete_task(task_id: str) -> str:
    task = load_task(task_id)
    if task.status != "in_progress":
        return f"Task {task_id} is {task.status}, cannot complete"
    task.status = "completed"
    save_task(task)
    unblocked = [t.subject for t in list_tasks()
                 if t.status == "pending" and t.blockedBy and can_start(t.id)]
    print(f"  \033[32m[complete] {task.subject} ✓\033[0m")
    msg = f"Completed {task.id} ({task.subject})"
    if unblocked:
        msg += f"\nUnblocked: {', '.join(unblocked)}"
        print(f"  \033[33m[unblocked] {', '.join(unblocked)}\033[0m")
    return msg
