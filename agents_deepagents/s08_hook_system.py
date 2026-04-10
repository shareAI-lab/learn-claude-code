#!/usr/bin/env python3
# Deep Agents track: extensibility -- inject behavior without rewriting the loop.
"""
s08_hook_system.py - Hook System with Deep Agents middleware

This chapter maps the original hook idea onto LangChain/Deep Agents middleware:
- SessionStart -> before_agent
- PreToolUse -> wrap_tool_call before handler
- PostToolUse -> wrap_tool_call after handler

Key insight: "Extend the agent without touching the loop."
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from langchain.agents.middleware.types import AgentMiddleware
from langchain.messages import HumanMessage, ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command

try:
    from ._deepagents_gating import build_stage_agent
    from .common import WORKDIR, build_openai_model, extract_text
    from ._common import run_bash as raw_bash, read_file as raw_read_file, write_file as raw_write_file, edit_file as raw_edit_file
except ImportError:
    from _deepagents_gating import build_stage_agent
    from common import WORKDIR, build_openai_model, extract_text
    from _common import run_bash as raw_bash, read_file as raw_read_file, write_file as raw_write_file, edit_file as raw_edit_file

HOOK_EVENTS = ("SessionStart", "PreToolUse", "PostToolUse")
HOOK_TIMEOUT = 30
TRUST_MARKER = WORKDIR / ".claude" / ".claude_trusted"
SYSTEM = f"You are a coding agent at {WORKDIR}. Hooks may extend behavior around tool execution."


class HookManager:
    def __init__(self, config_path: Path | None = None, sdk_mode: bool = False):
        self.hooks = {event: [] for event in HOOK_EVENTS}
        self._sdk_mode = sdk_mode
        path = config_path or (WORKDIR / ".hooks.json")
        if path.exists():
            try:
                config = json.loads(path.read_text())
                for event in HOOK_EVENTS:
                    self.hooks[event] = config.get("hooks", {}).get(event, [])
            except Exception:
                pass

    def _trusted(self) -> bool:
        return self._sdk_mode or TRUST_MARKER.exists()

    def run_hooks(self, event: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        result = {"blocked": False, "messages": []}
        if not self._trusted():
            return result
        for hook_def in self.hooks.get(event, []):
            matcher = hook_def.get("matcher")
            if matcher and context and matcher not in {"*", context.get("tool_name", "")}:
                continue
            command = hook_def.get("command", "")
            if not command:
                continue
            env = dict()
            if context:
                env.update(
                    {
                        "HOOK_EVENT": event,
                        "HOOK_TOOL_NAME": context.get("tool_name", ""),
                        "HOOK_TOOL_INPUT": json.dumps(context.get("tool_input", {}), ensure_ascii=False)[:10000],
                        "HOOK_TOOL_OUTPUT": str(context.get("tool_output", ""))[:10000],
                    }
                )
            proc = subprocess.run(
                command,
                shell=True,
                cwd=WORKDIR,
                env={**dict(__import__('os').environ), **env},
                capture_output=True,
                text=True,
                timeout=HOOK_TIMEOUT,
            )
            if proc.returncode == 1:
                result["blocked"] = True
                result["block_reason"] = proc.stderr.strip() or "Blocked by hook"
            elif proc.returncode == 2 and proc.stderr.strip():
                result["messages"].append(proc.stderr.strip())
        return result


HOOKS = HookManager(sdk_mode=True)


class HookMiddleware(AgentMiddleware):
    def before_agent(self, state, runtime):
        start = HOOKS.run_hooks("SessionStart")
        if start["messages"]:
            return {"messages": [HumanMessage("\n".join(start["messages"]))]}
        return None

    def wrap_tool_call(self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], ToolMessage | Command]):
        pre = HOOKS.run_hooks(
            "PreToolUse",
            {"tool_name": request.tool_call["name"], "tool_input": request.tool_call.get("args", {})},
        )
        if pre["blocked"]:
            return ToolMessage(
                content=pre.get("block_reason", "Blocked by hook"),
                tool_call_id=request.tool_call["id"],
                name=request.tool_call["name"],
                status="error",
            )
        result = handler(request)
        if isinstance(result, ToolMessage):
            post = HOOKS.run_hooks(
                "PostToolUse",
                {
                    "tool_name": request.tool_call["name"],
                    "tool_input": request.tool_call.get("args", {}),
                    "tool_output": result.content,
                },
            )
            if post["blocked"]:
                return ToolMessage(
                    content=post.get("block_reason", "Blocked by hook"),
                    tool_call_id=request.tool_call["id"],
                    name=request.tool_call["name"],
                    status="error",
                )
            extra = [*pre["messages"], *post["messages"]]
            if extra:
                return ToolMessage(
                    content="\n".join([*extra, str(result.content)]),
                    tool_call_id=result.tool_call_id,
                    name=result.name,
                    status=result.status,
                )
        return result


from langchain.tools import tool

@tool
def bash(command: str) -> str:
    """Run a shell command in the workspace."""
    return raw_bash(command)

@tool
def read_file(path: str, limit: int | None = None) -> str:
    """Read file contents from the workspace."""
    return raw_read_file(path, limit)

@tool
def write_file(path: str, content: str) -> str:
    """Write content to a workspace file."""
    return raw_write_file(path, content)

@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace exact text in a workspace file."""
    return raw_edit_file(path, old_text, new_text)

TOOLS = [bash, read_file, write_file, edit_file]


def build_agent():
    return build_stage_agent(
        "s08",
        model=build_openai_model(),
        tools=TOOLS,
        system_prompt=SYSTEM,
        extra_middleware=[HookMiddleware()],
    )


def agent_loop(messages: list[dict[str, Any]]) -> str:
    result = build_agent().invoke({"messages": messages})
    text = extract_text(result["messages"][-1].content)
    if text:
        messages.append({"role": "assistant", "content": text})
    return text


if __name__ == "__main__":
    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input("\033[36ms08-da >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        try:
            print(agent_loop(history) or "(no response)")
        except RuntimeError as exc:
            print(f"Error: {exc}")
        print()
