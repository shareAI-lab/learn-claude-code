"""System prompt 组装。

顺序:
1. 基础 system 声明
2. 读取 memory_files(通过 memory.load_all)
3. workspace 标签
4. 工具清单由 OpenAI 侧通过 `tools` 参数传递,这里不重复
"""
from __future__ import annotations

from ..config.models import Config
from ..memory import load_all


BASE_SYSTEM = """\
You are oai-code, an OpenAI-compatible coding agent that lives in the user's workspace.
Use the provided tools to read and edit files, run shell commands, and search the codebase.

Guidelines:
- Prefer Read/Grep/Glob before Edit/Write; do not overwrite a file you have not read.
- Keep replies concise. Let tool calls do the work; only explain when the user asks.
- Before destructive shell commands, double-check paths.
- If you need to plan multi-step work, say so briefly, then proceed.
"""


def build_system_prompt(cfg: Config) -> str:
    parts = [BASE_SYSTEM]
    parts.extend(load_all(cfg.memory_files, cwd=cfg.workspace_root()))
    parts.append(f'<workspace path="{cfg.workspace_root()}"/>')
    return "\n\n".join(parts)
