"""System prompt 组装。

顺序:
1. 基础 system 声明(从 prompts/{lang}/base_system.md 读)
2. 读取 memory_files(通过 memory.load_all)
3. skills 目录
4. workspace 标签
5. 工具清单由 OpenAI 侧通过 `tools` 参数传递,这里不重复
"""
from __future__ import annotations

from ..config.models import Config
from ..memory import load_all
from ..prompts import load_prompt


def build_system_prompt(cfg: Config, skills=None) -> str:
    base = load_prompt("base_system", lang=cfg.prompt_lang, workspace=cfg.workspace_root())
    parts = [base]
    parts.extend(load_all(cfg.memory_files, cwd=cfg.workspace_root()))
    if skills is not None and skills.skills:
        parts.append(
            "<skills>\nYou can invoke LoadSkill(name=...) to load any of these:\n"
            f"{skills.descriptions()}\n</skills>"
        )
    parts.append(f'<workspace path="{cfg.workspace_root()}"/>')
    return "\n\n".join(parts)
