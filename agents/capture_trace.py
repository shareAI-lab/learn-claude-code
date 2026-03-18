#!/usr/bin/env python3
"""
capture_trace.py - Capture API request/response traces from agent sessions.

Usage:
    python agents/capture_trace.py s01 "Create a file called hello.py that prints Hello World"
    python agents/capture_trace.py s02 "List files in the current directory and show disk usage"

Output:  web/src/data/traces/s01.json (etc.)
"""

import importlib
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(override=True)

TRACE_DIR = PROJECT_ROOT / "web" / "src" / "data" / "traces"

SESSION_FILES = {
    "s01": "s01_agent_loop",
    "s02": "s02_tool_use",
    "s03": "s03_todo_write",
    "s04": "s04_subagent",
    "s05": "s05_skill_loading",
    "s06": "s06_context_compact",
    "s07": "s07_task_system",
    "s08": "s08_background_tasks",
    "s09": "s09_agent_teams",
    "s10": "s10_team_protocols",
    "s11": "s11_autonomous_agents",
    "s12": "s12_worktree_task_isolation",
}


def _serialize(obj) -> object:
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if hasattr(obj, "__dict__"):
        return _serialize(vars(obj))
    return str(obj)


def _serialize_block(block) -> dict:
    if hasattr(block, "type"):
        if block.type == "text":
            return {"type": "text", "text": block.text}
        elif block.type == "tool_use":
            return {
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": _serialize(block.input),
            }
    return {"type": "unknown", "raw": str(block)}


def capture_session(session_id: str, user_prompt: str) -> list[dict]:
    if session_id not in SESSION_FILES:
        print(f"Unknown session: {session_id}")
        print(f"Available: {', '.join(sorted(SESSION_FILES))}")
        sys.exit(1)

    mod = importlib.import_module(f"agents.{SESSION_FILES[session_id]}")

    cycles: list[dict] = []
    original_create = mod.client.messages.create

    def intercepted_create(**kwargs):
        cycle_num = len(cycles) + 1

        request_data = {k: _serialize(v) for k, v in kwargs.items()}

        t0 = time.time()
        response = original_create(**kwargs)
        elapsed_ms = int((time.time() - t0) * 1000)

        response_data = {
            "id": response.id,
            "type": response.type,
            "role": response.role,
            "model": response.model,
            "stop_reason": response.stop_reason,
            "content": [_serialize_block(b) for b in response.content],
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }

        cycle = {
            "cycle": cycle_num,
            "elapsed_ms": elapsed_ms,
            "request": request_data,
            "response": response_data,
            "tool_executions": [],
        }
        cycles.append(cycle)
        return response

    patches = []

    tool_handlers = getattr(mod, "TOOL_HANDLERS", None) or getattr(mod, "TOOLS_MAP", None)
    original_handlers = {}

    if tool_handlers and isinstance(tool_handlers, dict):
        original_handlers = dict(tool_handlers)

        def make_interceptor(name, handler):
            def interceptor(**kw):
                result = handler(**kw)
                if cycles:
                    cycles[-1]["tool_executions"].append({
                        "name": name,
                        "input": _serialize(kw),
                        "output": str(result)[:5000],
                    })
                return result
            return interceptor

        for name, handler in original_handlers.items():
            tool_handlers[name] = make_interceptor(name, handler)
    elif hasattr(mod, "run_bash"):
        original_run_bash = mod.run_bash

        def patched_run_bash(command: str) -> str:
            result = original_run_bash(command)
            if cycles:
                cycles[-1]["tool_executions"].append({
                    "name": "bash",
                    "input": {"command": command},
                    "output": str(result)[:5000],
                })
            return result

        patches.append(patch.object(mod, "run_bash", side_effect=patched_run_bash))

    for p in patches:
        p.start()

    with patch.object(mod.client.messages, "create", side_effect=intercepted_create):
        messages = [{"role": "user", "content": user_prompt}]
        try:
            mod.agent_loop(messages)
        except Exception as e:
            print(f"Agent loop ended with: {e}")

    for p in patches:
        p.stop()

    if tool_handlers and isinstance(tool_handlers, dict):
        for name, handler in original_handlers.items():
            tool_handlers[name] = handler

    return cycles


def save_trace(session_id: str, cycles: list[dict], user_prompt: str):
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = TRACE_DIR / f"{session_id}.json"

    trace = {
        "version": session_id,
        "prompt": user_prompt,
        "model": os.environ.get("MODEL_ID", "unknown"),
        "total_cycles": len(cycles),
        "total_input_tokens": sum(c["response"]["usage"]["input_tokens"] for c in cycles),
        "total_output_tokens": sum(c["response"]["usage"]["output_tokens"] for c in cycles),
        "cycles": cycles,
    }

    out_path.write_text(json.dumps(trace, indent=2, ensure_ascii=False))
    print(f"\nTrace saved: {out_path}")
    print(f"  Cycles: {len(cycles)}")
    print(f"  Tokens: {trace['total_input_tokens']} in / {trace['total_output_tokens']} out")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python agents/capture_trace.py <session_id> <prompt>")
        print('Example: python agents/capture_trace.py s01 "Create hello.py"')
        sys.exit(1)

    session = sys.argv[1]
    prompt = sys.argv[2]

    print(f"Capturing trace for {session}...")
    print(f"Prompt: {prompt}\n")

    trace_cycles = capture_session(session, prompt)
    save_trace(session, trace_cycles, prompt)
