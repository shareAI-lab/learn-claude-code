#!/usr/bin/env python3
# Deep Agents track: safety -- the pipeline between intent and execution.
"""
s07_permission_system.py - Permission System with Deep Agents

Deep Agents can pause for human approval with `interrupt_on`, but this chapter
keeps the earlier lesson visible: every tool call still passes through an
explicit permission pipeline before execution.

Teaching pipeline:
  1. bash validation
  2. deny rules
  3. mode check
  4. allow rules
  5. ask user / block

Key insight: "Safety is a pipeline, not a boolean."
"""

from __future__ import annotations

import json
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Callable

from langchain.tools import tool

try:
    from ._deepagents_gating import build_stage_agent
    from .common import WORKDIR, build_openai_model, extract_text
    from ._common import read_file as raw_read_file
    from ._common import write_file as raw_write_file
    from ._common import edit_file as raw_edit_file
    from ._common import run_bash as raw_bash
except ImportError:
    from _deepagents_gating import build_stage_agent
    from common import WORKDIR, build_openai_model, extract_text
    from _common import read_file as raw_read_file
    from _common import write_file as raw_write_file
    from _common import edit_file as raw_edit_file
    from _common import run_bash as raw_bash

MODES = ("default", "plan", "auto")
READ_ONLY_TOOLS = {"read_file", "bash_readonly"}
WRITE_TOOLS = {"write_file", "edit_file", "bash"}

SYSTEM = f"""You are a coding agent at {WORKDIR}.
Respect the permission pipeline before executing tools.
Read-only work is easier to approve than writes."""


class BashSecurityValidator:
    """Detect obviously risky shell patterns before execution."""

    VALIDATORS = [
        ("shell_metachar", r"[;&|`$]"),
        ("sudo", r"\bsudo\b"),
        ("rm_rf", r"\brm\s+(-[a-zA-Z]*)?r"),
        ("cmd_substitution", r"\$\("),
        ("ifs_injection", r"\bIFS\s*="),
    ]

    def validate(self, command: str) -> list[tuple[str, str]]:
        failures: list[tuple[str, str]] = []
        for name, pattern in self.VALIDATORS:
            if re.search(pattern, command):
                failures.append((name, pattern))
        return failures

    def describe_failures(self, command: str) -> str:
        failures = self.validate(command)
        if not failures:
            return "No issues detected"
        return "Security flags: " + ", ".join(
            f"{name} (pattern: {pattern})" for name, pattern in failures
        )


bash_validator = BashSecurityValidator()

DEFAULT_RULES = [
    {"tool": "bash", "content": "rm -rf /", "behavior": "deny"},
    {"tool": "bash", "content": "sudo *", "behavior": "deny"},
    {"tool": "read_file", "path": "*", "behavior": "allow"},
]


class PermissionManager:
    def __init__(self, mode: str = "default", rules: list[dict[str, str]] | None = None):
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}. Choose from {MODES}")
        self.mode = mode
        self.rules = list(rules or DEFAULT_RULES)
        self.consecutive_denials = 0
        self.max_consecutive_denials = 3

    def _matches(self, rule: dict[str, str], tool_name: str, tool_input: dict[str, Any]) -> bool:
        if rule.get("tool") and rule["tool"] != "*" and rule["tool"] != tool_name:
            return False
        if "path" in rule and rule["path"] != "*":
            path = str(tool_input.get("path", ""))
            if not fnmatch(path, rule["path"]):
                return False
        if "content" in rule:
            command = str(tool_input.get("command", ""))
            if not fnmatch(command, rule["content"]):
                return False
        return True

    def check(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, str]:
        if tool_name == "bash":
            command = str(tool_input.get("command", ""))
            failures = bash_validator.validate(command)
            if failures:
                severe_hits = [f for f in failures if f[0] in {"sudo", "rm_rf"}]
                desc = bash_validator.describe_failures(command)
                if severe_hits:
                    return {"behavior": "deny", "reason": f"Bash validator: {desc}"}
                return {"behavior": "ask", "reason": f"Bash validator flagged: {desc}"}

        for rule in self.rules:
            if rule["behavior"] == "deny" and self._matches(rule, tool_name, tool_input):
                return {"behavior": "deny", "reason": f"Blocked by deny rule: {rule}"}

        if self.mode == "plan":
            if tool_name in WRITE_TOOLS:
                return {"behavior": "deny", "reason": "Plan mode: write operations are blocked"}
            return {"behavior": "allow", "reason": "Plan mode: read-only allowed"}

        if self.mode == "auto" and (tool_name in READ_ONLY_TOOLS or tool_name == "read_file"):
            return {"behavior": "allow", "reason": "Auto mode: read-only tool auto-approved"}

        for rule in self.rules:
            if rule["behavior"] == "allow" and self._matches(rule, tool_name, tool_input):
                self.consecutive_denials = 0
                return {"behavior": "allow", "reason": f"Matched allow rule: {rule}"}

        return {"behavior": "ask", "reason": f"No rule matched for {tool_name}, asking user"}

    def ask_user(self, tool_name: str, tool_input: dict[str, Any]) -> bool:
        preview = json.dumps(tool_input, ensure_ascii=False)[:200]
        try:
            answer = input(f"\n[Permission] {tool_name}: {preview}\nAllow? (y/n/always): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False

        if answer == "always":
            self.rules.append({"tool": tool_name, "path": "*", "behavior": "allow"})
            self.consecutive_denials = 0
            return True
        if answer in {"y", "yes"}:
            self.consecutive_denials = 0
            return True

        self.consecutive_denials += 1
        return False


PERMISSIONS = PermissionManager()


def _authorized(tool_name: str, tool_input: dict[str, Any]) -> tuple[bool, str]:
    decision = PERMISSIONS.check(tool_name, tool_input)
    behavior = decision["behavior"]
    if behavior == "allow":
        return True, decision["reason"]
    if behavior == "deny":
        return False, f"Permission denied: {decision['reason']}"
    if PERMISSIONS.ask_user(tool_name, tool_input):
        return True, f"Approved after prompt: {decision['reason']}"
    return False, f"Permission rejected: {decision['reason']}"


@tool
def bash(command: str) -> str:
    """Run a shell command after the permission pipeline approves it."""
    allowed, reason = _authorized("bash", {"command": command})
    if not allowed:
        return reason
    output = raw_bash(command)
    return output if reason.startswith("Matched") or reason.startswith("Auto") else f"{reason}\n{output}"


@tool
def read_file(path: str, limit: int | None = None) -> str:
    """Read file contents after the permission pipeline approves the request."""
    allowed, reason = _authorized("read_file", {"path": path, "limit": limit})
    if not allowed:
        return reason
    output = raw_read_file(path, limit)
    return output if reason.startswith("Matched") or reason.startswith("Auto") else f"{reason}\n{output}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file after the permission pipeline approves the request."""
    allowed, reason = _authorized("write_file", {"path": path, "content": content})
    if not allowed:
        return reason
    output = raw_write_file(path, content)
    return output if reason.startswith("Matched") or reason.startswith("Auto") else f"{reason}\n{output}"


@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace exact text in a file after the permission pipeline approves it."""
    allowed, reason = _authorized(
        "edit_file", {"path": path, "old_text": old_text, "new_text": new_text}
    )
    if not allowed:
        return reason
    output = raw_edit_file(path, old_text, new_text)
    return output if reason.startswith("Matched") or reason.startswith("Auto") else f"{reason}\n{output}"


TOOLS = [bash, read_file, write_file, edit_file]


def build_agent(mode: str = "default"):
    global PERMISSIONS
    PERMISSIONS = PermissionManager(mode=mode)
    return build_stage_agent(
        "s07",
        model=build_openai_model(),
        tools=TOOLS,
        system_prompt=SYSTEM,
    )


def agent_loop(messages: list[dict[str, Any]], mode: str = "default") -> str:
    result = build_agent(mode).invoke({"messages": messages})
    text = extract_text(result["messages"][-1].content)
    if text:
        messages.append({"role": "assistant", "content": text})
    return text


if __name__ == "__main__":
    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input("\033[36ms07-da >> \033[0m")
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
