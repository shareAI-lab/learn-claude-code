#!/usr/bin/env python3
# Harness: the loop -- keep feeding real tool results back into the model.
"""
s01_agent_loop.py - The Agent Loop

This file teaches the smallest useful coding-agent pattern:

    user message
      -> model reply
      -> if tool_use: execute tools
      -> write tool_result back to messages
      -> continue

It intentionally keeps the loop small, but still makes the loop state explicit
so later chapters can grow from the same structure.
"""

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime

try:
    import readline
    # #143 UTF-8 backspace fix for macOS libedit
    readline.parse_and_bind('set bind-tty-special-chars off')
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
    readline.parse_and_bind('set convert-meta off')
    readline.parse_and_bind('set enable-meta-keybindings on')
except ImportError:
    pass

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", ""),
    base_url=os.environ["OPENAI_BASE_URL"],
)
MODEL = os.environ["MODEL_ID"]

# ANSI colors -- make the live demo readable at a glance.
YELLOW = "\033[33m"
GREEN = "\033[32m"
MAGENTA_BOLD = "\033[1;35m"
DIM = "\033[2m"
RESET = "\033[0m"

# Full message history is too noisy for the terminal; stream it to a log file
# so you can `tail -f history.log` in another pane during the workshop.
# The raw file contains the full `state.messages` list as JSON, overwritten
# after every exchange, for anyone who wants to inspect the exact API shapes.
HISTORY_LOG = "history.log"
HISTORY_RAW_LOG = "history.raw.log"


def log_history(label: str, body: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    with open(HISTORY_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] --- {label} ---\n")
        f.write((body.rstrip() or "(empty)") + "\n\n")


def dump_raw_history(messages: list) -> None:
    with open(HISTORY_RAW_LOG, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)
        f.write("\n")


SYSTEM = (
    f"You are a coding agent at {os.getcwd()}. "
    "Use bash to inspect and change the workspace. Act first, then report clearly."
)

TOOLS = [{
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command in the current workspace.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
}]


@dataclass
class LoopState:
    # The minimal loop state: history, loop count, and why we continue.
    messages: list
    turn_count: int = 1
    transition_reason: str | None = None


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(item in command for item in dangerous):
        return "Error: Dangerous command blocked"
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"

    output = (result.stdout + result.stderr).strip()
    return output[:50000] if output else "(no output)"


def execute_tool_calls(tool_calls) -> list[dict]:
    results = []
    for tc in tool_calls:
        args = json.loads(tc.function.arguments)
        command = args["command"]
        print(f"{YELLOW}$ {command}{RESET}")
        output = run_bash(command)
        print(f"{DIM}{output[:200]}{RESET}")
        log_history(f"tool ({tc.function.name})", output)
        results.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": output,
        })
    return results


def run_one_turn(state: LoopState) -> bool:
    print(f"{MAGENTA_BOLD}--- turn {state.turn_count} ---{RESET}")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM}] + state.messages,
        tools=TOOLS,
        max_tokens=8000,
    )
    choice = response.choices[0]
    msg = choice.message

    # Build the assistant message dict for history
    assistant_msg = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        assistant_msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ]
    state.messages.append(assistant_msg)

    # Show the assistant's prose (if any) so the demo isn't silent between tool calls.
    if msg.content and msg.content.strip():
        print(f"{GREEN}{msg.content.strip()}{RESET}")

    # Log the assistant turn: prose first, then any tool requests as separate lines.
    body_lines = []
    if msg.content and msg.content.strip():
        body_lines.append(msg.content.strip())
    if msg.tool_calls:
        for tc in msg.tool_calls:
            body_lines.append(f"[tool_call] {tc.function.name}({tc.function.arguments})")
    log_history(f"assistant (turn {state.turn_count})", "\n".join(body_lines))

    if choice.finish_reason != "tool_calls" or not msg.tool_calls:
        state.transition_reason = None
        return False

    results = execute_tool_calls(msg.tool_calls)
    if not results:
        state.transition_reason = None
        return False

    state.messages.extend(results)
    state.turn_count += 1
    state.transition_reason = "tool_result"
    return True


def agent_loop(state: LoopState) -> None:
    while run_one_turn(state):
        pass


if __name__ == "__main__":
    # Fresh logs each session so `tail -f history.log` starts clean.
    open(HISTORY_LOG, "w").close()
    open(HISTORY_RAW_LOG, "w").close()

    history = []
    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        log_history("user", query)
        history.append({"role": "user", "content": query})
        state = LoopState(messages=history)
        agent_loop(state)
        dump_raw_history(state.messages)
        print()
