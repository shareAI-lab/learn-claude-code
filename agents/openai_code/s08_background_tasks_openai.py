#!/usr/bin/env python3
# Harness: background execution -- the model thinks while the harness waits.


import json
import os
import subprocess
import sys
import threading
import uuid
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
MODEL = os.environ.get("OPENAI_MODEL_ID") or os.environ.get("MODEL_ID")

SYSTEM = f"你是一个编程助手，工作目录是 {WORKDIR}，请使用background_run工具来执行长期运行的命令。"


# -- BackgroundManager: threaded execution + notification queue --
class BackgroundManager:
    def __init__(self):
        self.tasks = {}  # task_id -> {status, result, command}
        self._notification_queue = []  # completed task results
        self._lock = threading.Lock()

    def run(self, command: str) -> str:
        """Start a background thread, return task_id immediately."""
        task_id = str(uuid.uuid4())[:8]
        self.tasks[task_id] = {"status": "running", "result": None, "command": command}
        thread = threading.Thread(
            target=self._execute, args=(task_id, command), daemon=True
        )
        thread.start()
        return f"Background task {task_id} started: {command[:80]}"

    def _execute(self, task_id: str, command: str):
        """Thread target: run subprocess, capture output, push to queue."""
        try:
            if sys.platform == "win32":
                r = subprocess.run(
                    command,
                    shell=True,
                    cwd=WORKDIR,
                    capture_output=True,
                    text=True,
                    timeout=300,
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
                    timeout=300,
                    executable="/bin/bash",
                    encoding="utf-8",
                    errors="backslashreplace",
                )
            output = (r.stdout + r.stderr).strip()[:50000]
            status = "completed"
        except subprocess.TimeoutExpired:
            output = "Error: Timeout (300s)"
            status = "timeout"
        except Exception as e:
            output = f"Error: {e}"
            status = "error"
        self.tasks[task_id]["status"] = status
        self.tasks[task_id]["result"] = output or "(no output)"
        with self._lock:
            self._notification_queue.append({
                "task_id": task_id,
                "status": status,
                "command": command[:80],
                "result": (output or "(no output)")[:500],
            })

    def check(self, task_id: str = None) -> str:
        """Check status of one task or list all."""
        if task_id:
            t = self.tasks.get(task_id)
            if not t:
                return f"Error: Unknown task {task_id}"
            return f"[{t['status']}] {t['command'][:60]}\n{t.get('result') or '(running)'}"
        # 不传入task_id时，列出所有任务
        lines = []
        for tid, t in self.tasks.items():
            lines.append(f"{tid}: [{t['status']}] {t['command'][:60]}")
        return "\n".join(lines) if lines else "No background tasks."

    # 清空通知队列
    def drain_notifications(self) -> list:
        """Return and clear all pending completion notifications."""
        with self._lock:
            notifs = list(self._notification_queue)
            self._notification_queue.clear()
        return notifs


BG = BackgroundManager()


# -- Tool implementations --
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
    "bash":             lambda **kw: run_bash(kw["command"]),
    "read_file":        lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file":       lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":        lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "background_run":   lambda **kw: BG.run(kw["command"]),
    "check_background": lambda **kw: BG.check(kw.get("task_id")),
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command (blocking).",
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
            "name": "background_run",
            "description": "在后台执行命令。返回任务id。",
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
            "name": "check_background",
            "description": "检查后台任务状态;无task_id时列出全部任务。",
            "parameters": {
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
            },
        },
    },
]


def agent_loop(messages: list):
    while True:
        # Drain background notifications and inject as system message before LLM call
        notifs = BG.drain_notifications()
        if notifs and messages:
            notif_text = "\n".join(
                f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs
            )
            messages.append({"role": "user", "content": f"<background-results>\n{notif_text}\n</background-results>"})
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
            query = input("\033[36ms08-openai >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        if history and history[-1].get("role") == "assistant" and history[-1].get("content"):
            print(history[-1]["content"])
        print()
