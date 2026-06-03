#!/usr/bin/env python3
# Harness: goal mode -- persistent objectives that survive sessions.
"""
s24_goal_mode.py - Goal Mode

The agent pursues a goal autonomously until success criteria are met
or budget exhausted. Goal state persists to disk between sessions.

    /goal "Implement auth" | "login works, tests pass"
        |
        v
    [Goal Created] -> [Agent works] -> [Self-check: done?] -> No -> loop
                                                |
                                             Yes -> [COMPLETED]
                                                |
                                         /pause -> [PAUSED] -> /resume -> continue

Key insight: "A goal survives the session -- the agent remembers what it was trying to do."
"""

import json
import os
import subprocess
import time
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
GOALS_DIR = WORKDIR / ".goals"


class GoalState(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# -- Goal: persistent objective with self-evaluation --
class Goal:
    def __init__(self, objective: str, success_criteria: str, max_iterations: int = 20):
        self.objective = objective
        self.success_criteria = success_criteria
        self.state = GoalState.CREATED
        self.progress = ""
        self.iterations = 0
        self.max_iterations = max_iterations
        self.created_at = time.time()
        self.updated_at = self.created_at

    def _save(self):
        GOALS_DIR.mkdir(parents=True, exist_ok=True)
        (GOALS_DIR / "goal.json").write_text(json.dumps({
            "objective": self.objective, "success_criteria": self.success_criteria,
            "state": self.state.value, "progress": self.progress,
            "iterations": self.iterations, "max_iterations": self.max_iterations,
            "created_at": self.created_at, "updated_at": self.updated_at,
        }, indent=2))

    @staticmethod
    def _load() -> "Goal | None":
        path = GOALS_DIR / "goal.json"
        if not path.exists():
            return None
        d = json.loads(path.read_text())
        g = Goal(d["objective"], d["success_criteria"], d["max_iterations"])
        g.state, g.progress = GoalState(d["state"]), d["progress"]
        g.iterations, g.created_at, g.updated_at = d["iterations"], d["created_at"], d["updated_at"]
        return g

    def status(self) -> str:
        c = {"CREATED": 36, "RUNNING": 32, "PAUSED": 33, "COMPLETED": 34, "FAILED": 31}.get(self.state.value, 0)
        return (
            f"\033[{c}m[{self.state.value}]\033[0m Goal: {self.objective}\n"
            f"  Criteria: {self.success_criteria}\n"
            f"  Progress: {self.progress or '(none)'}\n"
            f"  Iterations: {self.iterations}/{self.max_iterations}"
        )


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


TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
}

TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
]

# -- Goal checker: separate LLM call evaluates whether success criteria are met --
def goal_check(progress: str, success_criteria: str, latest_work: str) -> bool:
    response = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content": (
            f"Evaluate whether the goal's success criteria have been met.\n\n"
            f"Success criteria: {success_criteria}\n\n"
            f"Progress so far:\n{progress}\n\n"
            f"Latest work done:\n{latest_work}\n\n"
            f"Answer only 'YES' or 'NO', then briefly explain."
        )}],
        max_tokens=500,
    )
    text = next((b.text for b in response.content if hasattr(b, "text")), "NO").strip()
    return text.startswith("YES")


# -- Goal mode agent loop --
def goal_loop(goal: Goal, messages: list):
    goal.state = GoalState.RUNNING
    goal.updated_at = time.time()
    goal._save()

    while goal.state == GoalState.RUNNING:
        if goal.iterations >= goal.max_iterations:
            goal.state = GoalState.FAILED
            goal.progress += f"\n[FAILED: Budget exhausted at {goal.max_iterations} iterations]"
            goal.updated_at = time.time()
            goal._save()
            print(f"\n\033[31mGoal FAILED: budget exhausted\033[0m")
            return

        goal.iterations += 1
        system = (
            f"You are a coding agent at {WORKDIR}. "
            f"Your goal: {goal.objective}\n"
            f"Success criteria: {goal.success_criteria}\n"
            f"Progress so far:\n{goal.progress or '(none yet)'}\n\n"
            f"Working on iteration {goal.iterations}/{goal.max_iterations}. Use tools to make progress."
        )
        response = client.messages.create(
            model=MODEL, system=system, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "tool_use":
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

        latest_work = next((b.text for b in response.content if hasattr(b, "text")), "")

        print(f"\n[goal check iteration {goal.iterations}...]", end=" ")
        if goal_check(goal.progress, goal.success_criteria, latest_work):
            goal.state = GoalState.COMPLETED
            goal.updated_at = time.time()
            goal._save()
            print(f"\n\033[32mGoal COMPLETED in {goal.iterations} iterations!\033[0m")
            return
        print("\033[90mnot done yet\033[0m")

        summary = latest_work[:500].replace("\n", " ")
        goal.progress += f"\n[Iteration {goal.iterations}] {summary}"
        goal.updated_at = time.time()
        goal._save()


if __name__ == "__main__":
    goal = Goal._load()
    USAGE = "/goal <objective> | <criteria>  |  /goal pause  |  /goal resume  |  /goal clear"

    while True:
        try:
            query = input("\033[36ms24 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        cmd = query.strip()

        if cmd == "/demo":
            if goal:
                print(f"Active goal found. Use /goal clear to start fresh.\n{goal.status()}")
            else:
                goal = Goal("Create hello.py that prints 'Hello, Goal Mode!' and a test",
                            "hello.py exists, prints correct output, and a test passes", max_iterations=5)
                goal._save()
                print("Demo goal created:\n" + goal.status())
            continue
        if cmd == "/goal clear":
            path = GOALS_DIR / "goal.json"
            if path.exists():
                path.unlink()
                goal = None
                print("Goal cleared.")
            else:
                print("No active goal.")
            continue
        if cmd == "/goal pause":
            if not goal:
                print("No active goal.")
            elif goal.state == GoalState.RUNNING:
                goal.state = GoalState.PAUSED
                goal.updated_at = time.time()
                goal._save()
                print("Goal paused.\n" + goal.status())
            else:
                print(f"Cannot pause goal in {goal.state.value} state.")
            continue
        if cmd == "/goal resume":
            if not goal:
                print("No active goal.")
            elif goal.state == GoalState.PAUSED:
                print("Resuming goal...")
                goal_loop(goal, [])
                goal = Goal._load()
                print(goal.status())
            else:
                print(f"Cannot resume goal in {goal.state.value} state.")
            continue
        if cmd.startswith("/goal "):
            rest = cmd[6:]
            if "|" in rest:
                obj, criteria = rest.split("|", 1)
                if goal:
                    print("Active goal exists. Use /goal clear first.")
                else:
                    goal = Goal(obj.strip(), criteria.strip())
                    goal._save()
                    print("Goal set. Type any input to start.\n" + goal.status())
            elif rest.strip():
                print(f"Usage: {USAGE}")
            else:
                print(goal.status() if goal else f"No active goal. {USAGE}")
            continue

        if goal and goal.state in (GoalState.CREATED, GoalState.RUNNING):
            goal_loop(goal, [])
            goal = Goal._load()
        elif goal:
            print(f"Goal is {goal.state.value}. Use /goal resume.")
        else:
            print(f"No active goal. {USAGE}")
        print()
