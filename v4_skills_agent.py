#!/usr/bin/env python3
"""
v4_skills_agent.py - Mini Claude Code: Skills Mechanism

A modular agent architecture demonstrating:
    - Tools: Capabilities the model CAN use (bash, read, write, edit)
    - Skills: Knowledge the model KNOWS (loaded from SKILL.md files)
    - Agents: Subagents with isolated context for focused work
    - Streaming: Real-time token output for immediate feedback

Architecture:
    v4/
    ├── config.py   - Client, model, paths
    ├── tools.py    - Tool definitions and implementations
    ├── skills.py   - SkillLoader for domain expertise
    ├── todo.py     - TodoManager for task tracking
    └── agents.py   - Agent types, loop, streaming

Core Concepts:
--------------
1. Tools vs Skills
    | Concept | What it is              | Example                    |
    |---------|-------------------------|---------------------------|
    | Tool    | What model CAN do       | bash, read_file, write    |
    | Skill   | How model KNOWS to do   | PDF processing, MCP dev   |

2. Knowledge Externalization
    Traditional: Knowledge locked in model parameters (expensive to change)
    Skills: Knowledge in editable files (change in minutes, free)

3. Progressive Disclosure
    Layer 1: Metadata (~100 tokens/skill) - always loaded
    Layer 2: SKILL.md body (~2000 tokens) - loaded on demand
    Layer 3: Resources (unlimited) - referenced as needed

4. Context Isolation
    Subagents run in isolated context to prevent pollution.
    Parent sees only the summary, not intermediate details.

5. Streaming
    Text tokens print immediately as they arrive.
    Tool calls accumulate from deltas and execute after stream ends.

Usage:
    python v4_skills_agent.py
"""

from v4 import WORKDIR, SKILLS, AGENT_TYPES, agent_loop


def main():
    """Interactive REPL for the v4 agent."""
    print(f"Mini Claude Code v4 (with Skills) - {WORKDIR}")
    print(f"Skills: {', '.join(SKILLS.list_skills()) or 'none'}")
    print(f"Agent types: {', '.join(AGENT_TYPES.keys())}")
    print("Type 'exit' to quit.\n")

    history = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ("exit", "quit", "q"):
            break

        history.append({"role": "user", "content": user_input})

        try:
            agent_loop(history)
        except Exception as e:
            print(f"Error: {e}")

        print()


if __name__ == "__main__":
    main()
