"""Compact 工具: 主动触发上下文压缩。

对齐 TOOLS.md §5.1: 调用后模型本轮应结束,由上层重新组织新一轮对话。
这里只是把状态的 messages 替换,真正的"结束轮"由 loop 感知 finish_reason 处理。
"""
from __future__ import annotations

from .registry import Tool, ToolRegistry


def register_compact(
    registry: ToolRegistry,
    *,
    trigger_compact_fn,  # callable: () -> str, 由 CLI 绑定到实际 state + summarize_llm
) -> None:
    registry.register(
        Tool(
            name="Compact",
            description=(
                "Compact the current conversation: earlier messages are summarized "
                "and the full transcript is archived. Use when the conversation is "
                "getting long but you want to keep working."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "What aspects to prioritize preserving",
                    },
                },
            },
            handler=lambda **kw: trigger_compact_fn(),
        )
    )
