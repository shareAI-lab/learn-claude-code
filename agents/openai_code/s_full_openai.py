#!/usr/bin/env python3
# OpenAI wrapper for the full reference harness.
#
# This file keeps all s_full mechanisms, but swaps the Anthropic API client
# with an OpenAI-compatible adapter.

import json
import os
from types import SimpleNamespace

from openai import OpenAI

from agents import s_full as base


def _stringify_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if hasattr(item, "text"):
                parts.append(str(item.text))
            elif isinstance(item, dict):
                if item.get("type") == "tool_result":
                    parts.append(
                        f"<tool_result id=\"{item.get('tool_use_id', '')}\">\n"
                        f"{item.get('content', '')}\n</tool_result>"
                    )
                elif item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p)
    return str(content)


def _convert_messages(messages: list, system: str = None) -> list:
    out = []
    if system:
        out.append({"role": "system", "content": system})
    for msg in messages:
        role = msg.get("role", "user")
        content = _stringify_content(msg.get("content", ""))
        if role not in ("system", "user", "assistant"):
            role = "user"
        out.append({"role": role, "content": content})
    return out


def _convert_tools(tools: list) -> list:
    converted = []
    for t in tools or []:
        if "function" in t:
            converted.append(t)
            continue
        name = t.get("name")
        if not name:
            continue
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                },
            }
        )
    return converted


class _OpenAIAnthropicCompatMessages:
    def __init__(self, client: OpenAI):
        self._client = client

    def create(self, model: str, messages: list, tools: list = None, max_tokens: int = 8000, system: str = None):
        oa_messages = _convert_messages(messages, system=system)
        oa_tools = _convert_tools(tools)
        kwargs = {
            "model": model,
            "messages": oa_messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        if oa_tools:
            kwargs["tools"] = oa_tools
            kwargs["tool_choice"] = "auto"
        resp = self._client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        blocks = []
        if msg.content:
            blocks.append(SimpleNamespace(type="text", text=msg.content))
        for tc in msg.tool_calls or []:
            try:
                parsed = json.loads(tc.function.arguments or "{}")
            except Exception:
                parsed = {}
            blocks.append(
                SimpleNamespace(
                    type="tool_use",
                    id=tc.id,
                    name=tc.function.name,
                    input=parsed,
                )
            )
        stop_reason = "tool_use" if (msg.tool_calls and len(msg.tool_calls) > 0) else "end_turn"
        return SimpleNamespace(content=blocks, stop_reason=stop_reason)


class _OpenAIAnthropicCompatClient:
    def __init__(self, api_key: str = None, base_url: str = None):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self.messages = _OpenAIAnthropicCompatMessages(self._client)


def _configure_openai_backend():
    base.client = _OpenAIAnthropicCompatClient(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )
    base.MODEL = (
        os.getenv("OPENAI_MODEL_ID")
        or os.getenv("OPENAI_MODEL")
        or os.getenv("MODEL_ID")
    )
    if not base.MODEL:
        raise RuntimeError("Missing model env var: set OPENAI_MODEL_ID / OPENAI_MODEL / MODEL_ID")


def main():
    _configure_openai_backend()
    history = []
    while True:
        try:
            query = input("\033[36ms_full_openai >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        if query.strip() == "/compact":
            if history:
                print("[manual compact via /compact]")
                history[:] = base.auto_compact(history)
            continue
        if query.strip() == "/tasks":
            print(base.TASK_MGR.list_all())
            continue
        if query.strip() == "/team":
            print(base.TEAM.list_all())
            continue
        if query.strip() == "/inbox":
            print(json.dumps(base.BUS.read_inbox("lead"), indent=2))
            continue
        history.append({"role": "user", "content": query})
        base.agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()


if __name__ == "__main__":
    main()
