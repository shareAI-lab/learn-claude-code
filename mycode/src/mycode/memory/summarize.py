"""退出总结: 从 session messages 里提炼"值得跨会话保留"的要点,
追加到 .mycode/MEMORY.md。

对齐 DESIGN §9 M3:
- 命令形式: /quit --summary 或 /exit-summary
- 使用模型: roles.summarize (复用 auto-compact 的小模型)
- 写入位置: 追加到 .mycode/MEMORY.md (不动用户手写的 CLAUDE.md)
- 条目格式: 带时间戳的 Markdown 块
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..config.models import Config


MEMORY_FILE_REL = ".mycode/MEMORY.md"


def _memory_path(cfg: Config) -> Path:
    p = cfg.workspace_root() / MEMORY_FILE_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def summarize_to_memory(
    messages: list[dict[str, Any]],
    cfg: Config,
    summarize_llm,
) -> str:
    """调 LLM 产出要点,追加到 .mycode/MEMORY.md。返回人类可读的状态字符串。"""
    non_system = [m for m in messages if m.get("role") != "system"]
    if not non_system:
        return "(no conversation to summarize)"

    from ..prompts import load_prompt

    convo_text = json.dumps(non_system, default=str, ensure_ascii=False)[-60000:]
    prompt_prefix = load_prompt(
        "summarize", lang=cfg.prompt_lang, workspace=cfg.workspace_root()
    )
    try:
        resp = summarize_llm.call(
            messages=[{"role": "user", "content": prompt_prefix + "\n\n" + convo_text}],
            tools=None,
        )
        extracted = (resp.content or "").strip()
    except Exception as e:
        return f"Error: summarize failed: {type(e).__name__}: {e}"

    if not extracted or extracted.lower().startswith("(nothing"):
        return "(nothing worth saving)"

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    block = (
        f"\n## Auto summary {ts}\n"
        f"{extracted}\n"
    )
    path = _memory_path(cfg)
    with path.open("a", encoding="utf-8") as f:
        if path.stat().st_size == 0:
            f.write(
                "# Auto-generated memory\n\n"
                "> This file is **appended** by `/quit --summary` or `/exit-summary`.\n"
                "> Feel free to curate / delete blocks you no longer want.\n"
            )
        f.write(block)
    return f"Appended {len(extracted.splitlines())} lines to {path}"
