from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any, Protocol

from coding_deepgent.compact.artifacts import format_compact_summary

COMPACT_SUMMARY_PROMPT = """Create a detailed compact summary of the conversation above.

Respond with text only. Do not call tools.
Use this shape:

<analysis>
Brief private checklist to ensure the summary is complete.
</analysis>

<summary>
Include the user's intent, decisions made, files or code touched, errors and fixes, current work, and the next continuation step if one is known.
</summary>
"""


class CompactSummarizer(Protocol):
    def invoke(self, messages: list[dict[str, Any]]) -> Any: ...


def build_compact_summary_prompt(custom_instructions: str | None = None) -> str:
    if custom_instructions and custom_instructions.strip():
        return (
            f"{COMPACT_SUMMARY_PROMPT}\n\n"
            f"Additional instructions:\n{custom_instructions.strip()}"
        )
    return COMPACT_SUMMARY_PROMPT


def build_compact_summary_request(
    messages: list[dict[str, Any]],
    *,
    custom_instructions: str | None = None,
    assist_context: str | None = None,
) -> list[dict[str, Any]]:
    request = [*deepcopy(messages)]
    if assist_context and assist_context.strip():
        request.append(
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": assist_context.strip(),
                    }
                ],
            }
        )
    request.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": build_compact_summary_prompt(custom_instructions),
                }
            ],
        }
    )
    return request


def generate_compact_summary(
    messages: list[dict[str, Any]],
    summarizer: CompactSummarizer | Callable[[list[dict[str, Any]]], Any],
    *,
    custom_instructions: str | None = None,
    assist_context: str | None = None,
) -> str:
    request = build_compact_summary_request(
        messages,
        custom_instructions=custom_instructions,
        assist_context=assist_context,
    )
    response = (
        summarizer(request)
        if callable(summarizer) and not hasattr(summarizer, "invoke")
        else summarizer.invoke(request)  # type: ignore[union-attr]
    )
    summary = format_compact_summary(_extract_text(response))
    if not summary:
        raise ValueError("compact summarizer returned an empty summary")
    return summary


def _extract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        if "content" in value:
            return _extract_text(value["content"])
        if "messages" in value and isinstance(value["messages"], list):
            for message in reversed(value["messages"]):
                message_text = _extract_text(message)
                if message_text:
                    return message_text
            return ""
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                if item.get("type") in {"text", "output_text"} and item.get("text"):
                    parts.append(str(item["text"]))
                elif item.get("content"):
                    parts.append(_extract_text(item["content"]))
                continue
            item_text = getattr(item, "text", None)
            if isinstance(item_text, str):
                parts.append(item_text)
        return "\n".join(part for part in parts if part).strip()

    content = getattr(value, "content", None)
    if content is not None:
        return _extract_text(content)
    return str(value).strip()
