#!/usr/bin/env python3
# Deep Agents track: persistence -- remembering across the session boundary.
"""
s09_memory_system.py - Memory System with Deep Agents

This chapter keeps memory explicit: one Markdown file per memory plus one index.
Deep Agents can load persistent files into prompt context, but the harness still
has to decide what deserves long-term storage.
"""

from __future__ import annotations

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

MEMORY_DIR = WORKDIR / '.memory'
MEMORY_INDEX = MEMORY_DIR / 'MEMORY.md'
MEMORY_TYPES = ('user', 'feedback', 'project', 'reference')
SYSTEM = f"You are a coding agent at {WORKDIR}. Save only durable cross-session facts in memory."


class MemoryManager:
    def __init__(self, memory_dir: Path | None = None):
        self.memory_dir = memory_dir or MEMORY_DIR
        self.memories: dict[str, dict[str, str]] = {}
        self.load_all()

    def load_all(self) -> None:
        self.memories = {}
        if not self.memory_dir.exists():
            return
        for md_file in sorted(self.memory_dir.glob('*.md')):
            if md_file.name == 'MEMORY.md':
                continue
            parsed = self._parse_frontmatter(md_file.read_text(encoding='utf-8'))
            if not parsed:
                continue
            name = parsed.get('name', md_file.stem)
            self.memories[name] = {
                'description': parsed.get('description', ''),
                'type': parsed.get('type', 'project'),
                'content': parsed.get('content', ''),
                'file': md_file.name,
            }

    def save_memory(self, name: str, description: str, mem_type: str, content: str) -> str:
        if mem_type not in MEMORY_TYPES:
            return f"Error: type must be one of {MEMORY_TYPES}"
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name.lower())
        if not safe_name:
            return 'Error: invalid memory name'
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.memory_dir / f'{safe_name}.md'
        file_path.write_text(
            f"---\nname: {name}\ndescription: {description}\ntype: {mem_type}\n---\n{content}\n",
            encoding='utf-8',
        )
        self.load_all()
        self._rebuild_index()
        try:
            display_path = file_path.relative_to(WORKDIR)
        except ValueError:
            display_path = file_path
        return f"Saved memory '{name}' [{mem_type}] to {display_path}"

    def load_memory_prompt(self) -> str:
        if not self.memories:
            return ''
        sections = ['# Memories (persistent across sessions)', '']
        for mem_type in MEMORY_TYPES:
            typed = {k: v for k, v in self.memories.items() if v['type'] == mem_type}
            if not typed:
                continue
            sections.append(f'## [{mem_type}]')
            for name, mem in typed.items():
                sections.append(f"### {name}: {mem['description']}")
                if mem['content'].strip():
                    sections.append(mem['content'].strip())
                sections.append('')
        return '\n'.join(sections).strip()

    def _rebuild_index(self) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        lines = ['# Memory Index', '']
        for name, mem in self.memories.items():
            lines.append(f"- {name}: {mem['description']} [{mem['type']}]")
        (self.memory_dir / 'MEMORY.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    def _parse_frontmatter(self, text: str) -> dict[str, str] | None:
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', text, re.DOTALL)
        if not match:
            return None
        header, body = match.group(1), match.group(2)
        result: dict[str, str] = {'content': body.strip()}
        for line in header.splitlines():
            if ':' in line:
                key, _, value = line.partition(':')
                result[key.strip()] = value.strip()
        return result


MEMORY = MemoryManager()


class MemoryPromptMiddleware(AgentMiddleware):
    def __init__(self, manager: MemoryManager):
        self.manager = manager

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        prompt = self.manager.load_memory_prompt()
        if not prompt:
            return handler(request)
        new_blocks = list(request.system_message.content_blocks) + [{"type": "text", "text": prompt}]
        return handler(request.override(system_message=SystemMessage(content=new_blocks)))


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

@tool
def save_memory(name: str, description: str, mem_type: str, content: str) -> str:
    """Save a persistent memory that should survive the current session."""
    return MEMORY.save_memory(name, description, mem_type, content)

TOOLS = [bash, read_file, write_file, edit_file, save_memory]


def build_agent():
    MEMORY.load_all()
    return build_stage_agent(
        's09',
        model=build_openai_model(),
        tools=TOOLS,
        system_prompt=SYSTEM,
        extra_middleware=[MemoryPromptMiddleware(MEMORY)],
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
            query = input('\033[36ms09-da >> \033[0m')
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
