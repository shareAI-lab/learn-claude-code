from __future__ import annotations

import pytest

from coding_deepgent.compact import TRUNCATION_MARKER, apply_tool_result_budget


def test_tool_result_budget_truncates_with_marker_and_metadata() -> None:
    text = "abcdefghijklmnopqrstuvwxyz" * 3
    result = apply_tool_result_budget(text, max_chars=len(TRUNCATION_MARKER) + 3)

    assert result.truncated is True
    assert result.text == "abc" + TRUNCATION_MARKER
    assert result.original_length == len(text)
    assert result.omitted_chars == len(text) - 3


def test_tool_result_budget_leaves_small_text_unchanged_and_validates_limit() -> None:
    result = apply_tool_result_budget("abc", max_chars=len(TRUNCATION_MARKER) + 1)

    assert result.truncated is False
    assert result.text == "abc"
    assert result.omitted_chars == 0

    with pytest.raises(ValueError):
        apply_tool_result_budget("abc", max_chars=2)
