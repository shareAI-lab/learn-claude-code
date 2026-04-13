from __future__ import annotations

from dataclasses import dataclass

TRUNCATION_MARKER = "\n...[tool result truncated by coding-deepgent budget]"


@dataclass(frozen=True, slots=True)
class BudgetedText:
    text: str
    original_length: int
    truncated: bool
    omitted_chars: int = 0


def apply_tool_result_budget(text: str, *, max_chars: int) -> BudgetedText:
    if max_chars < len(TRUNCATION_MARKER) + 1:
        raise ValueError("max_chars must leave room for truncation marker")
    original_length = len(text)
    if original_length <= max_chars:
        return BudgetedText(text=text, original_length=original_length, truncated=False)
    keep = max_chars - len(TRUNCATION_MARKER)
    return BudgetedText(
        text=text[:keep] + TRUNCATION_MARKER,
        original_length=original_length,
        truncated=True,
        omitted_chars=original_length - keep,
    )
