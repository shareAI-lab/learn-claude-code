#!/usr/bin/env python3
# Harness: on-demand knowledge -- domain expertise, loaded when the model asks.
"""
s05_subagent_openai.py - Skills (OpenAI version)

This file is an OpenAI adaptation of `agents/s05_skill_loading.py`.

The model loads specialized knowledge only when it calls `load_skill("...")`.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

# Keep imports stable when running from this directory
os.environ["PYTHONPATH"] = r"E:\ai_pycode\learn-claude-code-main"
sys.path.insert(0, r"E:\ai_pycode\learn-claude-code-main")


# Try to prevent Windows console encoding issues during tool output printing.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


WORKDIR = Path.cwd()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
MODEL = os.environ.get("OPENAI_MODEL_ID") or os.environ.get("MODEL_ID")

SKILLS_DIR = WORKDIR / "skills"

SYSTEM = ""  # will be filled after SKILL_LOADER is created


class SkillLoader:
    """Load skills from skills/<name>/SKILL.md using YAML frontmatter."""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills = {}
        self._load_all()

    def _load_all(self):
        if not self.skills_dir.exists():
            return
        for f in sorted(self.skills_dir.rglob("SKILL.md")):
            text = f.read_text(encoding="utf-8", errors="backslashreplace")
            meta, body = self._parse_frontmatter(text)
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body, "path": str(f)}

    def _parse_frontmatter(self, text: str) -> tuple:
        """Parse YAML frontmatter between --- delimiters."""
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            meta = {}
        return meta, match.group(2).strip()

    def get_descriptions(self) -> str:
        """Layer 1: short descriptions for the system prompt."""
        if not self.skills:
            return "(no skills available)"
        lines = []
        for name, skill in self.skills.items():
            desc = skill["meta"].get("description", "No description")
            tags = skill["meta"].get("tags", "")
            line = f"  - {name}: {desc}"
            if tags:
                line += f" [{tags}]"
            lines.append(line)
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        """Layer 2: full skill body returned in tool output."""
        skill = self.skills.get(name)
        if not skill:
            avail = ", ".join(self.skills.keys())
            return f"Error: Unknown skill '{name}'. Available: {avail}"
        return f"<skill name=\"{name}\">\n{skill['body']}\n</skill>"


SKILL_LOADER = SkillLoader(SKILLS_DIR)

SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.

Skills available:
{SKILL_LOADER.get_descriptions()}"""


# -- Tool implementations --
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        if sys.platform == "win32":
            r = subprocess.run(
                command,
                shell=True,
                cwd=WORKDIR,
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="backslashreplace",
            )
        else:
            r = subprocess.run(
                command,
                shell=True,
                cwd=WORKDIR,
                capture_output=True,
                text=True,
                timeout=120,
                executable="/bin/bash",
                encoding="utf-8",
                errors="backslashreplace",
            )
        stdout = r.stdout or ""
        stderr = r.stderr or ""
        out = (stdout + stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except Exception as e:
        return f"Error: {e}"


def run_read(path: str, limit: int = None) -> str:
    try:
        text = safe_path(path).read_text(encoding="utf-8", errors="backslashreplace")
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8", errors="backslashreplace")
        return f"Wrote {len(content)} bytes"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text(encoding="utf-8", errors="backslashreplace")
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1), encoding="utf-8", errors="backslashreplace")
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


TOOL_HANDLERS = {
    "bash": lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "load_skill": lambda **kw: SKILL_LOADER.get_content(kw["name"]),
}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace exact text in file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": "Load specialized knowledge by name.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Skill name to load"}},
                "required": ["name"],
            },
        },
    },
]


def agent_loop(messages: list):
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM}, *messages],
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=8000,
            temperature=0.7,
        )

        assistant_message = response.choices[0].message
        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": assistant_message.tool_calls,
            }
        )

        if not assistant_message.tool_calls:
            return

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            args = {}
            try:
                args = json.loads(tool_call.function.arguments or "{}")  # type: ignore[name-defined]
            except Exception:
                args = {}

            handler = TOOL_HANDLERS.get(tool_name)
            try:
                output = handler(**args) if handler else f"Unknown tool: {tool_name}"
            except Exception as e:
                output = f"Error: {e}"

            print(f"> {tool_name}:")
            print(str(output)[:200])

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(output)[:50000],
                }
            )


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms05 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break

        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})
        agent_loop(history)

        if history and history[-1]["role"] == "assistant" and history[-1].get("content"):
            print(history[-1]["content"])

        print()

