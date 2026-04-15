from __future__ import annotations

from typing import Any

import pytest

from coding_deepgent.compact import (
    build_compact_summary_prompt,
    build_compact_summary_request,
    generate_compact_summary,
)


class FakeSummarizer:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.requests: list[list[dict[str, Any]]] = []

    def invoke(self, messages: list[dict[str, Any]]) -> Any:
        self.requests.append(messages)
        return self.response


def test_build_compact_summary_request_appends_prompt_without_mutating_messages() -> None:
    messages = [{"role": "user", "content": "hello"}]

    request = build_compact_summary_request(
        messages, custom_instructions="Focus on code changes."
    )

    assert messages == [{"role": "user", "content": "hello"}]
    assert request[:-1] == messages
    assert request[-1]["role"] == "user"
    assert "Create a detailed compact summary" in str(request[-1]["content"])
    assert "Focus on code changes." in str(request[-1]["content"])


def test_build_compact_summary_request_includes_session_memory_assist() -> None:
    request = build_compact_summary_request(
        [{"role": "user", "content": "hello"}],
        assist_context="Session memory artifact:\nKeep repo focus.",
    )

    assert request[-2]["role"] == "system"
    assert "Session memory artifact" in str(request[-2]["content"])
    assert request[-1]["role"] == "user"


def test_generate_compact_summary_invokes_summarizer_and_formats_output() -> None:
    summarizer = FakeSummarizer(
        {
            "content": [
                {
                    "type": "text",
                    "text": (
                        "<analysis>drop this</analysis>"
                        "<summary>Keep the compact summary.</summary>"
                    ),
                }
            ]
        }
    )

    summary = generate_compact_summary(
        [{"role": "user", "content": "old"}],
        summarizer,
    )

    assert summary == "Keep the compact summary."
    assert len(summarizer.requests) == 1
    assert summarizer.requests[0][0] == {"role": "user", "content": "old"}


def test_generate_compact_summary_passes_session_memory_assist_to_summarizer() -> None:
    summarizer = FakeSummarizer("<summary>Keep the compact summary.</summary>")

    generate_compact_summary(
        [{"role": "user", "content": "old"}],
        summarizer,
        assist_context="Session memory artifact:\nKeep repo focus.",
    )

    assert summarizer.requests[0][-2]["role"] == "system"
    assert "Keep repo focus." in str(summarizer.requests[0][-2]["content"])


def test_generate_compact_summary_supports_callable_summarizer() -> None:
    seen: list[list[dict[str, Any]]] = []

    def summarize(messages: list[dict[str, Any]]) -> str:
        seen.append(messages)
        return "<summary>Callable summary.</summary>"

    assert (
        generate_compact_summary([{"role": "user", "content": "old"}], summarize)
        == "Callable summary."
    )
    assert seen


def test_generate_compact_summary_rejects_empty_output() -> None:
    with pytest.raises(ValueError, match="empty summary"):
        generate_compact_summary(
            [{"role": "user", "content": "old"}],
            FakeSummarizer("<analysis>only scratchpad</analysis>"),
        )


def test_build_compact_summary_prompt_omits_blank_custom_instructions() -> None:
    assert "Additional instructions" not in build_compact_summary_prompt(" ")
