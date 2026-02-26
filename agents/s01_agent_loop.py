#!/usr/bin/env python3
"""
s01_agent_loop.py - The Agent Loop

The entire secret of an AI coding agent in one pattern:

    while stop_reason == "tool_use":
        response = LLM(messages, tools)
        execute tools
        append results

    +----------+      +-------+      +---------+
    |   User   | ---> |  LLM  | ---> |  Tool   |
    |  prompt  |      |       |      | execute |
    +----------+      +---+---+      +----+----+
                          ^               |
                          |   tool_result |
                          +---------------+
                          (loop continues)

This is the core loop: feed tool results back to the model
until the model decides to stop. Production agents layer
policy, hooks, and lifecycle controls on top.
"""

import os
import subprocess

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

# Novita AI integration: use OpenAI-compatible API if NOVITA_API_KEY is set
if os.getenv("NOVITA_API_KEY"):
    from openai import OpenAI
    client = OpenAI(
        api_key=os.getenv("NOVITA_API_KEY"),
        base_url="https://api.novita.ai/openai",
    )
    use_novita = True
else:
    use_novita = False
    if os.getenv("ANTHROPIC_BASE_URL"):
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
    client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))

MODEL = os.environ["MODEL_ID"]

SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

TOOLS = [{
    "name": "bash",
    "description": "Run a shell command.",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
}]


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=os.getcwd(),
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


# -- The core pattern: a while loop that calls tools until the model stops --
def agent_loop(messages: list):
    while True:
        if use_novita:
            # Novita uses OpenAI-compatible API
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM}] + messages,
                tools=TOOLS,
                max_tokens=8000,
            )
            # Parse OpenAI-style response
            message = response.choices[0].message
            messages.append({"role": "assistant", "content": message.content,
                             "tool_calls": message.tool_calls})
            # If no tool calls, we're done
            if not message.tool_calls:
                return
            # Execute each tool call
            results = []
            for tc in message.tool_calls:
                print(f"\033[33m$ {tc.function.arguments}\033[0m")
                # Parse arguments (could be string or dict)
                args = tc.function.arguments
                if isinstance(args, str):
                    import json
                    args = json.loads(args)
                output = run_bash(args.get("command", ""))
                print(output[:200])
                results.append({"tool_call_id": tc.id, "content": output,
                                "type": "tool_result"})
            messages.append({"role": "user", "content": results})
        else:
            # Anthropic API
            response = client.messages.create(
                model=MODEL, system=SYSTEM, messages=messages,
                tools=TOOLS, max_tokens=8000,
            )
            # Append assistant turn
            messages.append({"role": "assistant", "content": response.content})
            # If the model didn't call a tool, we're done
            if response.stop_reason != "tool_use":
                return
            # Execute each tool call, collect results
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"\033[33m$ {block.input['command']}\033[0m")
                    output = run_bash(block.input["command"])
                    print(output[:200])
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": output})
            messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if use_novita:
            # OpenAI-style response
            if isinstance(response_content, dict):
                text = response_content.get("content")
                if text:
                    print(text)
        else:
            # Anthropic-style response
            if isinstance(response_content, list):
                for block in response_content:
                    if hasattr(block, "text"):
                        print(block.text)
        print()
