"""
v4 - Mini Claude Code: Modular Agent Architecture

Package Structure:
    config.py   - Client, model, paths configuration
    tools.py    - Tool definitions and implementations
    skills.py   - SkillLoader for domain expertise
    todo.py     - TodoManager for task tracking
    agents.py   - Agent types, loop, and subagents
"""

from .config import client, MODEL, WORKDIR, SKILLS_DIR
from .tools import TOOLS, execute_tool
from .skills import SKILLS
from .todo import TODO
from .agents import agent_loop, AGENT_TYPES

__all__ = [
    "client",
    "MODEL",
    "WORKDIR",
    "SKILLS_DIR",
    "TOOLS",
    "execute_tool",
    "SKILLS",
    "TODO",
    "agent_loop",
    "AGENT_TYPES",
]
