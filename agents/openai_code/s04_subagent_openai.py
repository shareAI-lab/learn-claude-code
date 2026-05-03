#!/usr/bin/env python3
# Harness: context isolation -- protecting the model's clarity of thought.
"""
s04_subagent.py - Subagents

Spawn a child agent with fresh messages=[]. The child works in its own
context, sharing the filesystem, then returns only a summary to the parent.

    Parent agent                     Subagent
    +------------------+             +------------------+
    | messages=[...]   |             | messages=[]      |  <-- fresh
    |                  |  dispatch   |                  |
    | tool: task       | ---------->| while tool_use:  |
    |   prompt="..."   |            |   call tools     |
    |   description="" |            |   append results |
    |                  |  summary   |                  |
    |   result = "..." | <--------- | return last text |
    +------------------+             +------------------+
              |
    Parent context stays clean.
    Subagent context is discarded.

Key insight: "Process isolation gives context isolation for free."
"""

import json
import os
import subprocess
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

import sys
load_dotenv(override=True)
# 在文件开头设置
os.environ['PYTHONPATH'] = r"E:\ai_pycode\learn-claude-code-main"
sys.path.insert(0, r"E:\ai_pycode\learn-claude-code-main")


# 尽量让控制台输出按 utf-8 编码，避免 Windows 默认编码导致的编码异常。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WORKDIR = Path.cwd()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
MODEL = os.environ.get("OPENAI_MODEL_ID")

SYSTEM = f"You are a coding agent at {WORKDIR}. Use the task tool to delegate exploration or subtasks."
SUBAGENT_SYSTEM = f"You are a coding subagent at {WORKDIR}. Complete the given task, then summarize your findings."


# -- Tool implementations shared by parent and child --
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
        # Windows 下 subprocess(text=True) 默认编码可能是 gbk，遇到非 gbk 字节会解码失败。
        # 这里强制 utf-8 并用 errors='replace' 保证 stdout/stderr 至少是字符串。
        if sys.platform == "win32":
            r = subprocess.run(
                command,
                shell=True,
                cwd=WORKDIR,
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="backslashreplace",
            )
        else:
            r = subprocess.run(
                command,
                shell=True,
                cwd=WORKDIR,
                capture_output=True,
                text=True,
                timeout=120,
                executable="/bin/bash",
                encoding="utf-8",
                errors="backslashreplace",
            )

        stdout = r.stdout or ""
        stderr = r.stderr or ""
        out = (stdout + stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"

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


TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
}

# Child gets all base tools except task (no recursive spawning)
CHILD_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace exact text in file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
]


# -- Subagent: fresh context, filtered tools, summary-only return --
def run_subagent(prompt: str) -> str:
    # fresh context: system+user only
    sub_messages = [
        {"role": "system", "content": SUBAGENT_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    last_assistant_content = "(no summary)"

    for _ in range(30):  # safety limit
        response = client.chat.completions.create(
            model=MODEL,
            messages=sub_messages,
            tools=CHILD_TOOLS,
            tool_choice="auto",
            max_tokens=8000,
            temperature=0.7,
        )
        assistant_message = response.choices[0].message
        last_assistant_content = assistant_message.content or last_assistant_content

        sub_messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": assistant_message.tool_calls,
            }
        )
        if not assistant_message.tool_calls:
            break

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            handler = TOOL_HANDLERS.get(tool_name)
            output = handler(**args) if handler else f"Unknown tool: {tool_name}"

            sub_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(output)[:50000],
                }
            )

    # Only the final text returns to the parent -- child context is discarded
    return last_assistant_content


# -- Parent tools: base tools + task dispatcher --
PARENT_TOOLS = CHILD_TOOLS + [
    {
        "type": "function",
        "function": {
            "name": "task",
            "description": "Spawn a subagent with fresh context. It shares the filesystem but not conversation history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["prompt"],
            },
        },
    },
]


def agent_loop(messages: list):
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM}, *messages],
            tools=PARENT_TOOLS,
            tool_choice="auto",
            max_tokens=8000,
            temperature=0.7,
        )
        assistant_message = response.choices[0].message
        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": assistant_message.tool_calls,
            }
        )
        if not assistant_message.tool_calls:
            return
        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            if tool_name == "task":
                desc = args.get("description", "subtask")
                prompt = args.get("prompt", "")
                print(f"> task ({desc}): {prompt[:80]}")
                output = run_subagent(prompt)
            else:
                handler = TOOL_HANDLERS.get(tool_name)
                output = handler(**args) if handler else f"Unknown tool: {tool_name}"

            print(f"  {str(output)[:200]}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(output)[:50000],
                }
            )
# 其实还可以弄一个机制，父agent能够指定分发给子agent的工具

if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms04 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        if history and history[-1]["role"] == "assistant" and history[-1].get("content"):
            print(history[-1]["content"])
        print()
