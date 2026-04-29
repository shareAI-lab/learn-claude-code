#!/usr/bin/env python3
# Harness: the pieces -- what an LLM API call is, before we wrap it in a loop.
"""
s00_agent_intro.py - The Agent, One Piece at a Time

Four tiny, self-contained demos. Each one adds exactly one concept:

    demo 1: hello_model     -- one API call. messages in, message out.
    demo 2: multi_turn      -- the model has no memory. you pass the history.
    demo 3: offer_a_tool    -- give the model a tool. it replies with a request to call it.
    demo 4: run_and_return  -- run the tool yourself, feed the result back, ask again.

s01 is just these four pieces wrapped in a `while`. Run a demo with:

    python agents/s00_agent_intro.py 1
"""

import json
import os
import subprocess
import sys

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", ""),
    base_url=os.environ["OPENAI_BASE_URL"],
)
MODEL = os.environ["MODEL_ID"]

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


def dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


# ANSI colors -- make the live demo readable at a glance.
CYAN_BOLD = "\033[1;36m"
MAGENTA_BOLD = "\033[1;35m"
RESET = "\033[0m"


def header(title: str) -> None:
    print(f"{MAGENTA_BOLD}--- {title} ---{RESET}")


def user_says(text: str) -> None:
    print(f"{CYAN_BOLD}USER:{RESET} {CYAN_BOLD}{text}{RESET}")


# ---------------------------------------------------------------------------
# demo 1: hello_model -- one API call. messages in, message out.
# ---------------------------------------------------------------------------
def demo_1_hello_model() -> None:
    header("demo 1: hello_model")
    user_text = "Say hello in one sentence."
    user_says(user_text)
    messages = [{"role": "user", "content": user_text}]

    print(">>> sending messages:")
    print(dump(messages))

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=200,
    )

    print(">>> model replied:")
    print(dump(response.choices[0].message.model_dump()))


# ---------------------------------------------------------------------------
# demo 2: multi_turn -- the model has no memory. you pass the history.
# ---------------------------------------------------------------------------
def demo_2_multi_turn() -> None:
    header("demo 2: multi_turn")
    turn_1 = "My name is Fred. Remember it."
    turn_2 = "What name did I tell you?"

    user_says(turn_1)
    messages = [{"role": "user", "content": turn_1}]

    r1 = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=200)
    reply1 = r1.choices[0].message
    print(">>> turn 1 reply:")
    print(dump(reply1.model_dump()))

    # Grow the history: append the assistant's reply, then the next user turn.
    messages.append({"role": "assistant", "content": reply1.content})
    user_says(turn_2)
    messages.append({"role": "user", "content": turn_2})
    print(">>> turn 2 messages (full history goes back every time):")
    print(dump(messages))

    r2 = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=200)
    print(">>> turn 2 reply:")
    print(dump(r2.choices[0].message.model_dump()))


# ---------------------------------------------------------------------------
# demo 3: offer_a_tool -- the model replies with tool_calls, not content.
# ---------------------------------------------------------------------------
def demo_3_offer_a_tool() -> None:
    header("demo 3: offer_a_tool")
    user_text = "What files are in the current directory?"
    user_says(user_text)
    messages = [{"role": "user", "content": user_text}]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        max_tokens=200,
    )

    print(">>> model replied (note: content is empty, tool_calls is populated):")
    print(dump(response.choices[0].message.model_dump()))
    print(f">>> finish_reason: {response.choices[0].finish_reason}")


# ---------------------------------------------------------------------------
# demo 4: run_and_return -- we run the tool, feed the result back, call again.
# ---------------------------------------------------------------------------
def demo_4_run_and_return() -> None:
    header("demo 4: run_and_return")
    user_text = "What files are in the current directory?"
    user_says(user_text)
    messages = [{"role": "user", "content": user_text}]

    r1 = client.chat.completions.create(
        model=MODEL, messages=messages, tools=TOOLS, max_tokens=200,
    )
    assistant_msg = r1.choices[0].message
    print(">>> model asked us to call a tool:")
    print(dump(assistant_msg.model_dump()))

    # Append the assistant's tool-call message to history.
    messages.append({
        "role": "assistant",
        "content": assistant_msg.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in assistant_msg.tool_calls
        ],
    })

    # Run each tool call locally and append one "tool" message per call_id.
    for tc in assistant_msg.tool_calls:
        args = json.loads(tc.function.arguments)
        output = run_bash(args["command"])
        print(f">>> ran: {args['command']}")
        print(output[:500])
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": output,
        })

    # Call the model again. Now it has the tool output and can answer in prose.
    r2 = client.chat.completions.create(
        model=MODEL, messages=messages, tools=TOOLS, max_tokens=400,
    )
    print(">>> model's final reply:")
    print(dump(r2.choices[0].message.model_dump()))


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------
DEMOS = {
    "1": ("hello_model",    demo_1_hello_model,    "one API call: messages in, message out"),
    "2": ("multi_turn",     demo_2_multi_turn,     "the model has no memory; you pass the history"),
    "3": ("offer_a_tool",   demo_3_offer_a_tool,   "the model replies with a tool request, not an answer"),
    "4": ("run_and_return", demo_4_run_and_return, "run the tool, feed the result back, call again"),
}


def print_menu() -> None:
    print("usage: python agents/s00_agent_intro.py <demo>")
    print()
    for key, (name, _, desc) in DEMOS.items():
        print(f"  {key}  {name:<16} - {desc}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg not in DEMOS:
        print_menu()
        sys.exit(0 if arg is None else 1)
    DEMOS[arg][1]()
