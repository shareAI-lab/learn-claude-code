#!/usr/bin/env python3
# Harness: named teams — @mention routes work to agents with independent configs.
"""
s25_named_teams.py - Named Team Agents

Each agent has a name, role, model tier, and independent system prompt.
Messages route via @mention — inspired by Codex --team and @mention messaging.

    User types:
    +-------------------------------------------+
    | @backend-review check auth.py security    |
    +-------------------+-----------------------+
                        |
                        v
               [@mention router]
                        |
          +-------------+-------------+
          |                           |
          v                           v
    [backend-review agent]     [frontend-dev agent]
    model: claude-sonnet        model: claude-haiku
    system: security audit      system: UI guidelines

    vs s09 (file-based inboxes):
    s09:  lead spawns teammates -> writes to JSONL inbox -> they poll
    s25:  user mentions @name directly -> agent runs immediately -> reply tagged

    @backend-review check security   ->  [backend-review agent]  -> result
    @frontend-dev update UI         ->  [frontend-dev agent]    -> result
    @all broadcast message          ->  [all agents]            -> results

Key insight: "Named agents with independent configs — @mention routes the work."
"""

import json
import os
import re
import subprocess
import threading
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]
TEAM_JSON = WORKDIR / ".named_team" / "team.json"

MENTION_RE = re.compile(r"^@([a-zA-Z0-9_-]+)\s+(.+)$")


# -- NamedAgent: config for a named team member --
class NamedAgent:
    def __init__(self, name, role, model=None, instructions="", status="idle"):
        self.name, self.role, self.model, self.instructions, self.status = (
            name, role, model or MODEL, instructions, status)

    def to_dict(self):
        return {"name": self.name, "role": self.role, "model": self.model,
                "instructions": self.instructions, "status": self.status}

    @staticmethod
    def from_dict(d):
        return NamedAgent(d["name"], d["role"], d.get("model"),
                          d.get("instructions", ""), d.get("status", "idle"))


# -- TeamRegistry: persists named agent configs as JSON --
class TeamRegistry:
    def __init__(self, path):
        self.path = Path(path); self.agents = {}; self._load()

    def _load(self):
        if self.path.exists():
            for a in json.loads(self.path.read_text()).get("agents", []):
                ag = NamedAgent.from_dict(a); self.agents[ag.name] = ag

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"agents": [a.to_dict() for a in self.agents.values()]}, indent=2))

    def register(self, name, role, model=None, instructions=""):
        name = name.strip().lower().replace(" ", "-")
        if name in self.agents:
            a = self.agents[name]; a.role = role; a.instructions = instructions
            if model: a.model = model
            self._save(); return f"Updated agent @{name}"
        self.agents[name] = NamedAgent(name, role, model, instructions)
        self._save(); return f"Added agent @{name} (role: {role})"

    def remove(self, name):
        name = name.strip().lower().replace(" ", "-")
        if name not in self.agents: return f"Agent @{name} not found"
        del self.agents[name]; self._save(); return f"Removed agent @{name}"

    def list_all(self):
        if not self.agents: return "No agents registered. Use /team add <name> <role> [instructions]"
        lines = ["\n\033[1mTeam Registry\033[0m"]
        lines.append(f"{'Name':<20} {'Role':<25} {'Model':<25} {'Status':<10}")
        lines.append("-" * 80)
        for a in sorted(self.agents.values(), key=lambda x: x.name):
            lines.append(f"{a.name:<20} {a.role:<25} {a.model:<25} \033[32m{a.status:<10}\033[0m")
        return "\n".join(lines + [f"\n{len(self.agents)} agent(s)"])

    def find(self, name):
        return self.agents.get(name.strip().lower().replace(" ", "-"))

    def all_names(self):
        return sorted(self.agents.keys())


REGISTRY = TeamRegistry(TEAM_JSON)


# -- Tool implementations --
def safe_path(p):
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR): raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_bash(command):
    if any(d in command for d in ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR, capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired: return "Error: Timeout (120s)"

def run_read(path, limit=None):
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines): lines = lines[:limit] + [f"... ({len(lines)-limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e: return f"Error: {e}"

def run_write(path, content):
    try:
        fp = safe_path(path); fp.parent.mkdir(parents=True, exist_ok=True); fp.write_text(content)
        return f"Wrote {len(content)} bytes"
    except Exception as e: return f"Error: {e}"

TOOL_HANDLERS = {
    "bash": lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
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


# -- Named agent loop: runs with its own system prompt and model --
def named_agent_loop(agent, prompt):
    agent.status = "working"; REGISTRY._save()
    system = (f"You are '{agent.name}' on the team. Role: {agent.role}.\n"
              f"Working directory: {WORKDIR}.\n{agent.instructions}\n\nUse tools to complete the task. Be concise.")
    messages = [{"role": "user", "content": prompt}]
    try:
        response = client.messages.create(model=agent.model, system=system,
                                          messages=messages, tools=TOOLS, max_tokens=8000)
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason == "tool_use":
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    handler = TOOL_HANDLERS.get(block.name)
                    output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
            messages.append({"role": "user", "content": results})
            response2 = client.messages.create(model=agent.model, system=system,
                                               messages=messages, max_tokens=8000)
            text = "".join(b.text for b in response2.content if hasattr(b, "text"))
        else:
            text = "".join(b.text for b in response.content if hasattr(b, "text"))
    except Exception as e: text = f"Error: {e}"
    finally:
        agent.status = "idle"; REGISTRY._save()
    return text or "(no output)"


def dispatch_agent(agent, prompt):
    """Dispatch to a named agent in its own thread, wait for result."""
    result = [None]
    def worker(): result[0] = named_agent_loop(agent, prompt)
    thread = threading.Thread(target=worker, daemon=True)
    thread.start(); thread.join(timeout=180)
    return result[0]


# -- Demo setup --
DEMO_AGENTS = [
    ("backend-review", "security reviewer", MODEL,
     "You specialize in security audits. Check for injection, auth flaws, hardcoded secrets."),
    ("frontend-dev", "UI developer", MODEL,
     "You specialize in frontend code. Focus on UX, accessibility, and clean React patterns."),
    ("docs-keeper", "documentation specialist", MODEL,
     "You keep documentation accurate and clear. Update docs when code changes."),
]


if __name__ == "__main__":
    while True:
        try: query = input("\033[36ms25 >> \033[0m")
        except (EOFError, KeyboardInterrupt): break
        if query.strip().lower() in ("q", "exit", ""): break
        cmd = query.strip()

        # /team commands
        if cmd.startswith("/team add "):
            parts = cmd[len("/team add "):].split(None, 2)
            if len(parts) < 2: print("Usage: /team add <name> <role> [instructions]")
            else: print(REGISTRY.register(parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
            continue
        if cmd.startswith("/team remove "):
            name = cmd[len("/team remove "):].strip()
            print(REGISTRY.remove(name) if name else "Usage: /team remove <name>")
            continue
        if cmd in ("/team list", "/team"):
            print(REGISTRY.list_all()); continue
        if cmd == "/team remove_all":
            REGISTRY.agents.clear(); REGISTRY._save(); print("All agents removed."); continue

        # /demo
        if cmd == "/demo":
            print("Setting up demo team with 3 agents...")
            for name, role, model, instr in DEMO_AGENTS: REGISTRY.register(name, role, model, instr)
            print(REGISTRY.list_all())
            demo_msg = "Write a brief Python function that validates an email address."
            agent = REGISTRY.find("backend-review")
            print(f"\nDispatching to @backend-review: {demo_msg}")
            if agent:
                print(f"\n\033[1m[backend-review]:\033[0m {dispatch_agent(agent, demo_msg)[:300]}")
            print(); continue

        # @mention routing
        m = MENTION_RE.match(cmd)
        if m:
            target, content = m.group(1).lower(), m.group(2)
            if target == "all":
                names = REGISTRY.all_names()
                if not names: print("No agents to broadcast to."); continue
                print(f"Broadcasting to {len(names)} agent(s)...")
                for n in names:
                    ag = REGISTRY.find(n); print(f"\n  Dispatching @{n}...")
                    if ag: print(f"\033[1m[{n}]:\033[0m {dispatch_agent(ag, content)[:300]}\n")
            else:
                agent = REGISTRY.find(target)
                if not agent:
                    names = REGISTRY.all_names()
                    print(f"Agent @{target} not found." + (f" Available: {', '.join('@'+n for n in names)}" if names else ""))
                    continue
                print(f"Routing to \033[1m@{target}\033[0m ({agent.role}, model={agent.model})...")
                result = dispatch_agent(agent, content)
                print(f"\n\033[1m[{target}]:\033[0m {result}")
            continue

        # Normal chat: route to first agent or prompt
        if REGISTRY.all_names():
            first = REGISTRY.find(REGISTRY.all_names()[0])
            print(f"No @mention — routing to @{first.name}...")
            print(f"\n\033[1m[{first.name}]:\033[0m {dispatch_agent(first, cmd)}")
        else:
            print("No agents registered. Use /team add or /demo to start.")
        print()
