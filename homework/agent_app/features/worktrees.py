import json
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from homework.agent_app.features.tasks import TaskStore, _save_task_unlocked, load_task


VALID_WT_NAME = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def register_worktree_tools(registry, schemas: dict, handlers: dict) -> None:
    """Register worktree lifecycle tools."""
    for name in ("create_worktree", "remove_worktree", "keep_worktree"):
        registry.register(schemas[name], handlers.get(name))


@dataclass(slots=True)
class WorktreeState:
    workdir: Path
    root: Path
    run_git: Callable[[list[str]], tuple[bool, str]]
    lock: threading.Lock = field(default_factory=threading.Lock)


def validate_worktree_name(name: str) -> str | None:
    if not name:
        return "Worktree name cannot be empty"
    if name == "." or name == "..":
        return f"'{name}' is not a valid worktree name"
    if not VALID_WT_NAME.fullmatch(name):
        return (
            f"Invalid worktree name: '{name}': "
            "only letters, digits, dots, underscores, dashes (1-64 chars)"
        )
    return None


def log_event(state: WorktreeState, event_type: str, name: str, task_id: str = ""):
    state.root.mkdir(parents=True, exist_ok=True)
    event = {"type": event_type, "worktree": name, "task_id": task_id, "ts": time.time()}
    with (state.root / "events.jsonl").open("a") as events_file:
        events_file.write(json.dumps(event) + "\n")


def bind_task_to_worktree(store: TaskStore, task_id: str, worktree_name: str):
    with store.lock:
        task = load_task(store, task_id)
        task.worktree = worktree_name
        _save_task_unlocked(store, task)
    print(f"  \033[33m[bind] {task.subject} → worktree:{worktree_name}\033[0m")


def create_worktree(
    state: WorktreeState,
    name: str,
    task_id: str = "",
    task_store: TaskStore | None = None,
) -> str:
    error = validate_worktree_name(name)
    if error:
        return f"Error: {error}"
    with state.lock:
        state.root.mkdir(parents=True, exist_ok=True)
        path = state.root / name
        if path.exists():
            return f"Worktree '{name}' already exists at {path}"
        ok, result = state.run_git(["worktree", "add", str(path), "-b", f"wt/{name}", "HEAD"])
        if not ok:
            return f"Git error: {result}"
        if task_id and task_store:
            bind_task_to_worktree(task_store, task_id, name)
        log_event(state, "create", name, task_id)
    print(f"  \033[33m[worktree] created: {name} at {path}\033[0m")
    return f"Worktree '{name}' created at {path}"


def _count_worktree_changes(state: WorktreeState, path: Path) -> tuple[int, int]:
    ok_status, status = state.run_git(["-C", str(path), "status", "--porcelain"])
    ok_log, log = state.run_git(["-C", str(path), "log", "@{push}..HEAD", "--oneline"])
    if not ok_status or not ok_log:
        return -1, -1
    return (
        len([line for line in status.splitlines() if line.strip()]),
        len([line for line in log.splitlines() if line.strip()]),
    )


def remove_worktree(state: WorktreeState, name: str, discard_changes: bool = False) -> str:
    error = validate_worktree_name(name)
    if error:
        return error
    with state.lock:
        path = state.root / name
        if not path.exists():
            return f"Worktree '{name}' not found"
        if not discard_changes:
            files, commits = _count_worktree_changes(state, path)
            if files < 0:
                return f"Cannot verify worktree '{name}' status. Use discard_changes=true to force removal."
            if files > 0 or commits > 0:
                return (
                    f"Worktree '{name}' has {files} uncommitted file(s) and {commits} unpushed commit(s). "
                    "Use discard_changes=true to force removal, or keep_worktree to preserve for review."
                )
        ok, _ = state.run_git(["worktree", "remove", str(path), "--force"])
        if not ok:
            return f"Failed to remove worktree directory for '{name}'"
        state.run_git(["branch", "-D", f"wt/{name}"])
        log_event(state, "remove", name)
    print(f"  \033[33m[worktree] removed: {name}\033[0m")
    return f"Worktree '{name}' removed"


def keep_worktree(state: WorktreeState, name: str) -> str:
    error = validate_worktree_name(name)
    if error:
        return error
    with state.lock:
        log_event(state, "keep", name)
    print(f"  \033[36m[worktree] kept: {name}\033[0m")
    return f"Worktree '{name}' kept for review (branch: wt/{name})"
