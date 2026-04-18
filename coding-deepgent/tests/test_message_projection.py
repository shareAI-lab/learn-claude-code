from __future__ import annotations

from typing import Any

from coding_deepgent.compact import (
    ORPHAN_TOOL_RESULT_TOMBSTONE,
    TRUNCATION_MARKER,
    project_messages,
    project_messages_with_stats,
)


def test_project_messages_merges_only_plain_same_role_text_messages() -> None:
    messages = [
        {"role": "user", "content": "first"},
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "third"},
    ]

    assert project_messages(messages) == [
        {"role": "user", "content": "first\n\nsecond"},
        {"role": "assistant", "content": "third"},
    ]


def test_project_messages_preserves_structured_content_and_does_not_merge_it() -> None:
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "plain"},
        {
            "role": "assistant",
            "content": [{"type": "tool_use", "id": "call-1", "name": "read_file"}],
        },
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "call-1", "content": "ok"}],
        },
        {"role": "user", "content": "tail"},
    ]

    assert project_messages(messages) == messages


def test_project_messages_preserves_extra_metadata_by_not_merging() -> None:
    messages = [
        {"role": "assistant", "content": "part 1", "id": "m1"},
        {"role": "assistant", "content": "part 2"},
    ]

    assert project_messages(messages) == [
        {"role": "assistant", "content": "part 1", "id": "m1"},
        {"role": "assistant", "content": "part 2"},
    ]


def test_project_messages_can_apply_per_message_budget() -> None:
    messages = [{"role": "user", "content": "x" * 120}]

    projected = project_messages(messages, max_chars_per_message=len(TRUNCATION_MARKER) + 5)

    assert projected == [
        {"role": "user", "content": "xxxxx" + TRUNCATION_MARKER},
    ]


def test_project_messages_tombstones_orphan_tool_result_blocks() -> None:
    result = project_messages_with_stats(
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "missing-call",
                        "content": "raw output",
                    }
                ],
            }
        ]
    )

    assert result.messages == [
        {
            "role": "user",
            "content": [{"type": "text", "text": ORPHAN_TOOL_RESULT_TOMBSTONE}],
        }
    ]
    assert result.repair_stats.orphan_tombstoned == 1
    assert result.repair_stats.reason == "missing_tool_use"


def test_project_messages_preserves_matched_tool_result_blocks() -> None:
    messages: list[dict[str, Any]] = [
        {
            "role": "assistant",
            "content": [{"type": "tool_use", "id": "call-1", "name": "read_file"}],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call-1", "content": "ok"}
            ],
        },
    ]

    result = project_messages_with_stats(messages)

    assert result.messages == messages
    assert result.repair_stats.orphan_tombstoned == 0


def test_project_messages_preserves_pairing_for_dynamic_extension_tool_names() -> None:
    messages: list[dict[str, Any]] = [
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "call-ext", "name": "mcp__docs__lookup"}
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "call-ext",
                    "content": "doc result",
                }
            ],
        },
    ]

    result = project_messages_with_stats(messages)

    assert result.messages == messages
    assert result.repair_stats.orphan_tombstoned == 0
