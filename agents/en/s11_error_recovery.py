#!/usr/bin/env python3
# Harness: resilience -- a robust agent recovers instead of crashing.
"""
s11_error_recovery.py - Error Recovery

Teaching demo of three recovery paths:

- continue when output is truncated
- compact when context grows too large
- back off when transport errors are temporary

    LLM response
         |
         v
    [Check stop_reason]
         |
         +-- "max_tokens" ----> [Strategy 1: max_output_tokens recovery]
         |                       Inject continuation message:
         |                       "Output limit hit. Continue directly."
         |                       Retry up to MAX_RECOVERY_ATTEMPTS (3).
         |                       Counter: max_output_recovery_count
         |
         +-- API error -------> [Check error type]
         |                       |
         |                       +-- prompt_too_long --> [Strategy 2: compact + retry]
         |                       |   Trigger auto_compact (LLM summary).
         |                       |   Replace history with summary.
         |                       |   Retry the turn.
         |                       |
         |                       +-- connection/rate --> [Strategy 3: backoff retry]
         |                           Exponential backoff: base * 2^attempt + jitter
         |                           Up to 3 retries.
         |
         +-- "end_turn" -----> [Normal exit]

    Recovery priority (first match wins):
    1. max_tokens -> inject continuation, retry
    2. prompt_too_long -> compact, retry
    3. connection error -> backoff, retry
    4. all retries exhausted -> fail gracefully
"""

import json
import os
import random
import subprocess
import time
from pathlib import Path

from anthropic import Anthropic, APIError
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

# Recovery constants
MAX_RECOVERY_ATTEMPTS = 3
BACKOFF_BASE_DELAY = 1.0  # seconds
BACKOFF_MAX_DELAY = 30.0  # seconds
TOKEN_THRESHOLD = 50000   # chars / 4 ~ tokens for compact trigger

CONTINUATION_MESSAGE = (
    "Output limit hit. Continue directly from where you stopped -- "
    "no recap, no repetition. Pick up mid-sentence if needed."
)


def estimate_tokens(messages: list) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(json.dumps(messages, default=str)) // 4


def auto_compact(messages: list) -> list:
    """
    Compress conversation history into a short continuation summary.
    """
    conversation_text = json.dumps(messages, default=str)[:80000]
    prompt = (
        "Summarize this conversation for continuity. Include:\n"
        "1) Task overview and success criteria\n"
        "2) Current state: completed work, files touched\n"
        "3) Key decisions and failed approaches\n"
        "4) Remaining next steps\n"
        "Be concise but preserve critical details.\n\n"
        + conversation_text
    )
    try:
        response = client.messages.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )
        summary = response.content[0].text
    except Exception as e:
        summary = f"(compact failed: {e}). Previous context lost."

    continuation = (
        "This session continues from a previous conversation that was compacted. "
        f"Summary of prior context:\n\n{summary}\n\n"
        "Continue from where we left off without re-asking the user."
    )
    return [{"role": "user", "content": continuation}]


def backoff_delay(attempt: int) -> float:
    """Exponential backoff with jitter: base * 2^attempt + random(0, 1)."""
    delay = min(BACKOFF_BASE_DELAY * (2 ** attempt), BACKOFF_MAX_DELAY)
    jitter = random.uniform(0, 1)
    return delay + jitter


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

TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
]

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks."


def agent_loop(messages: list):
    """
    Error-recovering agent loop with three paths:

    1. continue after max_tokens
    2. compact after prompt-too-long
    3. back off after transient transport failure
    """
    max_output_recovery_count = 0

    while True:
        # -- Attempt the API call with connection retry --
        response = None
        for attempt in range(MAX_RECOVERY_ATTEMPTS + 1):
            try:
                response = client.messages.create(
                    model=MODEL, system=SYSTEM, messages=messages,
                    tools=TOOLS, max_tokens=8000,
                )
                break  # success

            except APIError as e:
                error_body = str(e).lower()

                # Strategy 2: prompt_too_long -> compact and retry
                if "overlong_prompt" in error_body or ("prompt" in error_body and "long" in error_body):
                    print(f"[Recovery] Prompt too long. Compacting... (attempt {attempt + 1})")
                    messages[:] = auto_compact(messages)
                    continue

                # Strategy 3: connection/rate errors -> backoff
                if attempt < MAX_RECOVERY_ATTEMPTS:
                    delay = backoff_delay(attempt)
                    print(f"[Recovery] API error: {e}. "
                          f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RECOVERY_ATTEMPTS})")
                    time.sleep(delay)
                    continue

                # All retries exhausted
                print(f"[Error] API call failed after {MAX_RECOVERY_ATTEMPTS} retries: {e}")
                return

            except (ConnectionError, TimeoutError, OSError) as e:
                # Strategy 3: network-level errors -> backoff
                if attempt < MAX_RECOVERY_ATTEMPTS:
                    delay = backoff_delay(attempt)
                    print(f"[Recovery] Connection error: {e}. "
                          f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RECOVERY_ATTEMPTS})")
                    time.sleep(delay)
                    continue

                print(f"[Error] Connection failed after {MAX_RECOVERY_ATTEMPTS} retries: {e}")
                return

        if response is None:
            print("[Error] No response received.")
            return

        messages.append({"role": "assistant", "content": response.content})

        # -- Strategy 1: max_tokens recovery --
        if response.stop_reason == "max_tokens":
            max_output_recovery_count += 1
            if max_output_recovery_count <= MAX_RECOVERY_ATTEMPTS:
                print(f"[Recovery] max_tokens hit "
                      f"({max_output_recovery_count}/{MAX_RECOVERY_ATTEMPTS}). "
                      "Injecting continuation...")
                messages.append({"role": "user", "content": CONTINUATION_MESSAGE})
                continue  # retry the loop
            else:
                print(f"[Error] max_tokens recovery exhausted "
                      f"({MAX_RECOVERY_ATTEMPTS} attempts). Stopping.")
                return

        # Reset max_tokens counter on successful non-max_tokens response
        max_output_recovery_count = 0

        # -- Normal end_turn: no tool use requested --
        if response.stop_reason != "tool_use":
            return

        # -- Process tool calls --
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            handler = TOOL_HANDLERS.get(block.name)
            try:
                output = handler(**(block.input or {})) if handler else f"Unknown: {block.name}"
            except Exception as e:
                output = f"Error: {e}"
            print(f"> {block.name}: {str(output)[:200]}")
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(output),
            })

        messages.append({"role": "user", "content": results})

        # Check if we should auto-compact (proactive, not just reactive)
        if estimate_tokens(messages) > TOKEN_THRESHOLD:
            print("[Recovery] Token estimate exceeds threshold. Auto-compacting...")
            messages[:] = auto_compact(messages)


if __name__ == "__main__":
    print("[Error recovery enabled: max_tokens / prompt_too_long / connection backoff]")
    history = []
    while True:
        try:
            query = input("\033[36ms11 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
