from __future__ import annotations

from pathlib import Path

from langchain.tools import ToolRuntime, tool

from coding_deepgent.skills.loader import load_local_skill
from coding_deepgent.skills.schemas import LoadSkillInput


@tool(
    "load_skill",
    args_schema=LoadSkillInput,
    description="Load a local coding-deepgent skill by name. Does not load extension, MCP, remote, or distributed skills.",
)
def load_skill(name: str, runtime: ToolRuntime) -> str:
    """Load one local skill body after explicit model request."""

    context = runtime.context
    workdir = Path(getattr(context, "workdir", Path.cwd()))
    skill_dir = Path(getattr(context, "skill_dir", "skills"))
    return load_local_skill(workdir=workdir, skill_dir=skill_dir, name=name).render()
