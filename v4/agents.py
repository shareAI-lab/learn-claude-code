"""
Agent types, subagent execution, and main agent loop.

Agent Types:
    explore - Read-only for searching and analyzing
    code    - Full access for implementation
    plan    - Read-only for design and planning

Subagents run in ISOLATED context - they don't see parent's history.
This prevents context pollution and enables focused work.

Streaming:
    Text tokens are printed in real-time as they arrive.
    Tool call deltas are accumulated and executed after stream completes.
"""

import json
import sys
import time

from .config import client, MODEL, WORKDIR
from .skills import SKILLS
from .tools import BASE_TOOLS, SKILL_TOOL, TOOLS, execute_tool, register_tool


# =============================================================================
# Agent Type Registry
# =============================================================================

AGENT_TYPES = {
    "explore": {
        "description": "Read-only agent for exploring code, finding files, searching",
        "tools": ["bash", "read_file"],
        "prompt": "You are an exploration agent. Search and analyze, but never modify files. Return a concise summary.",
    },
    "code": {
        "description": "Full agent for implementing features and fixing bugs",
        "tools": "*",
        "prompt": "You are a coding agent. Implement the requested changes efficiently.",
    },
    "plan": {
        "description": "Planning agent for designing implementation strategies",
        "tools": ["bash", "read_file"],
        "prompt": "You are a planning agent. Analyze the codebase and output a numbered implementation plan. Do NOT make changes.",
    },
}


def get_agent_descriptions() -> str:
    """Generate agent type descriptions for system prompt."""
    return "\n".join(
        f"- {name}: {cfg['description']}"
        for name, cfg in AGENT_TYPES.items()
    )


def get_tools_for_agent(agent_type: str) -> list:
    """Filter tools based on agent type."""
    allowed = AGENT_TYPES.get(agent_type, {}).get("tools", "*")
    if allowed == "*":
        return BASE_TOOLS
    return [t for t in BASE_TOOLS if t["function"]["name"] in allowed]


# =============================================================================
# System Prompt
# =============================================================================

SYSTEM = f"""You are a coding agent at {WORKDIR}.

Loop: plan -> act with tools -> report.

**Skills available** (invoke with Skill tool when task matches):
{SKILLS.get_descriptions()}

**Subagents available** (invoke with Task tool for focused subtasks):
{get_agent_descriptions()}

Rules:
- Use Skill tool IMMEDIATELY when a task matches a skill description
- Use Task tool for subtasks needing focused exploration or implementation
- Use TodoWrite to track multi-step work
- Prefer tools over prose. Act, don't just explain.
- After finishing, summarize what changed."""


# =============================================================================
# Task Tool (Subagent)
# =============================================================================

TASK_TOOL = {
    "type": "function",
    "function": {
        "name": "Task",
        "description": f"Spawn a subagent for a focused subtask.\n\nAgent types:\n{get_agent_descriptions()}",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Short task description (3-5 words)"
                },
                "prompt": {
                    "type": "string",
                    "description": "Detailed instructions for the subagent"
                },
                "agent_type": {
                    "type": "string",
                    "enum": list(AGENT_TYPES.keys())
                },
            },
            "required": ["description", "prompt", "agent_type"],
        },
    },
}


def run_task(args: dict) -> str:
    """Execute a subagent task with isolated context."""
    description = args["description"]
    prompt = args["prompt"]
    agent_type = args["agent_type"]

    if agent_type not in AGENT_TYPES:
        return f"Error: Unknown agent type '{agent_type}'"

    config = AGENT_TYPES[agent_type]
    sub_system = f"""You are a {agent_type} subagent at {WORKDIR}.

{config["prompt"]}

Complete the task and return a clear, concise summary."""

    sub_tools = get_tools_for_agent(agent_type)
    sub_messages = [
        {"role": "system", "content": sub_system},
        {"role": "user", "content": prompt},
    ]

    print(f"  [{agent_type}] {description}")
    start = time.time()
    tool_count = 0

    # Subagent loop (non-streaming for simplicity)
    last_message = None
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=sub_messages,
            tools=sub_tools,
            max_tokens=8000,
        )

        last_message = response.choices[0].message

        if not last_message.tool_calls:
            break

        sub_messages.append({
            "role": "assistant",
            "content": last_message.content,
            "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in last_message.tool_calls
            ]
        })

        for tc in last_message.tool_calls:
            tool_count += 1
            args = json.loads(tc.function.arguments)
            output = execute_tool(tc.function.name, args)
            sub_messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": output,
            })

            elapsed = time.time() - start
            sys.stdout.write(
                f"\r  [{agent_type}] {description} ... {tool_count} tools, {elapsed:.1f}s"
            )
            sys.stdout.flush()

    elapsed = time.time() - start
    sys.stdout.write(
        f"\r  [{agent_type}] {description} - done ({tool_count} tools, {elapsed:.1f}s)\n"
    )

    return last_message.content or "(subagent returned no text)"


# Register Task tool handler
register_tool("Task", run_task)

# Add Task tool to the full tool list
ALL_TOOLS = TOOLS + [TASK_TOOL]


# =============================================================================
# Streaming Support
# =============================================================================

def collect_stream(stream):
    """
    Consume a streaming response, printing text tokens in real-time
    and accumulating tool call deltas.

    OpenAI streaming sends tool calls as incremental fragments:
        chunk 1: tool_calls=[{index=0, id="call_abc", function={name="bash", arguments=""}}]
        chunk 2: tool_calls=[{index=0, function={arguments='{"com'}}]
        ...

    Returns:
        (content, tool_calls) where tool_calls is a list of dicts
    """
    content = ""
    tool_calls_acc = {}

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if not delta:
            continue

        # Stream text content token-by-token
        if delta.content:
            sys.stdout.write(delta.content)
            sys.stdout.flush()
            content += delta.content

        # Accumulate tool call deltas
        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index

                if idx not in tool_calls_acc:
                    tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}

                if tc_delta.id:
                    tool_calls_acc[idx]["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        tool_calls_acc[idx]["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        tool_calls_acc[idx]["arguments"] += tc_delta.function.arguments

    # Newline after streamed text
    if content:
        print()

    # Convert accumulated tool calls to list sorted by index
    tool_calls = []
    for idx in sorted(tool_calls_acc.keys()):
        tc = tool_calls_acc[idx]
        tool_calls.append({
            "id": tc["id"],
            "type": "function",
            "function": {
                "name": tc["name"],
                "arguments": tc["arguments"],
            }
        })

    return content, tool_calls


# =============================================================================
# Main Agent Loop
# =============================================================================

def agent_loop(messages: list) -> list:
    """
    Main agent loop with streaming output.

    Text tokens are printed in real-time as they arrive from the API.
    Tool calls are accumulated from stream deltas, then executed after
    the stream completes.
    """
    while True:
        api_messages = [{"role": "system", "content": SYSTEM}] + messages
        stream = client.chat.completions.create(
            model=MODEL,
            messages=api_messages,
            tools=ALL_TOOLS,
            max_tokens=8000,
            stream=True,
        )

        content, tool_calls = collect_stream(stream)

        if not tool_calls:
            messages.append({"role": "assistant", "content": content or ""})
            return messages

        messages.append({
            "role": "assistant",
            "content": content or None,
            "tool_calls": tool_calls,
        })

        for tc in tool_calls:
            name = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])

            # Special display for different tool types
            if name == "Task":
                print(f"\n> Task: {args.get('description', 'subtask')}")
            elif name == "Skill":
                print(f"\n> Loading skill: {args.get('skill', '?')}")
            else:
                print(f"\n> {name}")

            output = execute_tool(name, args)

            # Skill tool shows summary, not full content
            if name == "Skill":
                print(f"  Skill loaded ({len(output)} chars)")
            elif name != "Task":
                preview = output[:200] + "..." if len(output) > 200 else output
                print(f"  {preview}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": output,
            })
