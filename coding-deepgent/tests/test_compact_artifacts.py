from __future__ import annotations

from copy import deepcopy

import pytest

from coding_deepgent.compact import (
    COMPACT_BOUNDARY_PREFIX,
    COMPACT_METADATA_KEY,
    COMPACT_SUMMARY_PREFIX,
    compact_messages_with_summary,
    format_compact_summary,
    project_messages,
)


def _text(message: dict[str, object]) -> str:
    content = message["content"]
    if isinstance(content, list):
        return "\n".join(
            str(block.get("text", ""))
            for block in content
            if isinstance(block, dict)
        )
    return str(content)


def test_compact_messages_builds_boundary_summary_and_preserved_tail() -> None:
    messages = [
        {"role": "user", "content": "old request"},
        {"role": "assistant", "content": "old answer"},
        {"role": "user", "content": "recent request"},
        {"role": "assistant", "content": "recent answer"},
    ]

    artifact = compact_messages_with_summary(
        messages,
        summary="Earlier work established the compact boundary.",
        keep_last=2,
    )

    assert artifact.original_message_count == 4
    assert artifact.summarized_message_count == 2
    assert artifact.kept_message_count == 2
    assert _text(artifact.messages[0]).startswith(COMPACT_BOUNDARY_PREFIX)
    assert _text(artifact.messages[1]).startswith(COMPACT_SUMMARY_PREFIX)
    assert artifact.messages[0]["metadata"][COMPACT_METADATA_KEY] == {
        "kind": "boundary",
        "trigger": "manual",
        "original_message_count": 4,
        "summarized_message_count": 2,
        "kept_message_count": 2,
    }
    assert artifact.messages[1]["metadata"][COMPACT_METADATA_KEY] == {
        "kind": "summary",
        "summary": "Earlier work established the compact boundary.",
    }
    assert artifact.messages[2:] == messages[-2:]


def test_compact_summary_strips_analysis_and_unwraps_summary() -> None:
    assert (
        format_compact_summary(
            "<analysis>scratchpad</analysis>\n<summary>\nKeep this.\n</summary>"
        )
        == "Keep this."
    )


def test_compact_messages_does_not_mutate_input_messages() -> None:
    messages = [
        {"role": "user", "content": [{"type": "text", "text": "old"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "recent"}]},
    ]
    original = deepcopy(messages)

    compact_messages_with_summary(messages, summary="Summary", keep_last=1)

    assert messages == original


def test_compact_artifact_survives_message_projection_without_user_merge() -> None:
    artifact = compact_messages_with_summary(
        [
            {"role": "user", "content": "old"},
            {"role": "user", "content": "recent"},
        ],
        summary="Summary",
        keep_last=1,
    )

    assert project_messages(artifact.messages) == artifact.messages


def test_compact_messages_expands_tail_to_preserve_tool_result_pair() -> None:
    tool_use_message = {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "id": "call-1", "name": "bash", "input": {}}
        ],
    }
    tool_result_message = {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "call-1",
                "content": "ok",
            }
        ],
    }
    artifact = compact_messages_with_summary(
        [
            {"role": "user", "content": "old"},
            tool_use_message,
            tool_result_message,
        ],
        summary="Summary",
        keep_last=1,
    )

    assert artifact.kept_message_count == 2
    assert artifact.messages[-2:] == [tool_use_message, tool_result_message]


def test_compact_messages_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="messages are required"):
        compact_messages_with_summary([], summary="Summary")
    with pytest.raises(ValueError, match="summary is required"):
        compact_messages_with_summary([{"role": "user", "content": "x"}], summary=" ")
    with pytest.raises(ValueError, match="keep_last"):
        compact_messages_with_summary(
            [{"role": "user", "content": "x"}], summary="Summary", keep_last=-1
        )
