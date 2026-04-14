from __future__ import annotations

from coding_deepgent.compact import TRUNCATION_MARKER, project_messages


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
    messages = [
        {"role": "user", "content": "plain"},
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
