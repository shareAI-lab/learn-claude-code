#!/usr/bin/env python3
# Harness: directory isolation -- parallel execution lanes that never collide.
"""
s18_worktree_task_isolation.py - Worktree + Task Isolation

Directory-level isolation for parallel task execution.
Tasks are the control plane and worktrees are the execution plane.

    .tasks/task_12.json
      {
        "id": 12,
        "subject": "Implement auth refactor",
        "status": "in_progress",
        "worktree": "auth-refactor"
      }

    .worktrees/index.json
      {
        "worktrees": [
          {
            "name": "auth-refactor",
            "path": ".../.worktrees/auth-refactor",
            "branch": "wt/auth-refactor",
            "task_id": 12,
            "status": "active"
          }
        ]
      }

Key insight: "Isolate by directory, coordinate by task ID."

Read this file in this order:
1. EventBus: how worktree lifecycle stays observable.
2. TaskManager: how a task binds to an execution lane without becoming the lane itself.
3. Worktree registry / closeout helpers: how directory state is created, tracked, and cleaned up.

Most common confusion:
- a worktree is not the task itself
- a worktree record is not just a path string

Teaching boundary:
this file teaches isolated execution lanes first.
Cross-machine execution, merge automation, and enterprise policy glue are intentionally out of scope.
"""

import json
import os
import re
import subprocess
import time
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]


def detect_repo_root(cwd: Path) -> Path | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        root = Path(r.stdout.strip())
        return root if r.returncode == 0 and root.exists() else None
    except Exception:
        return None


REPO_ROOT = detect_repo_root(WORKDIR) or WORKDIR

SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Use task + worktree tools for multi-task work. "
    "For parallel or risky changes: create tasks, allocate worktree lanes, "
    "run commands in those lanes, then choose keep/remove for closeout."
)


# -- EventBus: append-only lifecycle events for observability --
class EventBus:
    def __init__(self, event_log_path: Path):
        self.path = event_log_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("")

    def emit(self, event: str, task_id=None, wt_name=None, error=None, **extra):
        payload = {"event": event, "ts": time.time()}
        if task_id is not None:
            payload["task_id"] = task_id
        if wt_name:
            payload["worktree"] = wt_name
        if error:
            payload["error"] = error
        payload.update(extra)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

    def list_recent(self, limit: int = 20) -> str:
        n = max(1, min(int(limit or 20), 200))
        lines = self.path.read_text(encoding="utf-8").splitlines()
        items = []
        for line in lines[-n:]:
            try:
                items.append(json.loads(line))
            except Exception:
                items.append({"event": "parse_error", "raw": line})
        return json.dumps(items, indent=2)


# -- TaskManager: persistent task board with optional worktree binding --
class TaskManager:
    def __init__(self, tasks_dir: Path):
        self.dir = tasks_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self._next_id = self._max_id() + 1

    def _max_id(self) -> int:
        ids = []
        for f in self.dir.glob("task_*.json"):
            try:
                ids.append(int(f.stem.split("_")[1]))
            except Exception:
                pass
        return max(ids) if ids else 0

    def _path(self, task_id: int) -> Path:
        return self.dir / f"task_{task_id}.json"

    def _load(self, task_id: int) -> dict:
        path = self._path(task_id)
        if not path.exists():
            raise ValueError(f"Task {task_id} not found")
        return json.loads(path.read_text())

    def _save(self, task: dict):
        self._path(task["id"]).write_text(json.dumps(task, indent=2))

    def create(self, subject: str, description: str = "") -> str:
        task = {
            "id": self._next_id, "subject": subject, "description": description,
            "status": "pending", "owner": "", "worktree": "",
            "worktree_state": "unbound", "last_worktree": "",
            "closeout": None, "blockedBy": [],
            "created_at": time.time(), "updated_at": time.time(),
        }
        self._save(task)
        self._next_id += 1
        return json.dumps(task, indent=2)

    def get(self, task_id: int) -> str:
        return json.dumps(self._load(task_id), indent=2)

    def exists(self, task_id: int) -> bool:
        return self._path(task_id).exists()

    def update(self, task_id: int, status: str = None, owner: str = None) -> str:
        task = self._load(task_id)
        if status:
            if status not in ("pending", "in_progress", "completed", "deleted"):
                raise ValueError(f"Invalid status: {status}")
            task["status"] = status
        if owner is not None:
            task["owner"] = owner
        task["updated_at"] = time.time()
        self._save(task)
        return json.dumps(task, indent=2)

    def bind_worktree(self, task_id: int, worktree: str, owner: str = "") -> str:
        task = self._load(task_id)
        task["worktree"] = worktree
        task["last_worktree"] = worktree
        task["worktree_state"] = "active"
        if owner:
            task["owner"] = owner
        if task["status"] == "pending":
            task["status"] = "in_progress"
        task["updated_at"] = time.time()
        self._save(task)
        return json.dumps(task, indent=2)

    def unbind_worktree(self, task_id: int) -> str:
        task = self._load(task_id)
        task["worktree"] = ""
        task["worktree_state"] = "unbound"
        task["updated_at"] = time.time()
        self._save(task)
        return json.dumps(task, indent=2)

    def record_closeout(self, task_id: int, action: str, reason: str = "", keep_binding: bool = False) -> str:
        task = self._load(task_id)
        task["closeout"] = {
            "action": action,
            "reason": reason,
            "at": time.time(),
        }
        task["worktree_state"] = action
        if not keep_binding:
            task["worktree"] = ""
        task["updated_at"] = time.time()
        self._save(task)
        return json.dumps(task, indent=2)

    def list_all(self) -> str:
        tasks = []
        for f in sorted(self.dir.glob("task_*.json")):
            tasks.append(json.loads(f.read_text()))
        if not tasks:
            return "No tasks."
        lines = []
        for t in tasks:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]", "deleted": "[-]"}.get(t["status"], "[?]")
            owner = f" owner={t['owner']}" if t.get("owner") else ""
            wt = f" wt={t['worktree']}" if t.get("worktree") else ""
            lines.append(f"{marker} #{t['id']}: {t['subject']}{owner}{wt}")
        return "\n".join(lines)


TASKS = TaskManager(REPO_ROOT / ".tasks")
EVENTS = EventBus(REPO_ROOT / ".worktrees" / "events.jsonl")


# -- WorktreeManager: create/list/run/remove git worktrees --
class WorktreeManager:
    def __init__(self, repo_root: Path, tasks: TaskManager, events: EventBus):
        self.repo_root = repo_root
        self.tasks = tasks
        self.events = events
        self.dir = repo_root / ".worktrees"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.dir / "index.json"
        if not self.index_path.exists():
            self.index_path.write_text(json.dumps({"worktrees": []}, indent=2))
        self.git_available = self._check_git()

    def _check_git(self) -> bool:
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_root, capture_output=True, text=True, timeout=10,
            )
            return r.returncode == 0
        except Exception:
            return False

    def _run_git(self, args: list[str]) -> str:
        if not self.git_available:
            raise RuntimeError("Not in a git repository.")
        r = subprocess.run(
            ["git", *args], cwd=self.repo_root,
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            raise RuntimeError((r.stdout + r.stderr).strip() or f"git {' '.join(args)} failed")
        return (r.stdout + r.stderr).strip() or "(no output)"

    def _load_index(self) -> dict:
        return json.loads(self.index_path.read_text())

    def _save_index(self, data: dict):
        self.index_path.write_text(json.dumps(data, indent=2))

    def _find(self, name: str) -> dict | None:
        for wt in self._load_index().get("worktrees", []):
            if wt.get("name") == name:
                return wt
        return None

    def _update_entry(self, name: str, **changes) -> dict:
        idx = self._load_index()
        updated = None
        for item in idx.get("worktrees", []):
            if item.get("name") == name:
                item.update(changes)
                updated = item
                break
        self._save_index(idx)
        if not updated:
            raise ValueError(f"Worktree '{name}' not found in index")
        return updated

    def _validate_name(self, name: str):
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", name or ""):
            raise ValueError("Invalid worktree name. Use 1-40 chars: letters, digits, ., _, -")

    def create(self, name: str, task_id: int = None, base_ref: str = "HEAD") -> str:
        self._validate_name(name)
        if self._find(name):
            raise ValueError(f"Worktree '{name}' already exists")
        if task_id is not None and not self.tasks.exists(task_id):
            raise ValueError(f"Task {task_id} not found")

        path = self.dir / name
        branch = f"wt/{name}"
        self.events.emit("worktree.create.before", task_id=task_id, wt_name=name)
        try:
            self._run_git(["worktree", "add", "-b", branch, str(path), base_ref])
            entry = {
                "name": name, "path": str(path), "branch": branch,
                "task_id": task_id, "status": "active", "created_at": time.time(),
            }
            idx = self._load_index()
            idx["worktrees"].append(entry)
            self._save_index(idx)
            if task_id is not None:
                self.tasks.bind_worktree(task_id, name)
            self.events.emit("worktree.create.after", task_id=task_id, wt_name=name)
            return json.dumps(entry, indent=2)
        except Exception as e:
            self.events.emit("worktree.create.failed", task_id=task_id, wt_name=name, error=str(e))
            raise

    def list_all(self) -> str:
        wts = self._load_index().get("worktrees", [])
        if not wts:
            return "No worktrees in index."
        lines = []
        for wt in wts:
            suffix = f" task={wt['task_id']}" if wt.get("task_id") else ""
            lines.append(f"[{wt.get('status', '?')}] {wt['name']} -> {wt['path']} ({wt.get('branch', '-')}){suffix}")
        return "\n".join(lines)

    def status(self, name: str) -> str:
        wt = self._find(name)
        if not wt:
            return f"Error: Unknown worktree '{name}'"
        path = Path(wt["path"])
        if not path.exists():
            return f"Error: Worktree path missing: {path}"
        r = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=path, capture_output=True, text=True, timeout=60,
        )
        return (r.stdout + r.stderr).strip() or "Clean worktree"

    def enter(self, name: str) -> str:
        wt = self._find(name)
        if not wt:
            return f"Error: Unknown worktree '{name}'"
        path = Path(wt["path"])
        if not path.exists():
            return f"Error: Worktree path missing: {path}"
        updated = self._update_entry(name, last_entered_at=time.time())
        self.events.emit("worktree.enter", task_id=wt.get("task_id"), wt_name=name, path=str(path))
        return json.dumps(updated, indent=2)

    def run(self, name: str, command: str) -> str:
        dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
        if any(d in command for d in dangerous):
            return "Error: Dangerous command blocked"
        wt = self._find(name)
        if not wt:
            return f"Error: Unknown worktree '{name}'"
        path = Path(wt["path"])
        if not path.exists():
            return f"Error: Worktree path missing: {path}"
        try:
            self._update_entry(
                name,
                last_entered_at=time.time(),
                last_command_at=time.time(),
                last_command_preview=command[:120],
            )
            self.events.emit("worktree.run.before", task_id=wt.get("task_id"), wt_name=name, command=command[:120])
            r = subprocess.run(command, shell=True, cwd=path,
                               capture_output=True, text=True, timeout=300)
            out = (r.stdout + r.stderr).strip()
            self.events.emit("worktree.run.after", task_id=wt.get("task_id"), wt_name=name)
            return out[:50000] if out else "(no output)"
        except subprocess.TimeoutExpired:
            self.events.emit("worktree.run.timeout", task_id=wt.get("task_id"), wt_name=name)
            return "Error: Timeout (300s)"

    def remove(
        self,
        name: str,
        force: bool = False,
        complete_task: bool = False,
        reason: str = "",
    ) -> str:
        wt = self._find(name)
        if not wt:
            return f"Error: Unknown worktree '{name}'"
        task_id = wt.get("task_id")
        self.events.emit("worktree.remove.before", task_id=task_id, wt_name=name)
        try:
            args = ["worktree", "remove"]
            if force:
                args.append("--force")
            args.append(wt["path"])
            self._run_git(args)
            if complete_task and task_id is not None:
                self.tasks.update(task_id, status="completed")
                self.events.emit("task.completed", task_id=task_id, wt_name=name)
            if task_id is not None:
                self.tasks.record_closeout(task_id, "removed", reason, keep_binding=False)
            self._update_entry(
                name,
                status="removed",
                removed_at=time.time(),
                closeout={"action": "remove", "reason": reason, "at": time.time()},
            )
            self.events.emit("worktree.remove.after", task_id=task_id, wt_name=name)
            return f"Removed worktree '{name}'"
        except Exception as e:
            self.events.emit("worktree.remove.failed", task_id=task_id, wt_name=name, error=str(e))
            raise

    def keep(self, name: str) -> str:
        wt = self._find(name)
        if not wt:
            return f"Error: Unknown worktree '{name}'"
        if wt.get("task_id") is not None:
            self.tasks.record_closeout(wt["task_id"], "kept", "", keep_binding=True)
        self._update_entry(
            name,
            status="kept",
            kept_at=time.time(),
            closeout={"action": "keep", "reason": "", "at": time.time()},
        )
        self.events.emit("worktree.keep", task_id=wt.get("task_id"), wt_name=name)
        return json.dumps(self._find(name), indent=2)

    def closeout(
        self,
        name: str,
        action: str,
        reason: str = "",
        force: bool = False,
        complete_task: bool = False,
    ) -> str:
        if action == "keep":
            wt = self._find(name)
            if not wt:
                return f"Error: Unknown worktree '{name}'"
            if wt.get("task_id") is not None:
                self.tasks.record_closeout(
                    wt["task_id"], "kept", reason, keep_binding=True
                )
                if complete_task:
                    self.tasks.update(wt["task_id"], status="completed")
            self._update_entry(
                name,
                status="kept",
                kept_at=time.time(),
                closeout={"action": "keep", "reason": reason, "at": time.time()},
            )
            self.events.emit(
                "worktree.closeout.keep",
                task_id=wt.get("task_id"),
                wt_name=name,
                reason=reason,
            )
            return json.dumps(self._find(name), indent=2)
        if action == "remove":
            self.events.emit("worktree.closeout.remove", wt_name=name, reason=reason)
            return self.remove(
                name,
                force=force,
                complete_task=complete_task,
                reason=reason,
            )
        raise ValueError("action must be 'keep' or 'remove'")


WORKTREES = WorktreeManager(REPO_ROOT, TASKS, EVENTS)


# -- Base tools (same as previous sessions, kept minimal) --
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"

def run_read(path: str, limit: int = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"

def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes"
    except Exception as e:
        return f"Error: {e}"

def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        c = fp.read_text()
        if old_text not in c:
            return f"Error: Text not found in {path}"
        fp.write_text(c.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


TOOL_HANDLERS = {
    "bash": lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "task_create": lambda **kw: TASKS.create(kw["subject"], kw.get("description", "")),
    "task_list": lambda **kw: TASKS.list_all(),
    "task_get": lambda **kw: TASKS.get(kw["task_id"]),
    "task_update": lambda **kw: TASKS.update(kw["task_id"], kw.get("status"), kw.get("owner")),
    "task_bind_worktree": lambda **kw: TASKS.bind_worktree(kw["task_id"], kw["worktree"], kw.get("owner", "")),
    "worktree_create": lambda **kw: WORKTREES.create(kw["name"], kw.get("task_id"), kw.get("base_ref", "HEAD")),
    "worktree_list": lambda **kw: WORKTREES.list_all(),
    "worktree_enter": lambda **kw: WORKTREES.enter(kw["name"]),
    "worktree_status": lambda **kw: WORKTREES.status(kw["name"]),
    "worktree_run": lambda **kw: WORKTREES.run(kw["name"], kw["command"]),
    "worktree_closeout": lambda **kw: WORKTREES.closeout(
        kw["name"],
        kw["action"],
        kw.get("reason", ""),
        kw.get("force", False),
        kw.get("complete_task", False),
    ),
    "worktree_keep": lambda **kw: WORKTREES.keep(kw["name"]),
    "worktree_remove": lambda **kw: WORKTREES.remove(
        kw["name"],
        kw.get("force", False),
        kw.get("complete_task", False),
        kw.get("reason", ""),
    ),
    "worktree_events": lambda **kw: EVENTS.list_recent(kw.get("limit", 20)),
}

# Compact tool definitions -- same schema, less vertical space
TOOLS = [
    {"name": "bash", "description": "Run a shell command in the current workspace.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "task_create", "description": "Create a new task on the shared task board.",
     "input_schema": {"type": "object", "properties": {"subject": {"type": "string"}, "description": {"type": "string"}}, "required": ["subject"]}},
    {"name": "task_list", "description": "List all tasks with status, owner, and worktree binding.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "task_get", "description": "Get task details by ID.",
     "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}},
    {"name": "task_update", "description": "Update task status or owner.",
     "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "deleted"]}, "owner": {"type": "string"}}, "required": ["task_id"]}},
    {"name": "task_bind_worktree", "description": "Bind a task to a worktree name.",
     "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}, "worktree": {"type": "string"}, "owner": {"type": "string"}}, "required": ["task_id", "worktree"]}},
    {"name": "worktree_create", "description": "Create a git worktree and optionally bind it to a task.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "task_id": {"type": "integer"}, "base_ref": {"type": "string"}}, "required": ["name"]}},
    {"name": "worktree_list", "description": "List worktrees tracked in .worktrees/index.json.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "worktree_enter", "description": "Enter or reopen a worktree lane before working in it.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "worktree_status", "description": "Show git status for one worktree.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "worktree_run", "description": "Run a shell command in a named worktree directory.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "command": {"type": "string"}}, "required": ["name", "command"]}},
    {"name": "worktree_closeout", "description": "Close out a lane by keeping it for follow-up or removing it.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "action": {"type": "string", "enum": ["keep", "remove"]}, "reason": {"type": "string"}, "force": {"type": "boolean"}, "complete_task": {"type": "boolean"}}, "required": ["name", "action"]}},
    {"name": "worktree_remove", "description": "Remove a worktree and optionally mark its bound task completed.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "force": {"type": "boolean"}, "complete_task": {"type": "boolean"}, "reason": {"type": "string"}}, "required": ["name"]}},
    {"name": "worktree_keep", "description": "Mark a worktree as kept without removing it.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "worktree_events", "description": "List recent lifecycle events.",
     "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}}}},
]


def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                try:
                    output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                except Exception as e:
                    output = f"Error: {e}"
                print(f"> {block.name}: {str(output)[:200]}")
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    print(f"Repo root for s18: {REPO_ROOT}")
    if not WORKTREES.git_available:
        print("Note: Not in a git repo. worktree_* tools will return errors.")

    history = []
    while True:
        try:
            query = input("\033[36ms18 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
