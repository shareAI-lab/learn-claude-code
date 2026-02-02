#!/usr/bin/env python3
"""
Minimal Agent Template - Copy and customize this.

This is the simplest possible working agent (~80 lines).
It has everything you need: 3 tools + loop.

Usage:
    1. Set OPENAI_API_KEY environment variable
    2. python minimal-agent.py
    3. Type commands, 'q' to quit
"""

from openai import OpenAI
from pathlib import Path
import json
import subprocess
import os

# Configuration
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)
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
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run shell command",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
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
        messages = [{"role": "system", "content": SYSTEM}] + history
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )

        message = response.choices[0].message

        # If no tool calls, return text
        if not message.tool_calls:
            history.append({"role": "assistant", "content": message.content or ""})
            return message.content or ""

        # Build assistant message with tool calls
        history.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in message.tool_calls
            ]
        })

        # Execute tools
        for tc in message.tool_calls:
            args = json.loads(tc.function.arguments)
            print(f"> {tc.function.name}: {args}")
            output = execute_tool(tc.function.name, args)
            print(f"  {output[:100]}...")
            history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": output,
            })


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
