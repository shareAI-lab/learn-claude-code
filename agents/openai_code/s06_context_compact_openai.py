#!/usr/bin/env python3
# Harness: compression -- clean memory for infinite sessions.
"""
s06_subagent_openai.py - Compact (OpenAI version)

OpenAI adaptation of s06_context_compact.py.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

# Keep imports stable when running from this directory
os.environ["PYTHONPATH"] = r"E:\ai_pycode\learn-claude-code-main"
sys.path.insert(0, r"E:\ai_pycode\learn-claude-code-main")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WORKDIR = Path.cwd()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
MODEL = os.environ.get("OPENAI_MODEL_ID") or os.environ.get("MODEL_ID")

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks."

THRESHOLD = 50000
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
KEEP_RECENT = 3
PRESERVE_RESULT_TOOLS = {"read_file"}

# 估计token数量：每个token大约4个字符
def estimate_tokens(messages: list) -> int:
    """Rough token count: ~4 chars per token."""
    return len(str(messages)) // 4


# -- Layer 1: micro_compact - replace old tool results with placeholders --
def micro_compact(messages: list) -> list:
    # Collect all tool messages.
    tool_results = []
    for idx, msg in enumerate(messages):
        if msg.get("role") == "tool":
            tool_results.append((idx, msg))

    if len(tool_results) <= KEEP_RECENT:
        return messages

    # Build tool_call_id -> tool_name map from assistant tool_calls.
    tool_name_map = {}
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        tool_calls = msg.get("tool_calls") or []
        if not isinstance(tool_calls, list):
            continue
        for call in tool_calls:
            try:
                call_id = call.get("id")
                fn = call.get("function") or {}
                name = fn.get("name", "unknown")
                if call_id:
                    tool_name_map[call_id] = name
            except Exception:
                continue

    to_clear = tool_results[:-KEEP_RECENT]
    for _, result in to_clear:
        content = result.get("content")
        if not isinstance(content, str) or len(content) <= 100:
            continue
        tool_call_id = result.get("tool_call_id", "")
        tool_name = tool_name_map.get(tool_call_id, "unknown")
        if tool_name in PRESERVE_RESULT_TOOLS:
            continue
        result["content"] = f"[Previous: used {tool_name}]"

    return messages


# -- Layer 2: auto_compact - save transcript, summarize, replace messages --
def auto_compact(messages: list) -> list:
    TRANSCRIPT_DIR.mkdir(exist_ok=True)
    transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w", encoding="utf-8", errors="backslashreplace") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False, default=str) + "\n")
    print(f"[transcript saved: {transcript_path}]")

    conversation_text = json.dumps(messages, ensure_ascii=False, default=str)[-80000:]
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    "Summarize this conversation for continuity. Include: "
                    "1) What was accomplished, 2) Current state, 3) Key decisions made. "
                    "Be concise but preserve critical details.\n\n" + conversation_text
                ),
            }
        ],
        max_tokens=2000,
        temperature=0.3,
    )
    summary = response.choices[0].message.content or "No summary generated."

    return [
        {
            "role": "user",
            "content": f"[Conversation compressed. Transcript: {transcript_path}]\n\n{summary}",
        }
    ]


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
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except Exception as e:
        return f"Error: {e}"


def run_read(path: str, limit: int = None) -> str:
    try:
        lines = safe_path(path).read_text(encoding="utf-8", errors="backslashreplace").splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8", errors="backslashreplace")
        return f"Wrote {len(content)} bytes"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text(encoding="utf-8", errors="backslashreplace")
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1), encoding="utf-8", errors="backslashreplace")
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


TOOL_HANDLERS = {
    "bash": lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "compact": lambda **kw: "Manual compression requested.",
}

TOOLS = [
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
                "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
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
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
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
    {
        "type": "function",
        "function": {
            "name": "compact",
            "description": "Trigger manual conversation compression.",
            "parameters": {
                "type": "object",
                "properties": {"focus": {"type": "string", "description": "What to preserve in the summary"}},
            },
        },
    },
]


def agent_loop(messages: list):
    while True:
        micro_compact(messages)
        if estimate_tokens(messages) > THRESHOLD:
            print("[auto_compact triggered]")
            messages[:] = auto_compact(messages)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM}, *messages],
            tools=TOOLS,
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

        manual_compact = False
        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            if tool_name == "compact":
                manual_compact = True
                output = "Compressing..."
            else:
                handler = TOOL_HANDLERS.get(tool_name)
                try:
                    output = handler(**args) if handler else f"Unknown tool: {tool_name}"
                except Exception as e:
                    output = f"Error: {e}"

            print(f"> {tool_name}:")
            print(str(output)[:200])
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": str(output)})

        if manual_compact:
            print("[manual compact]")
            messages[:] = auto_compact(messages)
            return


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms06 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        if history and history[-1].get("role") == "assistant" and history[-1].get("content"):
            print(history[-1]["content"])
        print()

