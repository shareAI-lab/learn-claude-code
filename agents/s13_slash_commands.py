#!/usr/bin/env python3
# Harness: slash commands -- user shortcuts that bypass the model.
"""
s13_slash_commands.py - Slash Commands

Slash commands are user input shortcuts intercepted by the harness BEFORE
reaching the model. They enable instant, deterministic actions that don't
need an LLM call.

    User input:
    +-------------+
    | "/tasks"    |
    +-----+-------+
          |
          v
    [Slash command router]  <--- harness intercepts, model never sees it
          |
    +-----+-----+------------+
    |     |     |            |
    v     v     v            v
  List  Clear  Show     Inject context
  tasks  history  tools  (e.g. /plan)

Two categories:

  1. Standalone (no model call): /tasks, /clear, /tools
     - Executed immediately, result printed, loop continues
     - Zero API cost, zero latency

  2. Context injection (becomes a message): /plan, /debug
     - Expands to a structured prompt that IS sent to the model
     - Like a macro: short input -> rich, pre-written instruction

Key insight: "Slash commands give the user direct harness control."
"""

import json
import os
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

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks."


# -- Slash command handlers --

def cmd_tasks() -> str:
    """List all tasks on the task board."""
    tasks_dir = WORKDIR / ".tasks"
    if not tasks_dir.exists():
        return "No task board found (.tasks/ does not exist)."
    tasks = []
    for f in sorted(tasks_dir.glob("task_*.json")):
        try:
            tasks.append(json.loads(f.read_text()))
        except Exception:
            pass
    if not tasks:
        return "No tasks yet."
    lines = []
    for t in tasks:
        marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}.get(
            t.get("status", ""), "[?]"
        )
        owner = f" @{t['owner']}" if t.get("owner") else ""
        lines.append(f"  {marker} #{t['id']}: {t.get('subject', '-')}{owner}")
    return "\n".join(lines)


def cmd_clear() -> str:
    """Clear conversation history."""
    return "__CLEAR__"  # sentinel for caller to truncate history


def cmd_tools() -> str:
    """Show available tools."""
    lines = ["Available tools:"]
    for tool in TOOLS:
        name = tool["name"]
        desc = tool.get("description", "")
        lines.append(f"  - {name}: {desc}")
    lines.append(f"\nSlash commands: {', '.join(SLASH_COMMANDS.keys())}")
    return "\n".join(lines)


# -- Context injection: expand short command to rich prompt --

def inject_plan() -> str:
    """Expand /plan into a structured planning prompt."""
    return (
        "<plan-mode>\n"
        "Before implementing, outline your approach:\n"
        "1. What files need to change?\n"
        "2. What are the key steps?\n"
        "3. What could go wrong?\n"
        "List your plan, then wait for approval before coding.\n"
        "</plan-mode>"
    )


def inject_debug() -> str:
    """Expand /debug into a structured debugging prompt."""
    return (
        "<debug-mode>\n"
        "Diagnose the last failure. Follow this loop:\n"
        "1. Reproduce: what input triggers it?\n"
        "2. Isolate: minimize to the smallest failing case.\n"
        "3. Hypothesize: what could cause this?\n"
        "4. Verify: check your hypothesis with a test.\n"
        "</debug-mode>"
    )


# -- Slash command registry --

SLASH_COMMANDS = {
    # Standalone: returns output string (or sentinel), no model call
    "tasks": cmd_tasks,
    "clear": cmd_clear,
    "tools": cmd_tools,
    # Context injection: returns expanded prompt text sent to model
    "plan": inject_plan,
    "debug": inject_debug,
}


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
        r = subprocess.run(
            command,
            shell=True,
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
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
}

TOOLS = [
    {
        "name": "bash",
        "description": "Run a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read file contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace exact text in file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
]


# -- Slash command router --

def handle_slash_command(query: str):
    """
    Parse a slash command and return (action, payload).

    action: "standalone" | "inject" | None
      - "standalone": (action, output_string) -- print and skip model call
      - "inject":     (action, expanded_prompt) -- send to model instead of raw input
      - None: not a slash command, return original query
    """
    stripped = query.strip()
    if not stripped.startswith("/"):
        return (None, query)

    parts = stripped[1:].split(None, 1)
    cmd = parts[0].lower()
    handler = SLASH_COMMANDS.get(cmd)
    if not handler:
        return (None, f"Unknown command: /{cmd}. Available: {', '.join(f'/{k}' for k in sorted(SLASH_COMMANDS))}")

    result = handler()
    if result == "__CLEAR__":
        return ("standalone", result)  # sentinel for history truncation
    elif cmd in ("plan", "debug"):
        return ("inject", result)
    else:
        return ("standalone", result)


# -- Agent loop --

def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
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
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(output),
                    }
                )
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    history = []
    print("Slash commands: /tasks /clear /tools /plan /debug")

    while True:
        try:
            query = input("\033[36ms13 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        action, payload = handle_slash_command(query)

        if action == "standalone":
            # Standalone: handle immediately, no model call
            if payload == "__CLEAR__":
                history.clear()
                print("History cleared.")
            else:
                print(payload)
            continue
        elif action == "inject":
            # Injection: expand to rich prompt, send to model
            history.append({"role": "user", "content": payload})
        else:
            # Normal input (or unknown command error)
            history.append({"role": "user", "content": payload})

        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
