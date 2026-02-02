#!/usr/bin/env python3
"""
v1_basic_agent.py - Mini Claude Code: Model as Agent (~200 lines)

Core Philosophy: "The Model IS the Agent"
=========================================
The secret of Claude Code, Cursor Agent, Codex CLI? There is no secret.

Strip away the CLI polish, progress bars, permission systems. What remains
is surprisingly simple: a LOOP that lets the model call tools until done.

Traditional Assistant:
    User -> Model -> Text Response

Agent System:
    User -> Model -> [Tool -> Result]* -> Response
                          ^________|

The asterisk (*) matters! The model calls tools REPEATEDLY until it decides
the task is complete. This transforms a chatbot into an autonomous agent.

KEY INSIGHT: The model is the decision-maker. Code just provides tools and
runs the loop. The model decides:
  - Which tools to call
  - In what order
  - When to stop

The Four Essential Tools:
------------------------
Claude Code has ~20 tools. But these 4 cover 90% of use cases:

    | Tool       | Purpose              | Example                    |
    |------------|----------------------|----------------------------|
    | bash       | Run any command      | npm install, git status    |
    | read_file  | Read file contents   | View src/index.ts          |
    | write_file | Create/overwrite     | Create README.md           |
    | edit_file  | Surgical changes     | Replace a function         |

With just these 4 tools, the model can:
  - Explore codebases (bash: find, grep, ls)
  - Understand code (read_file)
  - Make changes (write_file, edit_file)
  - Run anything (bash: python, npm, make)

Usage:
    python v1_basic_agent.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)


# =============================================================================
# Configuration
# =============================================================================

WORKDIR = Path.cwd()
MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-5-20250929")
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)


# =============================================================================
# System Prompt - The only "configuration" the model needs
# =============================================================================

SYSTEM = f"""You are a coding agent at {WORKDIR}.

Loop: think briefly -> use tools -> report results.

Rules:
- Prefer tools over prose. Act, don't just explain.
- Never invent file paths. Use bash ls/find first if unsure.
- Make minimal changes. Don't over-engineer.
- After finishing, summarize what changed."""


# =============================================================================
# Tool Definitions - 4 tools cover 90% of coding tasks
# =============================================================================

TOOLS = [
    # Tool 1: Bash - The gateway to everything
    # Can run any command: git, npm, python, curl, etc.
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command. Use for: ls, find, grep, git, npm, python, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"],
            },
        },
    },

    # Tool 2: Read File - For understanding existing code
    # Returns file content with optional line limit for large files
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents. Returns UTF-8 text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max lines to read (default: all)"
                    },
                },
                "required": ["path"],
            },
        },
    },

    # Tool 3: Write File - For creating new files or complete rewrites
    # Creates parent directories automatically
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path for the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write"
                    },
                },
                "required": ["path", "content"],
            },
        },
    },

    # Tool 4: Edit File - For surgical changes to existing code
    # Uses exact string matching for precise edits
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace exact text in a file. Use for surgical edits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file"
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to find (must match precisely)"
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text"
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
]


# =============================================================================
# Tool Implementations
# =============================================================================

def safe_path(p: str) -> Path:
    """
    Ensure path stays within workspace (security measure).

    Prevents the model from accessing files outside the project directory.
    Resolves relative paths and checks they don't escape via '../'.
    """
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    """
    Execute shell command with safety checks.

    Security: Blocks obviously dangerous commands.
    Timeout: 60 seconds to prevent hanging.
    Output: Truncated to 50KB to prevent context overflow.
    """
    # Basic safety - block dangerous patterns
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=60
        )
        output = (result.stdout + result.stderr).strip()
        return output[:50000] if output else "(no output)"

    except subprocess.TimeoutExpired:
        return "Error: Command timed out (60s)"
    except Exception as e:
        return f"Error: {e}"


def run_read(path: str, limit: int = None) -> str:
    """
    Read file contents with optional line limit.

    For large files, use limit to read just the first N lines.
    Output truncated to 50KB to prevent context overflow.
    """
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()

        if limit and limit < len(lines):
            lines = lines[:limit]
            lines.append(f"... ({len(text.splitlines()) - limit} more lines)")

        return "\n".join(lines)[:50000]

    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    """
    Write content to file, creating parent directories if needed.

    This is for complete file creation/overwrite.
    For partial edits, use edit_file instead.
    """
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"

    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    """
    Replace exact text in a file (surgical edit).

    Uses exact string matching - the old_text must appear verbatim.
    Only replaces the first occurrence to prevent accidental mass changes.
    """
    try:
        fp = safe_path(path)
        content = fp.read_text()

        if old_text not in content:
            return f"Error: Text not found in {path}"

        # Replace only first occurrence for safety
        new_content = content.replace(old_text, new_text, 1)
        fp.write_text(new_content)
        return f"Edited {path}"

    except Exception as e:
        return f"Error: {e}"


def execute_tool(name: str, args: dict) -> str:
    """
    Dispatch tool call to the appropriate implementation.

    This is the bridge between the model's tool calls and actual execution.
    Each tool returns a string result that goes back to the model.
    """
    if name == "bash":
        return run_bash(args["command"])
    if name == "read_file":
        return run_read(args["path"], args.get("limit"))
    if name == "write_file":
        return run_write(args["path"], args["content"])
    if name == "edit_file":
        return run_edit(args["path"], args["old_text"], args["new_text"])
    return f"Unknown tool: {name}"


# =============================================================================
# The Agent Loop - This is the CORE of everything
# =============================================================================

def agent_loop(messages: list) -> list:
    """
    The complete agent in one function.

    This is the pattern that ALL coding agents share:

        while True:
            response = model(messages, tools)
            if no tool calls: return
            execute tools, append results, continue

    The model controls the loop:
      - Keeps calling tools until there are no more tool calls
      - Results become context (fed back as "tool" messages)
      - Memory is automatic (messages list accumulates history)

    Why this works:
      1. Model decides which tools, in what order, when to stop
      2. Tool results provide feedback for next decision
      3. Conversation history maintains context across turns
    """
    while True:
        # Step 1: Call the model
        api_messages = [{"role": "system", "content": SYSTEM}] + messages
        response = client.chat.completions.create(
            model=MODEL,
            messages=api_messages,
            tools=TOOLS,
            max_tokens=8000,
        )

        message = response.choices[0].message

        # Step 2: Print text output
        if message.content:
            print(message.content)

        # Step 3: If no tool calls, task is complete
        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content or ""})
            return messages

        # Step 4: Append assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in message.tool_calls
            ]
        })

        # Step 5: Execute each tool and collect results
        for tc in message.tool_calls:
            args = json.loads(tc.function.arguments)
            name = tc.function.name

            # Display what's being executed
            print(f"\n> {name}: {args}")

            # Execute and show result preview
            output = execute_tool(name, args)
            preview = output[:200] + "..." if len(output) > 200 else output
            print(f"  {preview}")

            # Append result as tool message
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": output,
            })


# =============================================================================
# Main REPL
# =============================================================================

def main():
    """
    Simple Read-Eval-Print Loop for interactive use.

    The history list maintains conversation context across turns,
    allowing multi-turn conversations with memory.
    """
    print(f"Mini Claude Code v1 - {WORKDIR}")
    print("Type 'exit' to quit.\n")

    history = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ("exit", "quit", "q"):
            break

        # Add user message to history
        history.append({"role": "user", "content": user_input})

        try:
            # Run the agent loop
            agent_loop(history)
        except Exception as e:
            print(f"Error: {e}")

        print()  # Blank line between turns


if __name__ == "__main__":
    main()
