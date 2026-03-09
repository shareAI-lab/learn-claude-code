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
import json

from dotenv import load_dotenv

load_dotenv(override=True)

API_KEY = os.getenv("ANTHROPIC_API_KEY")
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
MODEL = os.environ["MODEL_ID"]

SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

TOOLS = [{
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
}]

def call_openai_api(messages: list, tools: list = None):
    import httpx
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 8000,
        "temperature": 0.5,
        "stream": False,
    }
    
    if tools:
        payload["tools"] = tools
    
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{BASE_URL}/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"[DEBUG] API Error: {e}")
        if hasattr(e, 'response'):
            print(f"[DEBUG] Response body: {e.response.text}")
        raise Exception(f"API call failed: {e}")


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
        response_data = call_openai_api(messages, TOOLS)
        
        choice = response_data["choices"][0]
        message = choice["message"]
        
        assistant_message = {"role": "assistant", "content": message.get("content", "")}
        
        if "tool_calls" in message:
            assistant_message["tool_calls"] = message["tool_calls"]
        
        messages.append(assistant_message)
        
        if choice["finish_reason"] != "tool_calls":
            return
        
        results = []
        for tool_call in message.get("tool_calls", []):
            function_name = tool_call["function"]["name"]
            if function_name == "bash":
                arguments = json.loads(tool_call["function"]["arguments"])
                command = arguments["command"]
                print(f"\033[33m$ {command}\033[0m")
                output = run_bash(command)
                print(output[:200])
                results.append({
                    "tool_call_id": tool_call["id"],
                    "role": "tool",
                    "content": output
                })
        
        if results:
            messages.extend(results)


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        
        messages = [{"role": "system", "content": SYSTEM}]
        messages.extend(history)
        messages.append({"role": "user", "content": query})
        
        agent_loop(messages)
        
        last_message = messages[-1]
        if last_message["role"] == "assistant" and last_message.get("content"):
            print(last_message["content"])
        
        history = [msg for msg in messages if msg["role"] != "system"]
        print()
