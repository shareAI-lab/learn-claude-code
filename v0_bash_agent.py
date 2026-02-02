#!/usr/bin/env python
"""
v0_bash_agent.py - Mini Claude Code: Bash is All You Need (~50 lines core)

Core Philosophy: "Bash is All You Need"
======================================
This is the ULTIMATE simplification of a coding agent. After building v1-v3,
we ask: what is the ESSENCE of an agent?

The answer: ONE tool (bash) + ONE loop = FULL agent capability.

Why Bash is Enough:
------------------
Unix philosophy says everything is a file, everything can be piped.
Bash is the gateway to this world:

    | You need      | Bash command                           |
    |---------------|----------------------------------------|
    | Read files    | cat, head, tail, grep                  |
    | Write files   | echo '...' > file, cat << 'EOF' > file |
    | Search        | find, grep, rg, ls                     |
    | Execute       | python, npm, make, any command         |
    | **Subagent**  | python v0_bash_agent.py "task"         |

The last line is the KEY INSIGHT: calling itself via bash implements subagents!
No Task tool, no Agent Registry - just recursion through process spawning.

How Subagents Work:
------------------
    Main Agent
      |-- bash: python v0_bash_agent.py "analyze architecture"
           |-- Subagent (isolated process, fresh history)
                |-- bash: find . -name "*.py"
                |-- bash: cat src/main.py
                |-- Returns summary via stdout

Process isolation = Context isolation:
- Child process has its own history=[]
- Parent captures stdout as tool result
- Recursive calls enable unlimited nesting

Usage:
    # Interactive mode
    python v0_bash_agent.py

    # Subagent mode (called by parent agent or directly)
    python v0_bash_agent.py "explore src/ and summarize"
"""

from openai import OpenAI
from dotenv import load_dotenv
import json
import subprocess
import sys
import os

load_dotenv(override=True)

# Initialize OpenAI client (uses OPENAI_API_KEY and OPENAI_BASE_URL env vars)
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)
MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-5-20250929")

# The ONE tool that does everything
# Notice how the description teaches the model common patterns AND how to spawn subagents
TOOL = [{
    "type": "function",
    "function": {
        "name": "bash",
        "description": """Execute shell command. Common patterns:
- Read: cat/head/tail, grep/find/rg/ls, wc -l
- Write: echo 'content' > file, sed -i 's/old/new/g' file
- Subagent: python v0_bash_agent.py 'task description' (spawns isolated agent, returns summary)""",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"]
        }
    }
}]

# System prompt teaches the model HOW to use bash effectively
# Notice the subagent guidance - this is how we get hierarchical task decomposition
SYSTEM = f"""You are a CLI agent at {os.getcwd()}. Solve problems using bash commands.

Rules:
- Prefer tools over prose. Act first, explain briefly after.
- Read files: cat, grep, find, rg, ls, head, tail
- Write files: echo '...' > file, sed -i, or cat << 'EOF' > file
- Subagent: For complex subtasks, spawn a subagent to keep context clean:
  python v0_bash_agent.py "explore src/ and summarize the architecture"

When to use subagent:
- Task requires reading many files (isolate the exploration)
- Task is independent and self-contained
- You want to avoid polluting current conversation with intermediate details

The subagent runs in isolation and returns only its final summary."""


def chat(prompt, history=None):
    """
    The complete agent loop in ONE function.

    This is the core pattern that ALL coding agents share:
        while not done:
            response = model(messages, tools)
            if no tool calls: return
            execute tools, append results

    Args:
        prompt: User's request
        history: Conversation history (mutable, shared across calls in interactive mode)

    Returns:
        Final text response from the model
    """
    if history is None:
        history = []

    history.append({"role": "user", "content": prompt})

    while True:
        # 1. Call the model with tools
        messages = [{"role": "system", "content": SYSTEM}] + history
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL,
            max_tokens=8000
        )

        message = response.choices[0].message

        # 2. If model didn't call tools, we're done
        if not message.tool_calls:
            history.append({"role": "assistant", "content": message.content or ""})
            return message.content or ""

        # 3. Append assistant message with tool calls
        history.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in message.tool_calls
            ]
        })

        # 4. Execute each tool call and collect results
        for tc in message.tool_calls:
            args = json.loads(tc.function.arguments)
            cmd = args["command"]
            print(f"\033[33m$ {cmd}\033[0m")  # Yellow color for commands

            try:
                out = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=os.getcwd()
                )
                output = out.stdout + out.stderr
            except subprocess.TimeoutExpired:
                output = "(timeout after 300s)"

            print(output or "(empty)")
            # 5. Append results as tool messages
            history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": output[:50000]  # Truncate very long outputs
            })


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Subagent mode: execute task and print result
        # This is how parent agents spawn children via bash
        print(chat(sys.argv[1]))
    else:
        # Interactive REPL mode
        history = []
        while True:
            try:
                query = input("\033[36m>> \033[0m")  # Cyan prompt
            except (EOFError, KeyboardInterrupt):
                break
            if query in ("q", "exit", ""):
                break
            print(chat(query, history))
