"""OpenAI Chat Completions 封装。

设计要点:
- 统一使用官方 openai SDK，通过 base_url 切换任意兼容后端
- 支持 default_query（为 fenbi 式 URL 的 ?service_provider=ppio 提供能力）
- 流式与非流式两路,流式产出增量 chunk 事件
- 失败直接抛 APIError，由 agent loop 决定是否重试 / 回灌 error
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from ..config.models import Config


@dataclass
class LLMResponse:
    """非流式响应的解构结果。"""

    content: str
    tool_calls: list[dict[str, Any]]  # [{id, name, arguments(str json)}, ...]
    finish_reason: str
    raw: ChatCompletion


class LLMClient:
    """对 OpenAI Chat Completions 的薄封装。"""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        api_key = cfg.resolved_api_key() or "sk-noop"  # ollama 等允许空
        kwargs: dict[str, Any] = {"api_key": api_key}
        if cfg.base_url:
            kwargs["base_url"] = cfg.base_url
        if cfg.default_query:
            kwargs["default_query"] = cfg.default_query
        self._client = OpenAI(**kwargs)

    def _common_params(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": messages,
            "max_tokens": self.cfg.max_tokens,
        }
        if self.cfg.temperature is not None:
            params["temperature"] = self.cfg.temperature
        if tools:
            params["tools"] = tools
            params["parallel_tool_calls"] = not self.cfg.serial_only
        if stream:
            params["stream"] = True
            params["stream_options"] = {"include_usage": True}
        return params

    def call(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """非流式调用，返回结构化响应。"""
        resp = self._client.chat.completions.create(
            **self._common_params(messages, tools, stream=False)
        )
        choice = resp.choices[0]
        msg = choice.message
        tool_calls: list[dict[str, Any]] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    }
                )
        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            raw=resp,
        )

    def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """流式调用，逐块 yield 事件。

        事件格式::
            {"type": "text", "delta": "..."}
            {"type": "tool_call_start", "index": 0, "id": "...", "name": "..."}
            {"type": "tool_call_args", "index": 0, "delta": "..."}
            {"type": "finish", "reason": "tool_calls" | "stop" | ...}
            {"type": "usage", "usage": {...}}
        """
        stream = self._client.chat.completions.create(
            **self._common_params(messages, tools, stream=True)
        )
        seen_tool_starts: set[int] = set()
        finish_reason: str | None = None
        for chunk in stream:  # type: ChatCompletionChunk
            if not chunk.choices:
                if chunk.usage:
                    yield {
                        "type": "usage",
                        "usage": chunk.usage.model_dump(),
                    }
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            if delta.content:
                yield {"type": "text", "delta": delta.content}
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in seen_tool_starts:
                        seen_tool_starts.add(idx)
                        yield {
                            "type": "tool_call_start",
                            "index": idx,
                            "id": tc.id or "",
                            "name": (tc.function.name if tc.function else "") or "",
                        }
                    if tc.function and tc.function.arguments:
                        yield {
                            "type": "tool_call_args",
                            "index": idx,
                            "delta": tc.function.arguments,
                        }
            if choice.finish_reason:
                finish_reason = choice.finish_reason
        yield {"type": "finish", "reason": finish_reason or "stop"}
