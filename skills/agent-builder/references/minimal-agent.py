#!/usr/bin/env python3
"""
Minimal Agent Template - Copy and customize this.

This is the simplest possible working agent (~80 lines).
It has everything you need: 3 tools + loop.

Usage:
    1. Set ANTHROPIC_API_KEY environment variable
    2. python minimal-agent.py
    3. Type commands, 'q' to quit
"""

from anthropic import Anthropic
from pathlib import Path
import subprocess
import os

# Configuration
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")
WORKDIR = Path.cwd()

# System prompt - keep it simple
SYSTEM = f"""You are a coding agent at {WORKDIR}.

Rules:
- Use tools to complete tasks
- Prefer action over explanation
- Summarize what you did when done"""

# Minimal tool set - add more as needed
TOOLS = [
    {
        "name": "bash",
        "description": "Run shell command",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"]
        }
    },
    {
        "name": "read_file",
        "description": "Read file contents",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
]


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return result."""
    if name == "bash":
        try:
            r = subprocess.run(
                args["command"], shell=True, cwd=WORKDIR,
                capture_output=True, text=True, timeout=60
            )
            return (r.stdout + r.stderr).strip() or "(empty)"
        except subprocess.TimeoutExpired:
            return "Error: Timeout"

    if name == "read_file":
        try:
            return (WORKDIR / args["path"]).read_text()[:50000]
        except Exception as e:
            return f"Error: {e}"

    if name == "write_file":
        try:
            p = WORKDIR / args["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["content"])
            return f"Wrote {len(args['content'])} bytes to {args['path']}"
        except Exception as e:
            return f"Error: {e}"

    return f"Unknown tool: {name}"


def agent(prompt: str, history: list = None) -> str:
    """Run the agent loop."""
    if history is None:
        history = []

    history.append({"role": "user", "content": prompt})

    while True:
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=history,
            tools=TOOLS,
            max_tokens=8000,
        )

        # Build assistant message
        history.append({"role": "assistant", "content": response.content})

        # If no tool calls, return text
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if hasattr(b, "text"))

        # Execute tools
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"> {block.name}: {block.input}")
                output = execute_tool(block.name, block.input)
                print(f"  {output[:100]}...")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output
                })

        history.append({"role": "user", "content": results})


if __name__ == "__main__":
    print(f"Minimal Agent - {WORKDIR}")
    print("Type 'q' to quit.\n")

    history = []
    while True:
        try:
            query = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if query in ("q", "quit", "exit", ""):
            break
        print(agent(query, history))
        print()
