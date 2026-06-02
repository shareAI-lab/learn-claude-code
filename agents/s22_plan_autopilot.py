#!/usr/bin/env python3
# Harness: plan/autopilot -- plan first, execute second.
"""
s22_plan_autopilot.py - Plan/Autopilot Mode Switching

The agent generates a structured plan, the human reviews and approves,
then the agent executes steps autonomously without asking.

    Request -> [Plan Mode] -> Plan displayed -> User approves -> [Autopilot] -> Steps execute -> Done

    +--------+     +------------+     +-----------+     +------------+
    |  User  | --> | Plan Mode  | --> |  Human   | --> | Autopilot  |
    | request|     | (generate  |     |  reviews  |     | (execute   |
    |        |     |  plan JSON)|     |  approves |     |  steps)    |
    +--------+     +------------+     +-----------+     +-----+------+
                                                                  |
                                                                  v
                                                             +---------+
                                                             |  Done   |
                                                             +---------+

    Commands: /plan  /auto  /stop  /demo

Key insight: "Plan first, execute second -- humans review the plan, machines execute it."
"""

import json
import os
import subprocess
from enum import Enum
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]


class Mode(Enum):
    IDLE = "idle"
    PLAN = "plan"
    AUTOPILOT = "autopilot"


SYSTEM_PLAN = f"""You are a planning agent at {WORKDIR}.
Generate a structured plan as JSON. Return ONLY valid JSON, no markdown fences.
Format:
{{
  "steps": [
    {{"id": 1, "description": "...", "tools": ["bash"]}}
  ],
  "estimated_changes": ["file1.py"]
}}"""

SYSTEM_AUTO = f"""You are an execution agent at {WORKDIR}.
Execute the current plan step by step. Use tools to complete each step.
Report progress after each step. Stop on error and explain why."""


# -- Plan state --
class Plan:
    def __init__(self):
        self.steps = []
        self.estimated_changes = []
        self.completed = set()
        self.failed_step = None

    def load(self, data: dict) -> str:
        self.steps = data.get("steps", [])
        self.estimated_changes = data.get("estimated_changes", [])
        self.completed = set()
        self.failed_step = None
        return self.render()

    def render(self) -> str:
        if not self.steps:
            return "No plan loaded."
        lines = ["Plan:"]
        for s in self.steps:
            sid = s["id"]
            marker = "[x]" if sid in self.completed else (
                "[!]" if self.failed_step == sid else "[ ]"
            )
            tools = ", ".join(s.get("tools", []))
            lines.append(f"  {marker} #{sid}: {s['description']} ({tools})")
        if self.estimated_changes:
            lines.append(f"  Files: {', '.join(self.estimated_changes)}")
        done = len(self.completed)
        lines.append(f"  Progress: {done}/{len(self.steps)}")
        return "\n".join(lines)

    def mark_done(self, step_id: int):
        self.completed.add(step_id)

    def next_step(self) -> dict:
        for s in self.steps:
            if s["id"] not in self.completed:
                return s
        return None


PLAN = Plan()


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
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


def step_report(step_id: int, status: str, detail: str = "") -> str:
    if status == "done":
        PLAN.mark_done(step_id)
        return f"Step #{step_id} completed. {PLAN.render()}"
    if status == "error":
        PLAN.failed_step = step_id
        return f"Step #{step_id} failed: {detail}. Autopilot stopped."
    return f"Step #{step_id}: {detail}"


TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "step_report": lambda **kw: step_report(kw["step_id"], kw["status"], kw.get("detail", "")),
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
    {"name": "step_report", "description": "Report step progress. status: done or error.",
     "input_schema": {"type": "object", "properties": {"step_id": {"type": "integer"}, "status": {"type": "string", "enum": ["done", "error"]}, "detail": {"type": "string"}}, "required": ["step_id", "status"]}},
]


# -- Plan generation --
def generate_plan(request: str) -> str:
    messages = [{"role": "user", "content": f"Plan this task:\n{request}"}]
    response = client.messages.create(
        model=MODEL, system=SYSTEM_PLAN, messages=messages,
        max_tokens=4000,
    )
    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text
    text = text.strip().rstrip("`").strip()
    try:
        data = json.loads(text)
        return PLAN.load(data)
    except json.JSONDecodeError:
        return f"Plan parse error. Raw:\n{text[:500]}"


# -- Autopilot execution --
def run_autopilot(messages: list):
    """Execute plan steps sequentially. Stop on error or user interrupt."""
    while True:
        step = PLAN.next_step()
        if not step or PLAN.failed_step is not None:
            break
        sid = step["id"]
        desc = step["description"]
        tools = step.get("tools", [])
        prompt = (
            f"<step>{sid}. {desc}\nTools: {', '.join(tools)}\n"
            f"Execute this step, then call step_report with status=done.</step>"
        )
        messages.append({"role": "user", "content": prompt})
        while True:
            response = client.messages.create(
                model=MODEL, system=SYSTEM_AUTO, messages=messages,
                tools=TOOLS, max_tokens=8000,
            )
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                break
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    handler = TOOL_HANDLERS.get(block.name)
                    try:
                        output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                    except Exception as e:
                        output = f"Error: {e}"
                    print(f"  > {block.name}: {str(output)[:200]}")
                    results.append({
                        "type": "tool_result", "tool_use_id": block.id, "content": str(output),
                    })
            messages.append({"role": "user", "content": results})
    print(PLAN.render())


# -- Demo mode (no API calls) --
def run_demo():
    print("\n--- Plan/Autopilot Mode Flow (demo) ---\n")
    print("[1] User types request at REPL => Agent enters PLAN mode")
    print()
    print("[2] Agent generates structured plan:")
    demo = {
        "steps": [
            {"id": 1, "description": "Read auth.py and identify Strategy interface", "tools": ["read_file"]},
            {"id": 2, "description": "Extract Strategy to strategy.py", "tools": ["write_file"]},
            {"id": 3, "description": "Update imports in auth.py", "tools": ["edit_file"]},
            {"id": 4, "description": "Run tests to verify", "tools": ["bash"]},
        ],
        "estimated_changes": ["src/auth.py", "src/strategy.py"],
    }
    PLAN.load(demo)
    print(PLAN.render())
    print()
    print("[3] User reviews plan, types /auto => Agent enters AUTOPILOT mode")
    for step in PLAN.steps:
        PLAN.mark_done(step["id"])
        print(f"    Executing step #{step['id']}: {step['description']}")
    PLAN.steps = demo["steps"]
    PLAN.completed = {1, 2, 3, 4}
    print(f"\n[4] All steps complete:\n{PLAN.render()}")
    print("    Agent returns to IDLE. Type /stop to interrupt at any time.\n")


if __name__ == "__main__":
    mode = Mode.IDLE
    history = []
    pending_request = ""

    while True:
        try:
            query = input("\033[36ms22 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        cmd = query.strip()
        if cmd == "/demo":
            run_demo()
            continue
        if cmd.startswith("/plan"):
            request = cmd[6:].strip() or pending_request
            if not request:
                print("Usage: /plan <task description>")
                continue
            result = generate_plan(request)
            print(f"\n{result}")
            pending_request = ""
            print("Type /auto to execute, /stop to abort, or type a new request.")
            continue
        if cmd == "/auto":
            if not PLAN.steps:
                print("No plan loaded. Type your request, then /plan.")
                continue
            mode = Mode.AUTOPILOT
            history = [{"role": "user", "content": "Execute the current plan."}]
            print("\n--- Autopilot started ---")
            run_autopilot(history)
            print("--- Autopilot finished ---\n")
            mode = Mode.IDLE
            PLAN.steps = []
            PLAN.completed = set()
            continue
        if cmd == "/stop":
            if mode == Mode.AUTOPILOT:
                next_s = PLAN.next_step()
                if next_s:
                    PLAN.failed_step = next_s["id"]
                print("Autopilot stopped by user.")
                mode = Mode.IDLE
            continue

        # Default: treat as a request
        pending_request = query
        print("Request saved. Type /plan to generate a plan.")
