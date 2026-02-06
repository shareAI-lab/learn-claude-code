"""
Agent types, subagent execution, and main agent loop.

Agents follow the AGENT.md standard:
    agents/
    └── explore/
        └── AGENT.md    # YAML frontmatter + system prompt

AGENT.md Format:
    ---
    name: explore
    description: Read-only agent for exploring code.
    tools:
      - bash
      - read_file
    ---
    # System Prompt
    You are an exploration agent...

Subagents run in ISOLATED context - they don't see parent's history.
This prevents context pollution and enables focused work.

Streaming:
    Text tokens are printed in real-time as they arrive.
    Tool call deltas are accumulated and executed after stream completes.
"""

import json
import re
import sys
import time
from pathlib import Path

from .config import client, MODEL, WORKDIR
from .skills import SKILLS
from .tools import BASE_TOOLS, SKILL_TOOL, TOOLS, execute_tool, register_tool


# =============================================================================
# AgentLoader - Load agent definitions from AGENT.md files
# =============================================================================

class AgentLoader:
    """
    Loads agent type definitions from AGENT.md files.

    Each agent is a FOLDER containing:
    - AGENT.md (required): YAML frontmatter with config + markdown system prompt

    The YAML frontmatter defines the agent:
    - name: Agent type name
    - description: What the agent does
    - tools: List of allowed tools (or "*" for all)
    """

    def __init__(self, agents_dir: Path):
        self.agents_dir = agents_dir
        self.agents = {}
        self.load_agents()

    def parse_agent_md(self, path: Path) -> dict:
        """
        Parse an AGENT.md file into agent definition.

        Returns dict with: name, description, tools, prompt
        Returns None if file doesn't match format.
        """
        content = path.read_text()

        # Match YAML frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            return None

        frontmatter, body = match.groups()

        # Parse YAML-like frontmatter
        metadata = self._parse_yaml(frontmatter)

        # Require name and description
        if "name" not in metadata or "description" not in metadata:
            return None

        # Get tools list (default to all)
        tools = metadata.get("tools", "*")
        if isinstance(tools, dict):
            tools = list(tools.keys())

        return {
            "name": metadata["name"],
            "description": metadata["description"],
            "tools": tools,
            "prompt": body.strip(),
            "path": path,
        }

    def _parse_yaml(self, text: str) -> dict:
        """Simple YAML parser for agent frontmatter."""
        result = {}
        current_key = None
        in_list = False
        list_items = []

        for line in text.split("\n"):
            if not line.strip() or line.strip().startswith("#"):
                continue

            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            # Handle list items
            if stripped.startswith("- "):
                value = stripped[2:].strip()
                if in_list:
                    list_items.append(value)
                continue

            # Handle key: value pairs
            if ":" in stripped:
                # Save previous list if any
                if in_list and current_key:
                    result[current_key] = list_items
                    in_list = False
                    list_items = []

                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()

                if value:
                    # Simple key: value
                    result[key] = value
                else:
                    # Key with nested content (assume list)
                    current_key = key
                    in_list = True
                    list_items = []

        # Save final list if any
        if in_list and current_key:
            result[current_key] = list_items

        return result

    def load_agents(self):
        """Scan agents directory and load all valid AGENT.md files."""
        if not self.agents_dir.exists():
            return

        for agent_dir in self.agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue

            agent_md = agent_dir / "AGENT.md"
            if not agent_md.exists():
                continue

            agent = self.parse_agent_md(agent_md)
            if agent:
                self.agents[agent["name"]] = agent

    def get_agent(self, name: str) -> dict:
        """Get agent definition by name."""
        return self.agents.get(name)

    def get_descriptions(self) -> str:
        """Generate agent type descriptions for system prompt."""
        if not self.agents:
            return "(no agents available)"

        return "\n".join(
            f"- {name}: {agent['description']}"
            for name, agent in self.agents.items()
        )

    def list_agents(self) -> list:
        """Return list of available agent names."""
        return list(self.agents.keys())


# =============================================================================
# Initialize Agent Loader
# =============================================================================

AGENTS_DIR = WORKDIR / "agents"
AGENT_LOADER = AgentLoader(AGENTS_DIR)

# Fallback agent types if AGENT.md files not found
FALLBACK_AGENT_TYPES = {
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

# Build AGENT_TYPES from loader or fallbacks
AGENT_TYPES = {}
for name in ["explore", "code", "plan"]:
    agent = AGENT_LOADER.get_agent(name)
    if agent:
        AGENT_TYPES[name] = {
            "description": agent["description"],
            "tools": agent["tools"],
            "prompt": agent["prompt"],
        }
    elif name in FALLBACK_AGENT_TYPES:
        AGENT_TYPES[name] = FALLBACK_AGENT_TYPES[name]

# Add any additional agents from loader
for name, agent in AGENT_LOADER.agents.items():
    if name not in AGENT_TYPES:
        AGENT_TYPES[name] = {
            "description": agent["description"],
            "tools": agent["tools"],
            "prompt": agent["prompt"],
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

    # Build system prompt from agent definition
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
            tc_args = json.loads(tc.function.arguments)
            output = execute_tool(tc.function.name, tc_args)
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
            tc_args = json.loads(tc["function"]["arguments"])

            # Special display for different tool types
            if name == "Task":
                print(f"\n> Task: {tc_args.get('description', 'subtask')}")
            elif name == "Skill":
                print(f"\n> Loading skill: {tc_args.get('skill', '?')}")
            else:
                print(f"\n> {name}")

            output = execute_tool(name, tc_args)

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
