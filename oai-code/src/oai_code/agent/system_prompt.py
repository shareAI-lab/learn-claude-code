"""System prompt 组装。

顺序:
1. 基础 system 声明
2. 读取 memory_files(项目级 + 用户级)
3. 工具清单由 OpenAI 侧通过 `tools` 参数传递,这里只给简短说明
"""
from __future__ import annotations

from pathlib import Path

from ..config.models import Config


BASE_SYSTEM = """\
You are oai-code, an OpenAI-compatible coding agent that lives in the user's workspace.
Use the provided tools to read and edit files, run shell commands, and search the codebase.

Guidelines:
- Prefer Read/Grep/Glob before Edit/Write; do not overwrite a file you have not read.
- Keep replies concise. Let tool calls do the work; only explain when the user asks.
- Before destructive shell commands, double-check paths.
- If you need to plan multi-step work, say so briefly, then proceed.
"""


def _read_memory_file(p: str) -> str | None:
    path = Path(p).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists() or not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not text:
        return None
    return f"<memory path=\"{path}\">\n{text}\n</memory>"


def build_system_prompt(cfg: Config) -> str:
    parts = [BASE_SYSTEM]
    for mf in cfg.memory_files:
        if snippet := _read_memory_file(mf):
            parts.append(snippet)
    parts.append(f"<workspace path=\"{cfg.workspace_root()}\"/>")
    return "\n\n".join(parts)
