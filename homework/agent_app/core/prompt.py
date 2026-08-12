"""System prompt assembly with instance-owned caching."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime


PROMPT_SECTIONS = {
    "identity": "You are a coding agent. Act, don't explain.",
    "workspace": "Working directory: ",
    "tools": "Available tools: ",
}


def assemble_system_prompt(context: dict) -> str:
    sections = []
    sections.append(PROMPT_SECTIONS["identity"])
    sections.append(
        PROMPT_SECTIONS["tools"]
        + ", ".join(context.get("enabled_tools", []))
    )
    sections.append(
        PROMPT_SECTIONS["workspace"] + str(context.get("workspace", ""))
    )
    current_time = context.get("current_time")
    if not current_time:
        current_time = datetime.now().isoformat(timespec="seconds")
    sections.append(f"Current time: {current_time}")

    sections.append(
        "Coordination rules:\n"
        "- todo_write manages the temporary plan for the current session.\n"
        "- create_task manages the durable shared task graph.\n"
        "- task runs a synchronous one-shot subagent and waits for its result.\n"
        "- spawn_teammate starts an asynchronous persistent teammate.\n"
        "- A teammate that submits a plan must wait for Lead approval."
    )

    memories = context.get("memories", "")
    if memories:
        sections.append(f"Memory index:\n{memories}")

    skills = context.get("skills")
    if skills:
        sections.append(
            "Skills catalog:\n"
            f"{skills}\n"
            "Use load_skill(name) when a skill is relevant."
        )

    todos = context.get("todos", "")
    if todos:
        sections.append(f"Current session todos:\n{todos}")

    active_names = context.get("active_teammates", [])
    if active_names:
        sections.append(f"Active teammates:\n{', '.join(active_names)}")

    connect_mcp = context.get("connect_mcp", [])
    if connect_mcp:
        sections.append(
            f"Connected MCP servers:\n{', '.join(connect_mcp)}"
        )

    return "\n\n".join(sections)


@dataclass(slots=True)
class PromptBuilder:
    last_key: str | None = None
    last_prompt: str | None = None

    def build(self, context: dict) -> str:
        key = json.dumps(
            context,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        if key == self.last_key and self.last_prompt:
            print("  \033[90m[cache hit] system prompt unchanged\033[0m")
            return self.last_prompt

        self.last_key = key
        self.last_prompt = assemble_system_prompt(context)

        loaded = ["identity", "tools", "workspace"]
        if context.get("memories"):
            loaded.append("memory")
        if context.get("todos"):
            loaded.append("todos")
        print(
            f"  \033[32m[assembled] sections: {', '.join(loaded)}\033[0m"
        )
        return self.last_prompt
