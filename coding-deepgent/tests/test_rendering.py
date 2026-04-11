from __future__ import annotations

from coding_deepgent.rendering import extract_text, normalize_messages


def test_extract_text_reads_block_lists() -> None:
    content = [
        {"type": "text", "text": "alpha"},
        {"type": "output_text", "text": "beta"},
        {"type": "ignored", "content": "gamma"},
    ]

    assert extract_text(content) == "alpha\nbeta\ngamma"


def test_normalize_messages_merges_visible_history() -> None:
    messages = [
        {"role": "user", "content": "first"},
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "third"},
        {"role": "assistant", "content": "fourth"},
    ]

    assert normalize_messages(messages) == [
        {"role": "user", "content": "first\n\nsecond"},
        {"role": "assistant", "content": "third\n\nfourth"},
    ]
