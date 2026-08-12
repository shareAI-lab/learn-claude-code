"""Synchronous, non-recursive subagent execution with explicit dependencies."""

from __future__ import annotations

from typing import Callable


TASK_TOOL_SCHEMA = {
    "name": "task",
    "description": "Launch a subagent to handle a complex subtask. Returns only the final conclusion.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Complete instructions sent verbatim to the subagent. This is the only accepted parameter.",
            }
        },
        "required": ["description"],
        "additionalProperties": False,
    },
}


def register_subagent_tool(registry, schemas: dict, handlers: dict) -> None:
    """Register the non-recursive synchronous subagent tool."""
    registry.register(schemas["task"], handlers.get("task"))


def extract_text(content) -> str:
    if not isinstance(content, list):
        return str(content)
    return "\n".join(
        getattr(block, "text", "")
        for block in content
        if getattr(block, "type", None) == "text"
    )


def has_tool_use(content) -> bool:
    return any(
        (block.get("type") if isinstance(block, dict) else getattr(block, "type", None))
        == "tool_use"
        for block in content
    )


def spawn_subagent(
    description: str,
    llm: Callable,
    config,
    system: str,
    tools: list[dict],
    handlers: dict,
    hooks,
) -> str:
    """Run a fresh, bounded subagent conversation using only supplied tools."""
    print("\n\033[35m[Subagent spawned]\033[0m")
    messages = [{"role": "user", "content": description}]

    for _ in range(30):
        try:
            response = llm(
                model=config.primary_model,
                system=system,
                messages=list(messages),
                tools=tools,
                max_tokens=config.default_max_tokens,
            )
        except Exception as exc:
            error = f"[Subagent error] {type(exc).__name__}: {str(exc)[:300]}"
            print(f"  \033[31m{error}\033[0m")
            return error
        messages.append({"role": "assistant", "content": response.content})
        if not has_tool_use(response.content):
            break
        results = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            blocked = hooks.trigger("PreToolUse", block)
            if blocked:
                results.append({
                    "type": "tool_result", "tool_use_id": block.id,
                    "content": str(blocked),
                })
                continue
            handler = handlers.get(block.name)
            output = handler(**block.input) if handler else f"Unknown: {block.name}"
            hooks.trigger("PostToolUse", block, output)
            print(f"  \033[90m[sub] {block.name}: {str(output)[:100]}\033[0m")
            results.append({
                "type": "tool_result", "tool_use_id": block.id,
                "content": output,
            })
        messages.append({"role": "user", "content": results})

    result = extract_text(messages[-1]["content"])
    if not result:
        for message in reversed(messages):
            result = extract_text(message["content"])
            if result:
                break
        if not result:
            result = "Subagent stopped after 30 turns without final answer."
    print("\033[35m[Subagent done]\033[0m")
    return result
