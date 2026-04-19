"""AskExpertModel 工具: 遇到主 agent 搞不定的硬题,临时升级到 expert 模型。

对齐 Kode 的 AskExpertModelTool:
- expert LLM 走 roles.expert(未填则继承主 provider,但通常用户会配一个更强的模型)
- 纯文本问答:expert 看不到主 agent 的工具集,避免嵌套工具调用
- 失败转 Error 字符串,不抛出 loop
"""
from __future__ import annotations

from typing import Any

from ..config.models import Config
from ..llm.client import LLMClient
from .registry import Tool, ToolRegistry


def _run_ask_expert(
    *,
    expert_llm: LLMClient,
    question: str,
    context: str = "",
    prompt_lang: str = "en",
) -> str:
    from ..prompts import load_prompt

    q = (question or "").strip()
    if not q:
        return "Error: question is empty"

    user_content = q
    if context.strip():
        user_content = f"Context:\n{context.strip()}\n\nQuestion:\n{q}"

    try:
        system_prompt = load_prompt("expert_system", lang=prompt_lang)
        resp = expert_llm.call(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            tools=None,  # expert 不给工具
        )
    except Exception as e:
        return f"Error: expert LLM failed: {type(e).__name__}: {e}"

    answer = (resp.content or "").strip()
    if not answer:
        return "Error: expert returned empty answer"
    # 加个小前缀让主 agent 知道结果来源
    model_name = expert_llm.cfg.model or "expert"
    return f"[Expert model: {model_name}]\n\n{answer}"


def register_ask_expert(
    registry: ToolRegistry,
    *,
    cfg: Config,
    expert_llm: LLMClient,
) -> None:
    registry.register(
        Tool(
            name="AskExpertModel",
            description=(
                "Ask a stronger 'expert' model a single question. Use when you "
                "hit a hard problem (complex algorithm, obscure API, tricky "
                "domain knowledge) that your own reasoning may miss. The expert "
                "has NO tools — give it all the context it needs in one shot."
            ),
            requires=["network"],
            input_schema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The full question, self-contained",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional background: code snippets, "
                        "relevant file contents, prior attempts",
                    },
                },
                "required": ["question"],
            },
            handler=lambda **kw: _run_ask_expert(
                expert_llm=expert_llm,
                question=kw["question"],
                context=kw.get("context", ""),
                prompt_lang=cfg.prompt_lang,
            ),
        )
    )
