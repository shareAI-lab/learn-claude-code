from __future__ import annotations

from typing import Any


def _message_content(message: Any) -> Any:
    if isinstance(message, dict):
        return message.get("content", "")
    return getattr(message, "content", "")


def extract_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") in {"text", "output_text"} and block.get("text"):
                    texts.append(str(block["text"]))
                elif block.get("content"):
                    texts.append(str(block["content"]))
                continue
            text = getattr(block, "text", None)
            if text:
                texts.append(str(text))
        return "\n".join(texts).strip()

    text_attr = getattr(content, "text", None)
    if isinstance(text_attr, str):
        return text_attr.strip()
    if callable(text_attr):
        try:
            return str(text_attr()).strip()
        except TypeError:
            pass
    return str(content).strip()


def latest_assistant_text(result: Any) -> str:
    if isinstance(result, dict):
        messages = result.get("messages") or []
        for message in reversed(messages):
            role = (
                message.get("role")
                if isinstance(message, dict)
                else getattr(message, "type", "")
            )
            if role in {"assistant", "ai"}:
                text = extract_text(_message_content(message))
                if text:
                    return text
        if messages:
            return extract_text(_message_content(messages[-1]))
    return extract_text(_message_content(result))


def normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for message in messages:
        cleaned.append(
            {
                "role": message.get("role", "user"),
                "content": message.get("content", ""),
            }
        )

    if not cleaned:
        return cleaned

    merged = [cleaned[0]]
    for message in cleaned[1:]:
        if message["role"] == merged[-1]["role"]:
            merged[-1]["content"] = f"{merged[-1]['content']}\n\n{message['content']}"
        else:
            merged.append(message)
    return merged
