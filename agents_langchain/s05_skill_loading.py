#!/usr/bin/env python3
# LangChain track: on-demand knowledge -- discover light, load deep.
"""
s05_skill_loading.py - Skills with LangChain

The skill registry remains normal Python harness state.  LangChain sees a small
catalog in the system prompt and can call ``load_skill`` to fetch the full body
only when needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .common import (
        WORKDIR,
        bash,
        create_agent_runtime,
        edit_file,
        extract_text,
        invoke_and_append,
        read_file,
        write_file,
    )
except ImportError:
    from common import (
        WORKDIR,
        bash,
        create_agent_runtime,
        edit_file,
        extract_text,
        invoke_and_append,
        read_file,
        write_file,
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
    def __init__(self, skills_dir: Path) -> None:
        self.skills_dir = skills_dir
        self.documents: dict[str, SkillDocument] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not self.skills_dir.exists():
            return
        for path in sorted(self.skills_dir.rglob("SKILL.md")):
            meta, body = self._parse_frontmatter(path.read_text(encoding="utf-8"))
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
        lines = []
        for name in sorted(self.documents):
            manifest = self.documents[name].manifest
            lines.append(f"- {manifest.name}: {manifest.description}")
        return "\n".join(lines)

    def load_full_text(self, name: str) -> str:
        document = self.documents.get(name)
        if not document:
            known = ", ".join(sorted(self.documents)) or "(none)"
            return f"Error: Unknown skill '{name}'. Available skills: {known}"
        return f"<skill name=\"{document.manifest.name}\">\n{document.body}\n</skill>"


SKILL_REGISTRY = SkillRegistry(SKILLS_DIR)


def load_skill(name: str) -> str:
    """Load the full body of a named skill into the current context."""

    return SKILL_REGISTRY.load_full_text(name)


def system_prompt() -> str:
    return f"""You are a coding agent at {WORKDIR}.
Use load_skill when a task needs specialized instructions before you act.

Skills available:
{SKILL_REGISTRY.describe_available()}
"""


TOOLS = [bash, read_file, write_file, edit_file, load_skill]


def build_agent():
    return create_agent_runtime(system_prompt(), TOOLS)


def agent_loop(messages: list[dict[str, Any]]) -> str:
    return invoke_and_append(build_agent(), messages)


if __name__ == "__main__":
    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input("\033[36ms05-lc >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})
        try:
            final = agent_loop(history)
        except RuntimeError as exc:
            print(f"Error: {exc}")
            continue
        print(extract_text(final) or "(no response)")
        print()
