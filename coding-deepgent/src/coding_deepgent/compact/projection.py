from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from coding_deepgent.compact.budget import apply_tool_result_budget

ORPHAN_TOOL_RESULT_TOMBSTONE = (
    "[Orphaned tool_result tombstoned: missing matching tool_use]"
)


@dataclass(frozen=True, slots=True)
class ProjectionRepairStats:
    orphan_tombstoned: int = 0
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectMessagesResult:
    messages: list[dict[str, Any]]
    repair_stats: ProjectionRepairStats = ProjectionRepairStats()


def project_messages(
    messages: list[dict[str, Any]],
    *,
    max_chars_per_message: int | None = None,
) -> list[dict[str, Any]]:
    return project_messages_with_stats(
        messages,
        max_chars_per_message=max_chars_per_message,
    ).messages


def project_messages_with_stats(
    messages: list[dict[str, Any]],
    *,
    max_chars_per_message: int | None = None,
) -> ProjectMessagesResult:
    projected: list[dict[str, Any]] = []
    known_tool_use_ids: set[str] = set()
    orphan_tombstoned = 0

    for message in messages:
        normalized = _normalize_message(
            message, max_chars_per_message=max_chars_per_message
        )
        current_tool_use_ids = _message_tool_use_ids(normalized)
        normalized, message_tombstoned = _repair_orphan_tool_results(
            normalized,
            known_tool_use_ids=known_tool_use_ids | current_tool_use_ids,
        )
        orphan_tombstoned += message_tombstoned
        known_tool_use_ids.update(current_tool_use_ids)
        if projected and _can_merge_text_messages(projected[-1], normalized):
            merged = f"{projected[-1]['content']}\n\n{normalized['content']}"
            projected[-1]["content"] = _project_content(
                merged, max_chars_per_message=max_chars_per_message
            )
            continue
        projected.append(normalized)

    return ProjectMessagesResult(
        messages=projected,
        repair_stats=ProjectionRepairStats(
            orphan_tombstoned=orphan_tombstoned,
            reason="missing_tool_use" if orphan_tombstoned else None,
        ),
    )


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


def _repair_orphan_tool_results(
    message: dict[str, Any],
    *,
    known_tool_use_ids: set[str],
) -> tuple[dict[str, Any], int]:
    content = message.get("content")
    if not isinstance(content, list):
        return message, 0
    repaired_blocks: list[Any] = []
    tombstoned = 0
    changed = False
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            repaired_blocks.append(block)
            continue
        tool_use_id = block.get("tool_use_id")
        if isinstance(tool_use_id, str) and tool_use_id in known_tool_use_ids:
            repaired_blocks.append(block)
            continue
        repaired_blocks.append({"type": "text", "text": ORPHAN_TOOL_RESULT_TOMBSTONE})
        tombstoned += 1
        changed = True
    if not changed:
        return message, 0
    repaired = dict(message)
    repaired["content"] = repaired_blocks
    return repaired, tombstoned


def _message_tool_use_ids(message: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    content = message.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_use_id = block.get("id")
                if isinstance(tool_use_id, str) and tool_use_id:
                    ids.add(tool_use_id)
    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list):
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            tool_call_id = tool_call.get("id")
            if isinstance(tool_call_id, str) and tool_call_id:
                ids.add(tool_call_id)
    return ids
