#!/usr/bin/env python3
# Harness: hierarchical instructions — AGENTS.md at every level, nearest wins.
"""
s21_agents_md.py - AGENTS.md Hierarchy

Instruction files at different directory levels. Walk up from the target
file, collect every AGENTS.md, then merge farthest-first so nearest wins.

    /project/
    |-- AGENTS.md              "Write tests for all new code"
    |-- src/
    |   |-- AGENTS.md          "No tests for auto-generated code"
    |   |-- generated/code.py  --> resolves: [global + src override]
    |-- tests/
    |   |-- AGENTS.md          "Use pytest, assert patterns"
    `-- docs/
        |-- AGENTS.md          "Use Markdown, no HTML"

    Resolve /project/src/generated/code.py:
    1. Walk up: /project/src/ (found), /project/ (found)
    2. Merge: farthest first, nearest last => nearest section overrides

    +-------------------------------+
    | [1] /project/AGENTS.md        |  "Write tests for all new code"
    | [2] /project/src/AGENTS.md    |  "No tests for auto-generated code"
    +-------------------------------+
    | Merged: nearest (src) wins    |
    +-------------------------------+

Key insight: "Instructions are local to where they matter."
"""

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

# -- In-memory demo filesystem (no real files created) --
DEMO_FS = {
    "/project/AGENTS.md": (
        "## Rules\nWrite tests for all new code\nUse type hints\nFollow PEP 8\n"
        "## Style\n4-space indentation\nMax line length: 100\n"
        "## Tools\nUse pytest for testing\n"
    ),
    "/project/src/AGENTS.md": "## Rules\nNo tests for auto-generated code\nUse logging instead of print\n",
    "/project/tests/AGENTS.md": (
        "## Rules\nUse pytest, assert patterns\nTest edge cases first\n"
        "## Tools\nRun tests with -v --tb=short\n"
    ),
    "/project/docs/AGENTS.md": "## Style\nUse Markdown, no HTML\nInclude code examples\n",
}


class InstructionsLoader:
    """Find and merge AGENTS.md files from a file's directory up to root."""

    def __init__(self, fs: dict):
        self.fs = fs

    def find_agents_md(self, file_path: str) -> list[str]:
        """Walk up from file_path to root, find all AGENTS.md files (farthest first)."""
        parts = [p for p in file_path.strip("/").split("/") if p]
        found = []
        for i in range(len(parts), 0, -1):
            agent = "/" + "/".join(parts[:i]) + "/AGENTS.md"
            if agent in self.fs:
                found.append(agent)
        return list(reversed(found))

    def parse_sections(self, content: str) -> dict:
        """Parse AGENTS.md into sections: rules, tools, style."""
        sections = {"rules": [], "tools": [], "style": []}
        current = "rules"
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("## "):
                header = line[3:].strip().lower()
                current = header if header in sections else "rules"
            elif line.startswith("- ") or line.startswith("* "):
                sections[current].append(line[2:].strip())
            else:
                sections[current].append(line)
        return sections

    def merge_instructions(self, paths: list[str]) -> dict:
        """Merge from farthest to nearest. Nearest wins per section."""
        merged: dict[str, list[str]] = {"rules": [], "tools": [], "style": []}
        trace = []
        for p in paths:
            sections = self.parse_sections(self.fs[p])
            trace.append({"path": p.lstrip("/"), "sections": sections})
            for key in merged:
                if sections[key]:
                    merged[key] = sections[key]
        return {"merged": merged, "trace": trace}

    def resolve(self, file_path: str) -> dict:
        """Return merged instructions for a given file path."""
        paths = self.find_agents_md(file_path)
        if not paths:
            return {"file": file_path, "paths": [],
                    "merged": {"rules": [], "tools": [], "style": []}, "trace": []}
        result = self.merge_instructions(paths)
        result["file"] = file_path
        result["paths"] = paths
        return result


LOADER = InstructionsLoader(DEMO_FS)


def format_resolve(result: dict) -> str:
    """Format a resolved instruction set for display."""
    lines = [f"File: {result['file']}"]
    if not result["paths"]:
        return lines[0] + "\n  (no AGENTS.md found)"

    lines.append(f"\nFound {len(result['paths'])} AGENTS.md:")
    for i, p in enumerate(result["paths"]):
        tag = "nearest" if i == len(result["paths"]) - 1 else "base"
        lines.append(f"  [{tag}] {p}")

    lines.append("\nMerged instructions:")
    for section in ("rules", "tools", "style"):
        items = result["merged"][section]
        if items:
            lines.append(f"  ## {section.capitalize()}")
            for item in items:
                lines.append(f"    - {item}")

    if result.get("trace"):
        lines.append("\nSection sources:")
        for entry in result["trace"]:
            for section in ("rules", "tools", "style"):
                if entry["sections"][section]:
                    lines.append(f"  {section.capitalize():8s} <- {entry['path']}")
    return "\n".join(lines)


def format_tree() -> str:
    """Show the demo directory structure with instruction annotations."""
    return """\
/project/
├── AGENTS.md          "Write tests for all new code, type hints, PEP 8"
├── src/
│   ├── AGENTS.md      "No tests for auto-generated code, use logging"
│   └── generated/
├── tests/
│   └── AGENTS.md      "Use pytest, assert patterns, test edge cases"
└── docs/
    └── AGENTS.md      "Use Markdown, no HTML, include examples"

Nearest-file-wins: deeper AGENTS.md overrides parent sections."""


def run_demo():
    """Full demo: walk the tree, collect, merge, show results."""
    print("=" * 60)
    print("  AGENTS.md Hierarchical Instructions Demo")
    print("=" * 60)
    print(f"\n{format_tree()}\n")

    path = "/project/src/generated/code.py"
    paths = LOADER.find_agents_md(path)
    print(f"Walk up from {path}:")
    for i, p in enumerate(paths):
        print(f"  [{i + 1}] {p}")
    print()

    print("Merge (farthest first, nearest overrides):")
    for entry in LOADER.merge_instructions(paths)["trace"]:
        for section in ("rules", "tools", "style"):
            if entry["sections"][section]:
                print(f"  [{entry['path']}] {section}: {entry['sections'][section][:1]}")
    print()

    for demo_path in ["/project/src/generated/code.py", "/project/tests/test_utils.py", "/project/docs/guide.md"]:
        print(f"--- {demo_path} ---")
        print(format_resolve(LOADER.resolve(demo_path)))
        print()

    print("Demo complete.")


# -- Tools --
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
}

TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
]


def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=f"You are a coding agent at {WORKDIR}.",
            messages=messages, tools=TOOLS, max_tokens=8000,
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
    print("Commands: /demo  /tree  /resolve <path>")
    print()
    history = []
    while True:
        try:
            query = input("\033[36ms21 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        if query.strip() == "/demo":
            run_demo(); print(); continue
        if query.strip() == "/tree":
            print(format_tree()); print(); continue
        if query.strip().startswith("/resolve"):
            parts = query.strip().split(maxsplit=1)
            if len(parts) < 2:
                print("Usage: /resolve <path>")
            else:
                p = parts[1].strip()
                if not p.startswith("/"):
                    p = "/" + p
                print(format_resolve(LOADER.resolve(p)))
            print(); continue
        history.append({"role": "user", "content": query})
        agent_loop(history)
        content = history[-1]["content"]
        if isinstance(content, list):
            for block in content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
