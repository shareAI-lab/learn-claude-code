#!/usr/bin/env python3
# Harness: persistent tasks -- goals that outlive any single conversation.


import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

# Keep imports stable when running from this directory
os.environ["PYTHONPATH"] = r"E:\ai_pycode\learn-claude-code-main"
sys.path.insert(0, r"E:\ai_pycode\learn-claude-code-main")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WORKDIR = Path.cwd()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
MODEL = os.environ.get("OPENAI_MODEL_ID")
TASKS_DIR = WORKDIR / ".tasks"

SYSTEM = f"你是一个编程助手，工作目录是 {WORKDIR}，请使用任务工具来规划和跟踪工作。任务有三种状态，一种是pending待完成，一种是blockedBy被阻塞，一种是completed已完成。"


# 应该补充代码，初始化所有任务，如果刚开始任务1是完成的，那么任务2和3依赖于任务1，输出却依赖显示任务2和3被阻塞
# -- TaskManager: CRUD with dependency graph, persisted as JSON files --
class TaskManager:
    def __init__(self, tasks_dir: Path):
        self.dir = tasks_dir
        self.dir.mkdir(exist_ok=True)
        self._next_id = self._max_id() + 1

    def _max_id(self) -> int:
        ids = [int(f.stem.split("_")[1]) for f in self.dir.glob("task_*.json")]
        return max(ids) if ids else 0

    def _load(self, task_id: int) -> dict:
        path = self.dir / f"task_{task_id}.json"
        if not path.exists():
            raise ValueError(f"Task {task_id} not found")
        return json.loads(path.read_text())

    def _save(self, task: dict):
        path = self.dir / f"task_{task['id']}.json"
        path.write_text(json.dumps(task, indent=2, ensure_ascii=False))

    def create(self, subject: str, description: str = "") -> str:
        # pending表示可以做，blockedBy表示依赖任务未解除
        task = {
            "id": self._next_id, "subject": subject, "description": description,
            "status": "pending", "blockedBy": [], "owner": "",
        }
        self._save(task)
        self._next_id += 1
        return json.dumps(task, indent=2, ensure_ascii=False)

    def get(self, task_id: int) -> str:
        return json.dumps(self._load(task_id), indent=2, ensure_ascii=False)

    def update(self, task_id: int, status: str = None,
               add_blocked_by: list = None, remove_blocked_by: list = None) -> str:
        task = self._load(task_id)
        if status:
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Invalid status: {status}")
            task["status"] = status
            if status == "completed":
                self._clear_dependency(task_id)
        if add_blocked_by:
            task["blockedBy"] = list(set(task["blockedBy"] + add_blocked_by))
        if remove_blocked_by:
            task["blockedBy"] = [x for x in task["blockedBy"] if x not in remove_blocked_by]
        self._save(task)
        return json.dumps(task, indent=2, ensure_ascii=False)

    def _clear_dependency(self, completed_id: int):
        """Remove completed_id from all other tasks' blockedBy lists.把已完成的任务id从其他任务的依赖列表中移除"""
        for f in self.dir.glob("task_*.json"):
            task = json.loads(f.read_text())
            if completed_id in task.get("blockedBy", []):
                task["blockedBy"].remove(completed_id)
                self._save(task)

    def list_all(self) -> str:
        tasks = []
        files = sorted(
            self.dir.glob("task_*.json"),
            key=lambda f: int(f.stem.split("_")[1])
        )
        for f in files:
            tasks.append(json.loads(f.read_text()))
        if not tasks:
            return "No tasks."
        lines = []
        for t in tasks:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}.get(t["status"], "[?]")
            blocked = f" (blocked by: {t['blockedBy']})" if t.get("blockedBy") else ""
            lines.append(f"{marker} #{t['id']}: {t['subject']}{blocked}")
        return "\n".join(lines)


TASKS = TaskManager(TASKS_DIR)


# -- Base tool implementations --
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
        if sys.platform == "win32":
            r = subprocess.run(
                command,
                shell=True,
                cwd=WORKDIR,
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="backslashreplace",
            )
        else:
            r = subprocess.run(
                command,
                shell=True,
                cwd=WORKDIR,
                capture_output=True,
                text=True,
                timeout=120,
                executable="/bin/bash",
                encoding="utf-8",
                errors="backslashreplace",
            )
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except Exception as e:
        return f"Error: {e}"

def run_read(path: str, limit: int = None) -> str:
    try:
        lines = safe_path(path).read_text(encoding="utf-8", errors="backslashreplace").splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"

def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8", errors="backslashreplace")
        return f"Wrote {len(content)} bytes"
    except Exception as e:
        return f"Error: {e}"

def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        c = fp.read_text(encoding="utf-8", errors="backslashreplace")
        if old_text not in c:
            return f"Error: Text not found in {path}"
        fp.write_text(c.replace(old_text, new_text, 1), encoding="utf-8", errors="backslashreplace")
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


TOOL_HANDLERS = {
    "bash":        lambda **kw: run_bash(kw["command"]),
    "read_file":   lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file":  lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":   lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "task_create": lambda **kw: TASKS.create(kw["subject"], kw.get("description", "")),
    "task_update": lambda **kw: TASKS.update(kw["task_id"], kw.get("status"), kw.get("addBlockedBy"), kw.get("removeBlockedBy")),
    "task_list":   lambda **kw: TASKS.list_all(),
    "task_get":    lambda **kw: TASKS.get(kw["task_id"]),
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace exact text in file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_create",
            "description": "Create a new task.",
            "parameters": {
                "type": "object",
                "properties": {"subject": {"type": "string"}, "description": {"type": "string"}},
                "required": ["subject"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_update",
            "description": "Update a task's status or dependencies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                    "addBlockedBy": {"type": "array", "items": {"type": "integer"}},
                    "removeBlockedBy": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_list",
            "description": "List all tasks with status summary.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_get",
            "description": "Get full details of a task by ID.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": {"type": "integer"}},
                "required": ["task_id"],
            },
        },
    },
]


def agent_loop(messages: list):
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM}, *messages],
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=8000,
            temperature=0.7,
        )

        assistant_message = response.choices[0].message
        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": assistant_message.tool_calls,
            }
        )

        if not assistant_message.tool_calls:
            return

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except Exception:
                args = {}

            handler = TOOL_HANDLERS.get(tool_name)
            try:
                output = handler(**args) if handler else f"Unknown tool: {tool_name}"
            except Exception as e:
                output = f"Error: {e}"

            print(f"> {tool_name}:")
            print(str(output)[:200])
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": str(output)})


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms07-openai >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        if history and history[-1].get("role") == "assistant" and history[-1].get("content"):
            print(history[-1]["content"])
        print()
