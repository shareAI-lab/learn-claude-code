#!/usr/bin/env python3
"""
llm_client.py - OpenAI 兼容客户端适配层（DashScope 可直接使用）

目标：
1. 统一 `create_client()` 入口，避免章节文件直接依赖具体厂商 SDK。
2. 使用 OpenAI 兼容接口（`/chat/completions`），默认适配 DashScope。
3. 对外暴露 Anthropic 风格的最小返回结构：
   - `response.content`（`text` / `tool_use` 块列表）
   - `response.stop_reason`（`tool_use` / `max_tokens` / `end_turn`）
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

DEFAULT_OPENAI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL_ID = "qwen3.6-plus"


class APIError(Exception):
    """兼容原 `anthropic.APIError` 用法的通用 API 异常。"""


class AttrDict(dict):
    """同时支持 `dict[key]` 与 `obj.key` 访问，兼容现有章节代码。"""

    def __getattr__(self, key: str) -> Any:
        if key in self:
            return self[key]
        raise AttributeError(key)


@dataclass
class CompatResponse:
    """最小响应对象：保持现有章节对 `content/stop_reason` 的访问方式。"""

    content: list[AttrDict]
    stop_reason: str


def _ensure_env_defaults() -> None:
    # 统一 OpenAI 兼容端点默认值（DashScope）。
    if not os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = DEFAULT_OPENAI_BASE_URL

    # 统一模型默认值，兼容旧变量 MODEL_ID。
    if not os.getenv("MODEL_ID"):
        os.environ["MODEL_ID"] = os.getenv("OPENAI_MODEL", DEFAULT_MODEL_ID)
    if not os.getenv("OPENAI_MODEL"):
        os.environ["OPENAI_MODEL"] = os.environ["MODEL_ID"]


def _resolve_api_key(explicit_api_key: str | None = None) -> str:
    api_key = explicit_api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "缺少 API Key：请设置 OPENAI_API_KEY。"
            "（兼容历史配置时，也可临时使用 ANTHROPIC_API_KEY）"
        )
    return api_key


def _chat_completions_url(base_url: str) -> str:
    trimmed = (base_url or "").rstrip("/")
    if not trimmed:
        trimmed = DEFAULT_OPENAI_BASE_URL
    if trimmed.endswith("/chat/completions"):
        return trimmed
    if trimmed.endswith("/v1"):
        return f"{trimmed}/chat/completions"
    return f"{trimmed}/v1/chat/completions"


def _block_value(block: Any, key: str, default: Any = None) -> Any:
    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


def _serialize_content(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif "content" in item:
                    parts.append(_serialize_content(item["content"]))
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    if isinstance(value, dict):
        if value.get("type") == "text" and isinstance(value.get("text"), str):
            return value["text"]
        if "text" in value and isinstance(value["text"], str):
            return value["text"]
        if "content" in value:
            return _serialize_content(value["content"])
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _safe_parse_json_object(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    if not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _convert_assistant_blocks_to_openai(content: list[Any]) -> dict:
    text_parts: list[str] = []
    tool_calls: list[dict] = []

    for block in content:
        block_type = _block_value(block, "type")
        if block_type == "text":
            text = _block_value(block, "text", "")
            if text:
                text_parts.append(str(text))
            continue

        if block_type == "tool_use":
            tool_calls.append(
                {
                    "id": _block_value(block, "id", f"call_{uuid4().hex[:12]}"),
                    "type": "function",
                    "function": {
                        "name": _block_value(block, "name", ""),
                        "arguments": json.dumps(
                            _block_value(block, "input", {}) or {},
                            ensure_ascii=False,
                        ),
                    },
                }
            )
            continue

        fallback = _serialize_content(block)
        if fallback:
            text_parts.append(fallback)

    payload = {"role": "assistant", "content": "\n".join(text_parts).strip()}
    if tool_calls:
        payload["tool_calls"] = tool_calls
    return payload


def _convert_user_blocks_to_openai(content: list[Any]) -> list[dict]:
    converted: list[dict] = []
    text_parts: list[str] = []

    for block in content:
        block_type = _block_value(block, "type")

        if block_type == "tool_result":
            if text_parts:
                converted.append({"role": "user", "content": "\n".join(text_parts).strip()})
                text_parts = []
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": _block_value(block, "tool_use_id", ""),
                    "content": _serialize_content(_block_value(block, "content", "")) or "(empty)",
                }
            )
            continue

        if block_type == "text":
            text = _block_value(block, "text", "")
            if text:
                text_parts.append(str(text))
            continue

        fallback = _serialize_content(_block_value(block, "content", block))
        if fallback:
            text_parts.append(fallback)

    if text_parts:
        converted.append({"role": "user", "content": "\n".join(text_parts).strip()})
    return converted


def _convert_messages_to_openai(messages: list[dict], system: str | None = None) -> list[dict]:
    converted: list[dict] = []
    if system:
        converted.append({"role": "system", "content": system})

    for raw_msg in messages:
        role = str(raw_msg.get("role", "user"))
        content = raw_msg.get("content", "")

        if isinstance(content, str):
            converted.append({"role": role, "content": content})
            continue

        if isinstance(content, list):
            if role == "assistant":
                converted.append(_convert_assistant_blocks_to_openai(content))
            elif role == "user":
                converted.extend(_convert_user_blocks_to_openai(content))
            else:
                converted.append({"role": role, "content": _serialize_content(content)})
            continue

        converted.append({"role": role, "content": _serialize_content(content)})

    return converted


def _convert_tools_to_openai(tools: list[dict] | None) -> list[dict] | None:
    if not tools:
        return None

    converted: list[dict] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = tool.get("name")
        if not name:
            continue
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {"type": "object"}),
                },
            }
        )
    return converted if converted else None


def _parse_openai_content(raw_content: Any) -> str:
    if raw_content is None:
        return ""
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, list):
        parts: list[str] = []
        for part in raw_content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
            else:
                parts.append(str(part))
        return "\n".join(part for part in parts if part)
    return str(raw_content)


def _map_finish_reason_to_stop_reason(finish_reason: str, has_tool_calls: bool) -> str:
    if has_tool_calls:
        return "tool_use"
    if finish_reason == "length":
        return "max_tokens"
    return "end_turn"


class OpenAICompatMessages:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    def create(
        self,
        *,
        model: str,
        messages: list[dict],
        system: str | None = None,
        tools: list[dict] | None = None,
        max_tokens: int = 8000,
        **kwargs: Any,
    ) -> CompatResponse:
        payload: dict[str, Any] = {
            "model": model,
            "messages": _convert_messages_to_openai(messages, system=system),
            "max_tokens": max_tokens,
        }

        openai_tools = _convert_tools_to_openai(tools)
        if openai_tools:
            payload["tools"] = openai_tools

        # 兼容保留：如果调用方额外传了 OpenAI 通用参数，透明透传。
        for key in ("temperature", "top_p", "presence_penalty", "frequency_penalty"):
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]

        endpoint = _chat_completions_url(self.base_url)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url=endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise APIError(f"HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise APIError(f"Network error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise APIError("请求超时") from exc
        except json.JSONDecodeError as exc:
            raise APIError(f"JSON 响应无效：{exc}") from exc

        choices = data.get("choices") or []
        if not choices:
            raise APIError(f"响应格式异常：缺少 choices。payload={data}")

        choice = choices[0] or {}
        message = choice.get("message") or {}
        tool_calls = message.get("tool_calls") or []
        finish_reason = str(choice.get("finish_reason") or "")

        content_blocks: list[AttrDict] = []
        text = _parse_openai_content(message.get("content"))
        if text:
            content_blocks.append(AttrDict({"type": "text", "text": text}))

        for call in tool_calls:
            fn = call.get("function") or {}
            content_blocks.append(
                AttrDict(
                    {
                        "type": "tool_use",
                        "id": call.get("id") or f"call_{uuid4().hex[:12]}",
                        "name": fn.get("name", ""),
                        "input": _safe_parse_json_object(fn.get("arguments")),
                    }
                )
            )

        stop_reason = _map_finish_reason_to_stop_reason(finish_reason, has_tool_calls=bool(tool_calls))
        return CompatResponse(content=content_blocks, stop_reason=stop_reason)


class OpenAICompatClient:
    def __init__(self, base_url: str, api_key: str):
        self.messages = OpenAICompatMessages(base_url=base_url, api_key=api_key)


def create_client(*, base_url: str | None = None, api_key: str | None = None) -> OpenAICompatClient:
    """创建统一 LLM 客户端（默认 DashScope OpenAI 兼容端点）。"""
    _ensure_env_defaults()
    resolved_base_url = base_url or os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)
    resolved_api_key = _resolve_api_key(api_key)
    return OpenAICompatClient(base_url=resolved_base_url, api_key=resolved_api_key)
