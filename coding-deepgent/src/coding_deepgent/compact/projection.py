from __future__ import annotations

from copy import deepcopy
from typing import Any

from coding_deepgent.compact.budget import apply_tool_result_budget


def project_messages(
    messages: list[dict[str, Any]],
    *,
    max_chars_per_message: int | None = None,
) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []

    for message in messages:
        normalized = _normalize_message(
            message, max_chars_per_message=max_chars_per_message
        )
        if projected and _can_merge_text_messages(projected[-1], normalized):
            merged = f"{projected[-1]['content']}\n\n{normalized['content']}"
            projected[-1]["content"] = _project_content(
                merged, max_chars_per_message=max_chars_per_message
            )
            continue
        projected.append(normalized)

    return projected


def _normalize_message(
    message: dict[str, Any],
    *,
    max_chars_per_message: int | None,
) -> dict[str, Any]:
    normalized = deepcopy(message)
    normalized["role"] = message.get("role", "user")
    normalized["content"] = _project_content(
        message.get("content", ""), max_chars_per_message=max_chars_per_message
    )
    return normalized


def _project_content(content: Any, *, max_chars_per_message: int | None) -> Any:
    if isinstance(content, str) and max_chars_per_message is not None:
        return apply_tool_result_budget(content, max_chars=max_chars_per_message).text
    return content


def _can_merge_text_messages(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("role") != right.get("role"):
        return False
    if not isinstance(left.get("content"), str) or not isinstance(
        right.get("content"), str
    ):
        return False
    if set(left.keys()) != {"role", "content"}:
        return False
    if set(right.keys()) != {"role", "content"}:
        return False
    return True
