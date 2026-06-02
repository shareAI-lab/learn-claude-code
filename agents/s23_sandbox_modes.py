#!/usr/bin/env python3
# Harness: sandbox modes -- OS-level safety boundaries for tool execution.
"""
s23_sandbox_modes.py - Sandbox Modes

The harness defines what the model is allowed to touch.

    Model requests tool ---> [Sandbox Check] ---> Allowed? ---> Execute tool
                                  ^                    |
                                  |                    | Denied
                         +--------+--------+           |
                         |  WORKSPACE_READ  |  "Blocked: read-only mode"
                         |  WORKSPACE_WRITE |
                         |  NETWORK_ISOLATED |
                         |  UNRESTRICTED    |
                         +-----------------+

    Decision flow: enforce_path() -> check_command() -> check_read/write()

Key insight: "The harness defines what the model is allowed to touch."
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

# -- Sandboxed modes --
WORKSPACE_READ = "workspace_read"
WORKSPACE_WRITE = "workspace_write"
NETWORK_ISOLATED = "network_isolated"
UNRESTRICTED = "unrestricted"

SYSTEM = f"You are a coding agent at {WORKDIR}. Sandbox mode controls what you can do."

SAFE_COMMANDS = [r"^ls\b", r"^cat\b", r"^grep\b", r"^git status\b", r"^python\s+-m\s+pytest\b", r"^find\b", r"^head\b", r"^tail\b", r"^wc\b", r"^diff\b", r"^pwd\b", r"^echo\b"]
WRITE_COMMANDS = [r"^cp\b", r"^mv\b", r"^mkdir\b", r"^touch\b", r"^git add\b", r"^git commit\b", r"^ln\b"]
NETWORK_COMMANDS = [r"^curl\b", r"^wget\b", r"^git push\b", r"^npm install\b", r"^pip install\b", r"^git fetch\b", r"^git pull\b", r"^git clone\b"]
DANGEROUS_COMMANDS = [r"rm\s+-rf\b", r"^\s*sudo\b", r"chmod\s+777\b", r"^shutdown\b", r"^reboot\b", r">\s*/dev/", r"\|\s*sh\b"]


class Sandbox:
    """Policy layer that checks every tool call before execution."""

    def __init__(self, mode: str = WORKSPACE_READ):
        self.mode = mode
        self.log: list[str] = []

    # -- Path checks --
    def check_read(self, path: str) -> bool:
        return True  # all modes allow reads within workspace

    def check_write(self, path: str) -> bool:
        if self.mode in (WORKSPACE_WRITE, NETWORK_ISOLATED, UNRESTRICTED):
            return True
        return False

    def enforce_path(self, path: str) -> Path:
        resolved = (WORKDIR / path).resolve()
        if not str(resolved).startswith(str(WORKDIR.resolve())):
            raise ValueError(f"Path escapes workspace: {path}")
        return resolved

    # -- Command classification --
    def classify_command(self, cmd: str) -> str:
        for pattern in DANGEROUS_COMMANDS:
            if re.search(pattern, cmd):
                return "dangerous"
        for pattern in NETWORK_COMMANDS:
            if re.search(pattern, cmd):
                return "network"
        for pattern in WRITE_COMMANDS:
            if re.search(pattern, cmd):
                return "write"
        for pattern in SAFE_COMMANDS:
            if re.search(pattern, cmd):
                return "safe"
        return "unknown"

    def check_command(self, cmd: str) -> tuple[bool, str]:
        category = self.classify_command(cmd)

        if category == "dangerous":
            self.log.append(f"DENY command[{category}]: {cmd[:60]}")
            return False, f"Blocked: dangerous command ({cmd[:40]}...)"

        if category == "network" and self.mode == NETWORK_ISOLATED:
            self.log.append(f"DENY command[network]: {cmd[:60]}")
            return False, "Blocked: network access disabled in network_isolated mode"

        if category == "write" and self.mode == WORKSPACE_READ:
            self.log.append(f"DENY command[write]: {cmd[:60]}")
            return False, "Blocked: write commands disabled in workspace_read mode"

        if category in ("unknown", "network") and self.mode == WORKSPACE_READ:
            self.log.append(f"DENY command[{category}]: {cmd[:60]}")
            return False, f"Blocked: {category} command in workspace_read mode"

        self.log.append(f"ALLOW command[{category}]: {cmd[:60]}")
        return True, "allowed"

    def check_tool(self, tool_name: str, **kwargs) -> tuple[bool, str]:
        if tool_name == "bash":
            return self.check_command(kwargs.get("command", ""))
        if tool_name in ("write_file", "edit_file"):
            if not self.check_write(kwargs.get("path", "")):
                self.log.append(f"DENY {tool_name}: {kwargs.get('path', '')}")
                return False, "Blocked: write disabled in workspace_read mode"
        return True, "allowed"

    def switch(self, mode: str) -> str:
        valid = {WORKSPACE_READ, WORKSPACE_WRITE, NETWORK_ISOLATED, UNRESTRICTED}
        if mode not in valid:
            return f"Error: Invalid mode '{mode}'. Valid: {valid}"
        old = self.mode
        self.mode = mode
        self.log.append(f"MODE {old} -> {mode}")
        return f"Sandbox: {old} -> {mode}"

    def summary(self) -> str:
        lines = [f"Mode: {self.mode}", f"Checks: {len(self.log)}"]
        recent = self.log[-10:]
        for entry in recent:
            lines.append(f"  {entry}")
        return "\n".join(lines)


SANDBOX = Sandbox(WORKSPACE_READ)


# -- Tool implementations --
def safe_path(p: str) -> Path:
    return SANDBOX.enforce_path(p)


def run_bash(command: str) -> str:
    allowed, reason = SANDBOX.check_tool("bash", command=command)
    if not allowed:
        return reason
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"


def run_read(path: str, limit: int = None) -> str:
    if not SANDBOX.check_read(path):
        return "Blocked: read access denied"
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    allowed, reason = SANDBOX.check_tool("write_file", path=path)
    if not allowed:
        return reason
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    allowed, reason = SANDBOX.check_tool("edit_file", path=path)
    if not allowed:
        return reason
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
    "bash":             lambda **kw: run_bash(kw["command"]),
    "read_file":        lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file":       lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":        lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "sandbox_mode":     lambda **kw: SANDBOX.switch(kw["mode"]),
    "sandbox_status":   lambda **kw: SANDBOX.summary(),
}

TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "sandbox_mode", "description": "Switch sandbox mode: workspace_read, workspace_write, network_isolated, unrestricted.",
     "input_schema": {"type": "object", "properties": {"mode": {"type": "string"}}, "required": ["mode"]}},
    {"name": "sandbox_status", "description": "Show current sandbox mode and recent access log.",
     "input_schema": {"type": "object", "properties": {}}},
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


def demo_all_modes():
    test_cmds = [("ls agents/", "safe"), ("mkdir test", "write"), ("curl https://x.com", "network"), ("rm -rf /", "dangerous")]
    for mode in [WORKSPACE_READ, WORKSPACE_WRITE, NETWORK_ISOLATED, UNRESTRICTED]:
        SANDBOX.switch(mode)
        print(f"\n--- {mode} ---")
        for cmd, cat in test_cmds:
            ok, _ = SANDBOX.check_command(cmd)
            print(f"  {'ALLOW' if ok else 'DENY ':5s} [{cat:10s}] {cmd}")


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms23 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        stripped = query.strip()
        if stripped.lower() in ("q", "exit", ""):
            break
        if stripped.startswith("/sandbox"):
            mode = stripped.split(None, 1)[1] if len(stripped.split(None, 1)) > 1 else ""
            if mode:
                print(SANDBOX.switch(mode))
            else:
                print(f"Current mode: {SANDBOX.mode}")
            continue
        if stripped.startswith("/check "):
            target = stripped[7:].strip()
            allowed, reason = SANDBOX.check_command(target)
            cat = SANDBOX.classify_command(target)
            print(f"[{cat}] {'ALLOW' if allowed else 'DENY':4s}: {reason}")
            continue
        if stripped == "/demo":
            demo_all_modes()
            continue
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
