from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

COMPACT_BOUNDARY_PREFIX = "coding-deepgent compact boundary"
COMPACT_SUMMARY_PREFIX = (
    "This session is being continued from a compacted conversation."
)
COMPACT_METADATA_KEY = "coding_deepgent_compact"
COLLAPSE_BOUNDARY_PREFIX = "coding-deepgent collapse boundary"
COLLAPSE_SUMMARY_PREFIX = (
    "This session is being continued from a collapsed conversation."
)
COLLAPSE_METADATA_KEY = "coding_deepgent_collapse"


@dataclass(frozen=True, slots=True)
class CompactArtifact:
    trigger: Literal["manual"]
    summary: str
    original_message_count: int
    summarized_message_count: int
    kept_message_count: int
    start_message_id: str | None
    end_message_id: str | None
    covered_message_ids: tuple[str, ...] | None
    messages: list[dict[str, Any]]


def compact_messages_with_summary(
    messages: list[dict[str, Any]],
    *,
    summary: str,
    keep_last: int = 4,
    start_message_id: str | None = None,
    end_message_id: str | None = None,
    covered_message_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
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
            start_message_id=start_message_id,
            end_message_id=end_message_id,
            covered_message_ids=covered_message_ids,
            metadata=metadata,
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
        start_message_id=start_message_id,
        end_message_id=end_message_id,
        covered_message_ids=tuple(covered_message_ids)
        if covered_message_ids is not None
        else None,
        messages=artifact_messages,
    )


def build_compact_boundary_message(
    *,
    trigger: str,
    original_message_count: int,
    summarized_message_count: int,
    kept_message_count: int,
    start_message_id: str | None = None,
    end_message_id: str | None = None,
    covered_message_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    compact_metadata_payload: dict[str, Any] = {
        "kind": "boundary",
        "trigger": trigger,
        "original_message_count": original_message_count,
        "summarized_message_count": summarized_message_count,
        "kept_message_count": kept_message_count,
    }
    if start_message_id is not None:
        compact_metadata_payload["start_message_id"] = start_message_id
    if end_message_id is not None:
        compact_metadata_payload["end_message_id"] = end_message_id
    if covered_message_ids:
        compact_metadata_payload["covered_message_ids"] = list(covered_message_ids)
    if metadata is not None:
        compact_metadata_payload["metadata"] = deepcopy(metadata)
    return {
        "role": "system",
        "metadata": {COMPACT_METADATA_KEY: compact_metadata_payload},
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
        "metadata": {
            COMPACT_METADATA_KEY: {
                "kind": "summary",
                "summary": summary,
            }
        },
        "content": [
            {
                "type": "text",
                "text": f"{COMPACT_SUMMARY_PREFIX}\n\nSummary:\n{summary}",
            }
        ],
    }


def build_collapse_boundary_message(
    *,
    trigger: str,
    original_message_count: int,
    collapsed_message_count: int,
    kept_message_count: int,
    start_message_id: str,
    end_message_id: str,
    covered_message_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    collapse_metadata_payload: dict[str, Any] = {
        "kind": "boundary",
        "trigger": trigger,
        "original_message_count": original_message_count,
        "collapsed_message_count": collapsed_message_count,
        "kept_message_count": kept_message_count,
        "start_message_id": start_message_id,
        "end_message_id": end_message_id,
    }
    if covered_message_ids:
        collapse_metadata_payload["covered_message_ids"] = list(covered_message_ids)
    if metadata is not None:
        collapse_metadata_payload["metadata"] = deepcopy(metadata)
    return {
        "role": "system",
        "metadata": {COLLAPSE_METADATA_KEY: collapse_metadata_payload},
        "content": [
            {
                "type": "text",
                "text": (
                    f"{COLLAPSE_BOUNDARY_PREFIX}: trigger={trigger}; "
                    f"original_messages={original_message_count}; "
                    f"collapsed_messages={collapsed_message_count}; "
                    f"kept_messages={kept_message_count}"
                ),
            }
        ],
    }


def build_collapse_summary_message(summary: str) -> dict[str, Any]:
    return {
        "role": "user",
        "metadata": {
            COLLAPSE_METADATA_KEY: {
                "kind": "summary",
                "summary": summary,
            }
        },
        "content": [
            {
                "type": "text",
                "text": f"{COLLAPSE_SUMMARY_PREFIX}\n\nSummary:\n{summary}",
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
    if compact_metadata(message) is not None:
        return True
    text = _message_text(message)
    return text.startswith(COMPACT_BOUNDARY_PREFIX) or text.startswith(
        COMPACT_SUMMARY_PREFIX
    )


def compact_metadata(message: dict[str, Any]) -> dict[str, Any] | None:
    metadata = message.get("metadata")
    if not isinstance(metadata, dict):
        return None
    compact = metadata.get(COMPACT_METADATA_KEY)
    return compact if isinstance(compact, dict) else None


def compact_record_from_messages(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    boundary: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    for message in messages:
        metadata = compact_metadata(message)
        if metadata is None:
            continue
        if metadata.get("kind") == "boundary":
            boundary = metadata
            summary = None
        elif metadata.get("kind") == "summary" and boundary is not None:
            summary = metadata

    if boundary is None or summary is None:
        return None
    summary_text = summary.get("summary")
    if not isinstance(summary_text, str) or not summary_text.strip():
        return None
    start_message_id = boundary.get("start_message_id")
    end_message_id = boundary.get("end_message_id")
    covered_message_ids = boundary.get("covered_message_ids")
    metadata = boundary.get("metadata")
    if not isinstance(start_message_id, str) or not start_message_id.strip():
        return None
    if not isinstance(end_message_id, str) or not end_message_id.strip():
        return None
    if covered_message_ids is not None and (
        not isinstance(covered_message_ids, list)
        or not covered_message_ids
        or any(not isinstance(item, str) or not item.strip() for item in covered_message_ids)
    ):
        return None
    if metadata is not None and not isinstance(metadata, dict):
        return None
    return {
        "trigger": str(boundary.get("trigger", "manual")),
        "summary": summary_text.strip(),
        "start_message_id": start_message_id.strip(),
        "end_message_id": end_message_id.strip(),
        "covered_message_ids": [item.strip() for item in covered_message_ids]
        if isinstance(covered_message_ids, list)
        else None,
        "metadata": deepcopy(metadata) if isinstance(metadata, dict) else None,
    }


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
