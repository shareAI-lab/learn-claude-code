"""Tool execution and background-dispatch policy without application state."""

from __future__ import annotations


def is_slow_operation(tool_name: str, tool_input: dict) -> bool:
    if tool_name != "bash":
        return False
    command = tool_input.get("command", "").lower()
    slow_keywords = [
        "install",
        "build",
        "test",
        "deploy",
        "compile",
        "docker build",
        "pip install",
        "npm install",
        "cargo build",
        "pytest",
        "make",
    ]
    return any(keyword in command for keyword in slow_keywords)


def should_run_background(tool_name: str, tool_input: dict) -> bool:
    if tool_name != "bash":
        return False
    return bool(tool_input.get("run_in_background")) or is_slow_operation(
        tool_name, tool_input
    )


def execute_tool(block, handlers: dict) -> str:
    handler = handlers.get(block.name)
    if handler:
        return handler(**block.input)
    return f"Unknown tool: {block.name}"
