#!/usr/bin/env python3
"""
_llm_client.py - LLM Provider Abstraction Layer

Unified wrapper for Anthropic Messages API and OpenAI-compatible Chat Completions API.
Enables s01-s20 teaching code to switch between providers via environment variable.

Usage:
    from agents._llm_client import LLMClient
    client = LLMClient()  # auto-detect from env
    response = client.chat(system=SYSTEM, messages=messages, tools=TOOLS, max_tokens=8000)
    # response.content is a list of ContentBlock-like objects
    # response.stop_reason is "tool_use" or "end_turn"

Environment variables:
    LLM_PROVIDER=anthropic|openai  (default: anthropic)
    ANTHROPIC_API_KEY=...
    ANTHROPIC_BASE_URL=...         (optional, for proxies)
    MODEL_ID=claude-3-5-sonnet-20241022
    OPENAI_API_KEY=...             (or DEEPSEEK_API_KEY)
    OPENAI_BASE_URL=https://api.deepseek.com/v1
    MODEL_ID=deepseek-chat
"""

import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass
class ContentBlock:
    """Anthropic-style content block, unified across providers."""
    type: str          # "text" | "tool_use"
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict = None

    def __post_init__(self):
        if self.input is None:
            self.input = {}


@dataclass
class LLMResponse:
    """Anthropic-style response wrapper."""
    content: list
    stop_reason: str  # "tool_use" | "end_turn" | "stop"


class LLMClient:
    """
    Unified LLM client supporting Anthropic and OpenAI-compatible providers.

    Provider is selected via LLM_PROVIDER env var (default: anthropic).
    For OpenAI-compatible providers (DeepSeek, Qwen, Kimi, etc.), set:
        LLM_PROVIDER=openai
        OPENAI_API_KEY=sk-...
        OPENAI_BASE_URL=https://api.deepseek.com/v1
        MODEL_ID=deepseek-chat
    """

    def __init__(self, provider: str = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", "anthropic").lower()
        self.model = os.environ["MODEL_ID"]

        if self.provider == "anthropic":
            from anthropic import Anthropic
            base_url = os.getenv("ANTHROPIC_BASE_URL")
            self._client = Anthropic(base_url=base_url) if base_url else Anthropic()
        elif self.provider == "openai":
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {self.provider}. Use 'anthropic' or 'openai'.")

    def chat(self, system: str, messages: list, tools: list = None,
             max_tokens: int = 8000) -> LLMResponse:
        """
        Send a chat request and return a unified LLMResponse.

        Args:
            system: System prompt string.
            messages: List of message dicts (Anthropic format).
            tools: List of tool dicts (Anthropic format with input_schema).
            max_tokens: Maximum tokens in response.

        Returns:
            LLMResponse with .content (list of ContentBlock) and .stop_reason.
        """
        if self.provider == "anthropic":
            return self._chat_anthropic(system, messages, tools, max_tokens)
        else:
            return self._chat_openai(system, messages, tools, max_tokens)

    def _chat_anthropic(self, system: str, messages: list, tools: list,
                        max_tokens: int) -> LLMResponse:
        """Direct Anthropic API call, return as-is."""
        kwargs = {"model": self.model, "system": system, "messages": messages,
                  "max_tokens": max_tokens}
        if tools:
            kwargs["tools"] = tools
        response = self._client.messages.create(**kwargs)
        return LLMResponse(content=list(response.content),
                           stop_reason=response.stop_reason)

    def _chat_openai(self, system: str, messages: list, tools: list,
                     max_tokens: int) -> LLMResponse:
        """OpenAI-compatible call, convert to Anthropic-style response."""
        # Convert messages: prepend system message
        oai_messages = [{"role": "system", "content": system}]
        for msg in messages:
            oai_messages.append(self._convert_msg_to_openai(msg))

        # Convert tools
        oai_tools = None
        if tools:
            oai_tools = [{"type": "function",
                          "function": {"name": t["name"],
                                       "description": t.get("description", ""),
                                       "parameters": t.get("input_schema", {"type": "object", "properties": {}})}}
                         for t in tools]

        kwargs = {"model": self.model, "messages": oai_messages,
                  "max_tokens": max_tokens}
        if oai_tools:
            kwargs["tools"] = oai_tools

        response = self._client.chat.completions.create(**kwargs)
        return self._wrap_openai_response(response)

    def _convert_msg_to_openai(self, msg: dict) -> dict:
        """Convert Anthropic message format to OpenAI format."""
        role = msg["role"]
        content = msg.get("content")

        # Simple string content
        if isinstance(content, str):
            return {"role": role, "content": content}

        # List content (tool_use / tool_result blocks)
        if isinstance(content, list):
            # Assistant message with tool_use blocks
            if role == "assistant":
                text_parts = []
                tool_calls = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block["text"])
                        elif block.get("type") == "tool_use":
                            tool_calls.append({
                                "id": block["id"],
                                "type": "function",
                                "function": {"name": block["name"],
                                             "arguments": json.dumps(block.get("input", {}))},
                            })
                    else:
                        # Anthropic SDK object
                        btype = getattr(block, "type", None)
                        if btype == "text":
                            text_parts.append(block.text)
                        elif btype == "tool_use":
                            tool_calls.append({
                                "id": block.id,
                                "type": "function",
                                "function": {"name": block.name,
                                             "arguments": json.dumps(getattr(block, "input", {}))},
                            })
                result = {"role": "assistant"}
                if text_parts:
                    result["content"] = "\n".join(text_parts)
                if tool_calls:
                    result["tool_calls"] = tool_calls
                return result

            # User message with tool_result blocks
            if role == "user":
                tool_results = []
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": block.get("content", ""),
                        })
                    elif isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block["text"])
                if tool_results:
                    return tool_results[0]  # OpenAI expects one tool msg per call
                return {"role": "user", "content": "\n".join(text_parts) if text_parts else ""}

        return {"role": role, "content": str(content) if content else ""}

    def _wrap_openai_response(self, response) -> LLMResponse:
        """Convert OpenAI ChatCompletion response to Anthropic-style LLMResponse."""
        choice = response.choices[0]
        msg = choice.message
        content = []

        # Text content
        if msg.content:
            content.append(ContentBlock(type="text", text=msg.content))

        # Tool calls
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}
                content.append(ContentBlock(
                    type="tool_use",
                    id=tc.id,
                    name=tc.function.name,
                    input=args,
                ))

        # Map finish_reason
        finish = choice.finish_reason
        if finish == "tool_calls":
            stop_reason = "tool_use"
        elif finish == "stop":
            stop_reason = "end_turn"
        else:
            stop_reason = finish or "end_turn"

        return LLMResponse(content=content, stop_reason=stop_reason)
