#!/usr/bin/env python3
# Deep Agents track: assembly -- the system prompt is a pipeline, not a string.
"""
s10_system_prompt.py - System Prompt Construction with Deep Agents

This chapter keeps the prompt explicit: stable sections are assembled once, and
more volatile runtime context is injected through middleware right before model
calls.
"""

from __future__ import annotations

import datetime
import os
import re
from pathlib import Path
from typing import Any, Callable

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from langchain.tools import tool

try:
    from ._deepagents_gating import build_stage_agent
    from .common import WORKDIR, build_openai_model, extract_text
    from ._common import run_bash as raw_bash, read_file as raw_read_file, write_file as raw_write_file, edit_file as raw_edit_file
except ImportError:
    from _deepagents_gating import build_stage_agent
    from common import WORKDIR, build_openai_model, extract_text
    from _common import run_bash as raw_bash, read_file as raw_read_file, write_file as raw_write_file, edit_file as raw_edit_file

DYNAMIC_BOUNDARY = '=== DYNAMIC_BOUNDARY ==='


class SystemPromptBuilder:
    def __init__(self, workdir: Path | None = None, tools: list[Any] | None = None):
        self.workdir = workdir or WORKDIR
        self.tools = tools or []
        self.skills_dir = self.workdir / 'skills'
        self.memory_dir = self.workdir / '.memory'

    def build_core(self) -> str:
        return (
            f'You are a coding agent operating in {self.workdir}.\n'
            'Use the provided tools to explore, read, write, and edit files.\n'
            'Always verify before assuming. Prefer reading files over guessing.'
        )

    def build_tool_listing(self) -> str:
        if not self.tools:
            return ''
        lines = ['# Available tools']
        for tool in self.tools:
            name = getattr(tool, 'name', getattr(tool, '__name__', type(tool).__name__))
            lines.append(f'- {name}')
        return '\n'.join(lines)

    def build_skill_listing(self) -> str:
        if not self.skills_dir.exists():
            return ''
        skills = []
        for skill_md in sorted(self.skills_dir.rglob('SKILL.md')):
            text = skill_md.read_text(encoding='utf-8')
            match = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
            if not match:
                continue
            meta: dict[str, str] = {}
            for line in match.group(1).splitlines():
                if ':' in line:
                    k, _, v = line.partition(':')
                    meta[k.strip()] = v.strip()
            skills.append(f"- {meta.get('name', skill_md.parent.name)}: {meta.get('description', '')}")
        return '# Available skills\n' + '\n'.join(skills) if skills else ''

    def build_memory_section(self) -> str:
        if not self.memory_dir.exists():
            return ''
        items = []
        for md_file in sorted(self.memory_dir.glob('*.md')):
            if md_file.name == 'MEMORY.md':
                continue
            items.append(f'- {md_file.name}')
        return '# Memory files\n' + '\n'.join(items) if items else ''

    def build_claude_md(self) -> str:
        sources = []
        user_claude = Path.home() / '.claude' / 'CLAUDE.md'
        if user_claude.exists():
            sources.append(('user global (~/.claude/CLAUDE.md)', user_claude.read_text(encoding='utf-8').strip()))
        project_claude = self.workdir / 'CLAUDE.md'
        if project_claude.exists():
            sources.append(('project root (CLAUDE.md)', project_claude.read_text(encoding='utf-8').strip()))
        if not sources:
            return ''
        parts = ['# CLAUDE.md instructions']
        for label, content in sources:
            parts.append(f'## From {label}')
            parts.append(content)
        return '\n\n'.join(parts)

    def build_dynamic_context(self) -> str:
        return '\n'.join([
            '# Dynamic context',
            f'Current date: {datetime.date.today().isoformat()}',
            f'Working directory: {self.workdir}',
            f'Platform: {os.uname().sysname}',
        ])

    def build(self) -> str:
        sections = [
            self.build_core(),
            self.build_tool_listing(),
            self.build_skill_listing(),
            self.build_memory_section(),
            self.build_claude_md(),
            DYNAMIC_BOUNDARY,
            self.build_dynamic_context(),
        ]
        return '\n\n'.join(part for part in sections if part)

    def build_static(self) -> str:
        full = self.build()
        if DYNAMIC_BOUNDARY not in full:
            return full
        return full.split(DYNAMIC_BOUNDARY, 1)[0].rstrip()


class DynamicContextMiddleware(AgentMiddleware):
    def __init__(self, builder: SystemPromptBuilder):
        self.builder = builder

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        blocks = list(request.system_message.content_blocks)
        blocks.append({"type": "text", "text": DYNAMIC_BOUNDARY})
        blocks.append({"type": "text", "text": self.builder.build_dynamic_context()})
        return handler(request.override(system_message=SystemMessage(content=blocks)))


@tool
def bash(command: str) -> str:
    """Run a shell command in the workspace."""
    return raw_bash(command)

@tool
def read_file(path: str, limit: int | None = None) -> str:
    """Read file contents from the workspace."""
    return raw_read_file(path, limit)

@tool
def write_file(path: str, content: str) -> str:
    """Write content to a workspace file."""
    return raw_write_file(path, content)

@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace exact text in a workspace file."""
    return raw_edit_file(path, old_text, new_text)

TOOLS = [bash, read_file, write_file, edit_file]
BUILDER = SystemPromptBuilder(tools=TOOLS)


def build_agent():
    return build_stage_agent(
        's10',
        model=build_openai_model(),
        tools=TOOLS,
        system_prompt=BUILDER.build_static(),
        extra_middleware=[DynamicContextMiddleware(BUILDER)],
    )


def agent_loop(messages: list[dict[str, Any]]) -> str:
    result = build_agent().invoke({"messages": messages})
    text = extract_text(result["messages"][-1].content)
    if text:
        messages.append({"role": "assistant", "content": text})
    return text


if __name__ == '__main__':
    history: list[dict[str, Any]] = []
    while True:
        try:
            query = input('\033[36ms10-da >> \033[0m')
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ('q', 'exit', ''):
            break
        history.append({"role": "user", "content": query})
        try:
            print(agent_loop(history) or '(no response)')
        except RuntimeError as exc:
            print(f'Error: {exc}')
        print()
