"""AskUserQuestion 工具: agent 反向向用户提问,阻塞等用户输入。

对齐 Claude Code 的 AskUserQuestion 形态(简化版):
- 一次可发多道问题
- 每道问题有 question + 2-4 个 options(单选)
- 用户选完之后结构化回灌给模型

handler 需要一个 ask_fn 回调:
  ask_fn(questions: list[Question]) -> list[Answer]
在 REPL 里由 Repl 注入真实实现,单次模式 / 单元测试用 stub。
"""
from __future__ import annotations

import json
from typing import Any, Callable

from .registry import Tool, ToolRegistry


# (questions, ) → answers 字典
AskFn = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]


def _validate_and_normalize(raw: Any) -> list[dict[str, Any]] | str:
    """校验 questions 入参,返回规范化列表或错误字符串。"""
    if not isinstance(raw, list):
        return "Error: questions must be a list"
    if not (1 <= len(raw) <= 4):
        return "Error: questions count must be 1..4"
    out: list[dict[str, Any]] = []
    for i, q in enumerate(raw):
        if not isinstance(q, dict):
            return f"Error: question[{i}] must be object"
        question = str(q.get("question", "")).strip()
        options = q.get("options")
        if not question:
            return f"Error: question[{i}] missing 'question'"
        if not isinstance(options, list) or not (2 <= len(options) <= 4):
            return f"Error: question[{i}].options must be list of 2..4"
        norm_options: list[dict[str, str]] = []
        for j, opt in enumerate(options):
            if not isinstance(opt, dict):
                return f"Error: question[{i}].options[{j}] must be object"
            label = str(opt.get("label", "")).strip()
            description = str(opt.get("description", "")).strip()
            if not label:
                return f"Error: question[{i}].options[{j}] missing 'label'"
            norm_options.append({"label": label, "description": description})
        out.append(
            {
                "question": question,
                "header": str(q.get("header", ""))[:32],
                "options": norm_options,
            }
        )
    return out


def register_ask_user(
    registry: ToolRegistry,
    *,
    ask_fn: AskFn,
) -> None:
    def _handler(**kw) -> str:
        normalized = _validate_and_normalize(kw.get("questions", []))
        if isinstance(normalized, str):
            return normalized
        try:
            answers = ask_fn(normalized)
        except InteractiveUnavailable as e:
            return f"Error: {e}"
        except KeyboardInterrupt:
            return "Error: user aborted"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"
        return json.dumps(answers, ensure_ascii=False, indent=2)

    registry.register(
        Tool(
            name="AskUserQuestion",
            description=(
                "Ask the user 1-4 questions with 2-4 options each. Blocks until "
                "the user answers. Use when you need a decision or preference "
                "that is not in the conversation."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 4,
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {"type": "string"},
                                "header": {
                                    "type": "string",
                                    "description": "Short chip label, max ~12 chars",
                                },
                                "options": {
                                    "type": "array",
                                    "minItems": 2,
                                    "maxItems": 4,
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "label": {"type": "string"},
                                            "description": {"type": "string"},
                                        },
                                        "required": ["label", "description"],
                                    },
                                },
                            },
                            "required": ["question", "options"],
                        },
                    }
                },
                "required": ["questions"],
            },
            handler=_handler,
        )
    )


class InteractiveUnavailable(RuntimeError):
    """非交互环境(-p 单次模式)调 AskUserQuestion 时抛。"""


def non_interactive_ask(_: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """给 `oaic -p "..."` 用的 fallback:直接拒绝。"""
    raise InteractiveUnavailable("AskUserQuestion requires interactive mode; run without -p")
