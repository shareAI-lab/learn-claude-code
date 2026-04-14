from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

COMPACT_BOUNDARY_PREFIX = "coding-deepgent compact boundary"
COMPACT_SUMMARY_PREFIX = (
    "This session is being continued from a compacted conversation."
)


@dataclass(frozen=True, slots=True)
class CompactArtifact:
    trigger: Literal["manual"]
    summary: str
    original_message_count: int
    summarized_message_count: int
    kept_message_count: int
    messages: list[dict[str, Any]]


def compact_messages_with_summary(
    messages: list[dict[str, Any]],
    *,
    summary: str,
    keep_last: int = 4,
) -> CompactArtifact:
    if not messages:
        raise ValueError("messages are required for compaction")
    if keep_last < 0:
        raise ValueError("keep_last must be non-negative")

    formatted_summary = format_compact_summary(summary)
    if not formatted_summary:
        raise ValueError("summary is required for compaction")

    clean_messages = [
        deepcopy(message)
        for message in messages
        if not is_compact_artifact_message(message)
    ]
    keep_start = _adjust_keep_start_for_tool_pairs(
        clean_messages, max(0, len(clean_messages) - keep_last)
    )
    kept_messages = clean_messages[keep_start:]
    artifact_messages = [
        build_compact_boundary_message(
            trigger="manual",
            original_message_count=len(clean_messages),
            summarized_message_count=keep_start,
            kept_message_count=len(kept_messages),
        ),
        build_compact_summary_message(formatted_summary),
        *kept_messages,
    ]
    return CompactArtifact(
        trigger="manual",
        summary=formatted_summary,
        original_message_count=len(clean_messages),
        summarized_message_count=keep_start,
        kept_message_count=len(kept_messages),
        messages=artifact_messages,
    )


def build_compact_boundary_message(
    *,
    trigger: Literal["manual"],
    original_message_count: int,
    summarized_message_count: int,
    kept_message_count: int,
) -> dict[str, Any]:
    return {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": (
                    f"{COMPACT_BOUNDARY_PREFIX}: trigger={trigger}; "
                    f"original_messages={original_message_count}; "
                    f"summarized_messages={summarized_message_count}; "
                    f"kept_messages={kept_message_count}"
                ),
            }
        ],
    }


def build_compact_summary_message(summary: str) -> dict[str, Any]:
    return {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"{COMPACT_SUMMARY_PREFIX}\n\nSummary:\n{summary}",
            }
        ],
    }


def format_compact_summary(summary: str) -> str:
    formatted = re.sub(r"<analysis>[\s\S]*?</analysis>", "", summary).strip()
    summary_match = re.search(r"<summary>([\s\S]*?)</summary>", formatted)
    if summary_match:
        formatted = summary_match.group(1) or ""
    return re.sub(r"\n\n+", "\n\n", formatted).strip()


def is_compact_artifact_message(message: dict[str, Any]) -> bool:
    text = _message_text(message)
    return text.startswith(COMPACT_BOUNDARY_PREFIX) or text.startswith(
        COMPACT_SUMMARY_PREFIX
    )


def _adjust_keep_start_for_tool_pairs(
    messages: list[dict[str, Any]],
    start_index: int,
) -> int:
    if start_index <= 0 or start_index >= len(messages):
        return start_index

    needed_tool_uses = _tool_result_ids(messages[start_index:])
    if not needed_tool_uses:
        return start_index

    kept_tool_uses = _tool_use_ids(messages[start_index:])
    missing_tool_uses = needed_tool_uses - kept_tool_uses
    adjusted = start_index
    for index in range(start_index - 1, -1, -1):
        message_tool_uses = _tool_use_ids([messages[index]])
        if missing_tool_uses & message_tool_uses:
            adjusted = index
            missing_tool_uses -= message_tool_uses
        if not missing_tool_uses:
            break
    return adjusted


def _tool_result_ids(messages: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for message in messages:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                tool_use_id = block.get("tool_use_id")
                if isinstance(tool_use_id, str) and tool_use_id:
                    ids.add(tool_use_id)
    return ids


def _tool_use_ids(messages: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for message in messages:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_use_id = block.get("id")
                if isinstance(tool_use_id, str) and tool_use_id:
                    ids.add(tool_use_id)
    return ids


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            str(block.get("text", ""))
            for block in content
            if isinstance(block, dict) and block.get("type") in {"text", "output_text"}
        ]
        return "\n".join(part for part in parts if part)
    return str(content)
