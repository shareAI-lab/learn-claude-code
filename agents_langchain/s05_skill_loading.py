#!/usr/bin/env python3
# LangChain track: on-demand knowledge -- discover skill summaries cheaply, load full bodies by tool.
"""
s05_skill_loading.py - Skills with LangChain

The two-layer model stays the same as the baseline: the system prompt contains a
cheap skill catalog, while the `load_skill` tool returns the full SKILL.md body
only when the model decides it is relevant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool

try:
    from agents_langchain._common import (
        WORKDIR,
        build_openai_chat_model,
        edit_file as edit_file_impl,
        latest_text,
        read_file as read_file_impl,
        run_bash,
        write_file as write_file_impl,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script fallback
    from _common import (
        WORKDIR,
        build_openai_chat_model,
        edit_file as edit_file_impl,
        latest_text,
        read_file as read_file_impl,
        run_bash,
        write_file as write_file_impl,
    )

SKILLS_DIR = WORKDIR / "skills"


@dataclass
class SkillManifest:
    name: str
    description: str
    path: Path


@dataclass
class SkillDocument:
    manifest: SkillManifest
    body: str


class SkillRegistry:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.documents: dict[str, SkillDocument] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not self.skills_dir.exists():
            return
        for path in sorted(self.skills_dir.rglob("SKILL.md")):
            meta, body = self._parse_frontmatter(path.read_text())
            name = meta.get("name", path.parent.name)
            description = meta.get("description", "No description")
            manifest = SkillManifest(name=name, description=description, path=path)
            self.documents[name] = SkillDocument(manifest=manifest, body=body.strip())

    def _parse_frontmatter(self, text: str) -> tuple[dict[str, str], str]:
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text

        meta: dict[str, str] = {}
        for line in match.group(1).strip().splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
        return meta, match.group(2)

    def describe_available(self) -> str:
        if not self.documents:
            return "(no skills available)"
        return "\n".join(
            f"- {doc.manifest.name}: {doc.manifest.description}"
            for _, doc in sorted(self.documents.items())
        )

    def load_full_text(self, name: str) -> str:
        document = self.documents.get(name)
        if not document:
            known = ", ".join(sorted(self.documents)) or "(none)"
            return f"Error: Unknown skill '{name}'. Available skills: {known}"
        return f"<skill name=\"{document.manifest.name}\">\n{document.body}\n</skill>"


SKILL_REGISTRY = SkillRegistry(SKILLS_DIR)

SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use load_skill when a task needs specialized instructions before you act.

Skills available:
{SKILL_REGISTRY.describe_available()}
"""


@tool
def bash(command: str) -> str:
    """Run a shell command in the current workspace."""

    return run_bash(command)


@tool
def read_file(path: str, limit: int | None = None) -> str:
    """Read file contents from the workspace, optionally limiting lines."""

    return read_file_impl(path, limit)


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a workspace file."""

    return write_file_impl(path, content)


@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace one exact text occurrence in a workspace file."""

    return edit_file_impl(path, old_text, new_text)


@tool
def load_skill(name: str) -> str:
    """Load the full body of a named skill into the current context."""

    return SKILL_REGISTRY.load_full_text(name)


TOOLS = [bash, read_file, write_file, edit_file, load_skill]


def build_agent():
    return create_agent(build_openai_chat_model(), tools=TOOLS, system_prompt=SYSTEM)


def invoke_agent(agent: Any, messages: list[Any], query: str) -> list[Any]:
    result = agent.invoke({"messages": [*messages, {"role": "user", "content": query}]})
    return list(result["messages"])


if __name__ == "__main__":
    agent = build_agent()
    history: list[Any] = []
    while True:
        try:
            query = input("\033[36mlc-s05 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history = invoke_agent(agent, history, query)
        print(latest_text(history))
        print()
