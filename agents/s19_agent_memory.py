#!/usr/bin/env python3
# Harness: persistence — agent state survives across sessions.
"""
s19_agent_memory.py - Agent Memory & Persistence

Save and restore agent state across sessions using JSON files.
Two memory tiers: priority (small, always loaded) and working (timestamped, pruned).

    .agent_memory/
    ├── priority.json      (always loaded, < 500 chars)
    │                       {"directives": ["..."], "preferences": {...}}
    ├── working/
    │   ├── 2025-01-01T12-00-00.json  (timestamped entries)
    │   └── 2025-01-02T08-30-00.json
    └── checkpoint.json    (last conversation state)

    Session lifecycle:
    1. STARTUP: load priority + recent working memory
    2. LOAD: restore checkpoint (conversation state)
    3. WORK: agent loop, append messages
    4. SAVE: checkpoint after each turn
    5. PRUNE: remove working memory > 7 days old

    Priority vs Working:
    Priority  — small, always loaded, never pruned
    Working   — timestamped, loaded if recent, auto-pruned

Key insight: "Files outside the conversation outlive the conversation."
"""

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

MEMORY_DIR = WORKDIR / ".agent_memory"
WORKING_DIR = MEMORY_DIR / "working"


# -- MemoryStore: two-tier persistence --
class MemoryStore:
    """Two-tier memory: priority (small, always loaded) + working (timestamped, pruned)."""

    def __init__(self, base_dir: Path):
        self.base = base_dir
        self.working = base_dir / "working"
        self.base.mkdir(parents=True, exist_ok=True)
        self.working.mkdir(parents=True, exist_ok=True)

    # --- Priority memory: always loaded, never pruned ---
    def read_priority(self) -> dict:
        path = self.base / "priority.json"
        if not path.exists():
            return {"directives": [], "notes": {}}
        return json.loads(path.read_text())

    def write_priority(self, data: dict):
        path = self.base / "priority.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def add_directive(self, directive: str):
        data = self.read_priority()
        if "directives" not in data:
            data["directives"] = []
        data["directives"].append(directive)
        self.write_priority(data)
        return f"Added directive: {directive}"

    def add_note(self, key: str, value: str):
        data = self.read_priority()
        if "notes" not in data:
            data["notes"] = {}
        data["notes"][key] = value
        self.write_priority(data)
        return f"Saved note: {key}={value}"

    # --- Working memory: timestamped entries, auto-pruned ---
    def write_working(self, content: str) -> str:
        ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        path = self.working / f"{ts}.json"
        entry = {"timestamp": ts, "content": content}
        path.write_text(json.dumps(entry, indent=2, ensure_ascii=False))
        return f"Saved at {ts}"

    def read_working(self, hours: int = 24) -> list:
        """Read working memory entries from the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        entries = []
        for f in sorted(self.working.glob("*.json")):
            entry = json.loads(f.read_text())
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts >= cutoff:
                entries.append(entry)
        return entries

    def prune(self, days: int = 7) -> int:
        """Remove entries older than N days."""
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0
        for f in self.working.glob("*.json"):
            entry = json.loads(f.read_text())
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts < cutoff:
                f.unlink()
                removed += 1
        return removed

    # --- Checkpoint: conversation state ---
    def save_checkpoint(self, messages: list):
        """Save conversation state. Convert content blocks to serializable format."""
        serializable = []
        for msg in messages:
            new_msg = {"role": msg["role"]}
            content = msg.get("content", "")
            # Handle Anthropic content blocks
            if isinstance(content, list):
                blocks = []
                for block in content:
                    if hasattr(block, "type"):
                        if block.type == "text":
                            blocks.append({"type": "text", "text": block.text})
                        elif block.type == "tool_use":
                            blocks.append({
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            })
                        else:
                            blocks.append({"type": str(block)})
                    else:
                        blocks.append(block)
                new_msg["content"] = blocks
            else:
                new_msg["content"] = content
            serializable.append(new_msg)

        path = self.base / "checkpoint.json"
        path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False))

    def load_checkpoint(self) -> list:
        """Load last checkpoint. Returns empty list if none exists."""
        path = self.base / "checkpoint.json"
        if not path.exists():
            return []
        return json.loads(path.read_text())

    def clear(self):
        """Clear all memory."""
        for f in self.base.glob("*.json"):
            f.unlink()
        for f in self.working.glob("*.json"):
            f.unlink()


MEMORY = MemoryStore(MEMORY_DIR)


# -- Build system prompt with memory context --
def build_system_prompt(messages: list) -> str:
    """Build system prompt that includes priority + working memory."""
    parts = [f"You are a persistent coding agent at {WORKDIR}."]

    # Priority memory — always included
    priority = MEMORY.read_priority()
    if priority.get("directives"):
        parts.append("\n## Standing Directives")
        for d in priority["directives"]:
            parts.append(f"  - {d}")
    if priority.get("notes"):
        parts.append("\n## Notes")
        for k, v in priority["notes"].items():
            parts.append(f"  {k}: {v}")

    # Working memory — recent entries
    recent = MEMORY.read_working(hours=24)
    if recent:
        parts.append(f"\n## Recent Memory ({len(recent)} entries)")
        for entry in recent[-5:]:  # Last 5 entries max
            parts.append(f"  [{entry['timestamp']}] {entry['content'][:200]}")

    return "\n".join(parts)


# -- Base tools --
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


TOOL_HANDLERS = {
    "bash":      lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
    "mem_save":  lambda **kw: MEMORY.write_working(kw["content"]),
    "mem_load":  lambda **kw: json.dumps(MEMORY.read_working(kw.get("hours", 24)), indent=2),
    "mem_directive": lambda **kw: MEMORY.add_directive(kw["directive"]),
}

TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "mem_save", "description": "Save content to working memory (timestamped, auto-pruned after 7 days).",
     "input_schema": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}},
    {"name": "mem_load", "description": "Load recent working memory entries.",
     "input_schema": {"type": "object", "properties": {"hours": {"type": "integer", "description": "Hours to look back"}}}},
    {"name": "mem_directive", "description": "Add a standing directive to priority memory (persists always).",
     "input_schema": {"type": "object", "properties": {"directive": {"type": "string"}}, "required": ["directive"]}},
]


def agent_loop(messages: list):
    system = build_system_prompt(messages)
    while True:
        response = client.messages.create(
            model=MODEL, system=system, messages=messages,
            tools=TOOLS, max_tokens=4000,
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
                print(f"> {block.name}: {str(output)[:120]}")
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    # Restore previous session
    history = MEMORY.load_checkpoint()
    if history:
        print(f"Restored {len(history)} messages from previous session.")
    else:
        print("Fresh session — no prior state.")

    # Prune old working memory
    pruned = MEMORY.prune(days=7)
    if pruned:
        print(f"Pruned {pruned} old working memory entries.")

    print(f"\nMemory directory: {MEMORY_DIR}")
    print("Commands: /memory /checkpoint /save /clear /directives")
    print("Memory is auto-saved after each turn.\n")

    while True:
        try:
            query = input("\033[36ms19 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        cmd = query.strip()

        if cmd == "/memory":
            priority = MEMORY.read_priority()
            print(f"\n=== Priority Memory ===")
            print(json.dumps(priority, indent=2))
            working = MEMORY.read_working()
            print(f"\n=== Working Memory ({len(working)} entries) ===")
            for entry in working[-5:]:
                print(f"  [{entry['timestamp']}] {entry['content'][:100]}")
            print()
            continue

        if cmd == "/checkpoint":
            print(f"Checkpoint: {len(history)} messages")
            path = MEMORY_DIR / "checkpoint.json"
            if path.exists():
                size = path.stat().st_size
                print(f"  File size: {size} bytes")
            print()
            continue

        if cmd == "/save":
            MEMORY.save_checkpoint(history)
            print("Checkpoint saved.")
            priority = MEMORY.read_priority()
            if priority.get("directives"):
                MEMORY.write_priority(priority)  # ensure priority is up to date
            print()
            continue

        if cmd == "/clear":
            MEMORY.clear()
            history.clear()
            print("All memory cleared. Starting fresh.")
            print()
            continue

        if cmd.startswith("/directive"):
            text = cmd[len("/directive"):].strip()
            if text:
                result = MEMORY.add_directive(text)
                print(result)
            else:
                print("Usage: /directive <your standing instruction>")
            print()
            continue

        if cmd.startswith("/note"):
            parts = cmd[5:].strip().split("=", 1)
            if len(parts) == 2:
                key, value = parts[0].strip(), parts[1].strip()
                print(MEMORY.add_note(key, value))
            else:
                print("Usage: /note key=value")
            print()
            continue

        if cmd.startswith("/prune"):
            count = MEMORY.prune()
            print(f"Pruned {count} old entries.")
            print()
            continue

        if cmd.startswith("/memsave"):
            text = cmd[7:].strip()
            if text:
                print(MEMORY.write_working(text))
            else:
                print("Usage: /memsave <content>")
            print()
            continue

        # Normal interaction
        history.append({"role": "user", "content": query})
        agent_loop(history)

        # Auto-save checkpoint after each turn
        MEMORY.save_checkpoint(history)

        # Print response
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
