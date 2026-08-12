"""Anthropic SDK request and streaming boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homework.agent_app.core.recovery import PartialStreamError


@dataclass(frozen=True, slots=True)
class AnthropicAdapter:
    client: Any

    def create(
        self,
        *,
        system,
        messages,
        model,
        max_tokens,
        tools,
    ):
        request = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if system is not None:
            request["system"] = system
        if tools is not None:
            request["tools"] = tools
        return self.client.messages.create(**request)

    def create_streaming(
        self,
        *,
        system,
        messages,
        model,
        max_tokens,
        tools,
    ):
        chunks = []
        try:
            with self.client.messages.stream(
                model=model,
                system=system,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
            ) as stream:
                for chunk in stream.text_stream:
                    if not chunk:
                        continue
                    chunks.append(chunk)
                    print(chunk, end="", flush=True)
                return stream.get_final_message()
        except Exception as exc:
            if chunks:
                raise PartialStreamError("".join(chunks), exc) from exc
            raise
        finally:
            if chunks and not chunks[-1].endswith("\n"):
                print()
