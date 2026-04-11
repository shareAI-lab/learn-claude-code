from __future__ import annotations

from pathlib import Path

from agents_deepagents import s06_context_compact as s06


def message(
    message_id: str,
    role: s06.MessageRole,
    content: str,
    *,
    name: str | None = None,
    tool_call_id: str | None = None,
    **metadata: object,
) -> s06.ContextMessage:
    return s06.ContextMessage(
        id=message_id,
        role=role,
        content=content,
        name=name,
        tool_call_id=tool_call_id,
        metadata=dict(metadata),
    )


def summarizer(messages: list[s06.ContextMessage] | tuple[s06.ContextMessage, ...]) -> str:
    return "summary:" + ",".join(message.id for message in messages)


def test_apply_tool_result_budget_persists_large_outputs(tmp_path: Path) -> None:
    original = "A" * 160
    state = s06.ContextCompressionState(
        messages=[
            message("u1", "user", "Inspect the repo"),
            message("a1", "assistant", "Running tool"),
            message(
                "t1",
                "tool",
                original,
                name="bash",
                tool_call_id="tool-1",
                group_id="round-1",
            ),
        ]
    )

    compacted = s06.apply_tool_result_budget(
        state,
        storage_dir=tmp_path,
        per_tool_threshold=80,
        per_message_budget=1_000,
        preview_chars=40,
    )

    assert compacted.messages[2].content == original
    assert compacted.model_messages[2].content.startswith("<persisted-output>")
    persisted = compacted.persisted_outputs["tool-1"]
    assert (tmp_path / "tool-1.txt").read_text() == original
    assert persisted.preview == "A" * 23 + "... [truncated]"
    assert compacted.compact_boundaries[-1].kind == "tool_result_budget"


def test_aggregate_budget_reuses_frozen_replacement_decisions(tmp_path: Path) -> None:
    first_state = s06.ContextCompressionState(
        messages=[
            message("u1", "user", "Need two tool results"),
            message(
                "t-small",
                "tool",
                "S" * 80,
                name="bash",
                tool_call_id="tool-small",
                group_id="round-1",
            ),
            message(
                "t-large",
                "tool",
                "L" * 140,
                name="read_file",
                tool_call_id="tool-large",
                group_id="round-1",
            ),
        ]
    )
    first_result = s06.apply_tool_result_budget(
        first_state,
        storage_dir=tmp_path,
        per_tool_threshold=999,
        per_message_budget=210,
        preview_chars=50,
    )

    assert "tool-large" in first_result.replacement_decisions

    second_state = s06.ContextCompressionState(
        messages=[
            message("u2", "user", "Replay the same round"),
            message(
                "t-small-2",
                "tool",
                "S" * 80,
                name="bash",
                tool_call_id="tool-small",
                group_id="round-2",
            ),
            message(
                "t-large-2",
                "tool",
                "L" * 140,
                name="read_file",
                tool_call_id="tool-large",
                group_id="round-2",
            ),
        ],
        persisted_outputs=first_result.persisted_outputs,
        replacement_decisions=first_result.replacement_decisions,
    )
    second_result = s06.apply_tool_result_budget(
        second_state,
        storage_dir=tmp_path,
        per_tool_threshold=999,
        per_message_budget=500,
        preview_chars=50,
    )

    assert second_result.model_messages[2].content.startswith("<persisted-output>")


def test_snip_projection_preserves_canonical_history() -> None:
    state = s06.ContextCompressionState(
        messages=[
            message(f"m{index}", "user" if index % 2 else "assistant", f"msg {index}")
            for index in range(1, 9)
        ]
    )

    compacted = s06.snip_projection(state, keep_last=2)

    assert len(compacted.messages) == 8
    assert [msg.id for msg in compacted.model_messages] == ["snip-1", "m7", "m8"]
    assert compacted.compact_boundaries[-1].kind == "snip"


def test_microcompact_messages_clears_older_compactable_results() -> None:
    state = s06.ContextCompressionState(
        messages=[
            message("u1", "user", "Run some tools"),
            message("t1", "tool", "bash output 1" * 10, name="bash", tool_call_id="t1"),
            message("t2", "tool", "read output 2" * 10, name="read_file", tool_call_id="t2"),
            message("t3", "tool", "not compactable" * 10, name="custom", tool_call_id="t3"),
            message("t4", "tool", "edit output 4" * 10, name="edit_file", tool_call_id="t4"),
        ]
    )

    compacted = s06.microcompact_messages(state, keep_recent=1)

    assert compacted.model_messages[1].content == s06.MICROCOMPACT_PLACEHOLDER
    assert compacted.model_messages[2].content == s06.MICROCOMPACT_PLACEHOLDER
    assert compacted.model_messages[3].content != s06.MICROCOMPACT_PLACEHOLDER
    assert compacted.model_messages[4].content != s06.MICROCOMPACT_PLACEHOLDER
    assert compacted.compact_boundaries[-1].details["cleared_tool_call_ids"] == ["t1", "t2"]


def test_context_collapse_summarizes_oldest_groups_without_splitting_tool_pair() -> None:
    state = s06.ContextCompressionState(
        messages=[
            message("u1", "user", "Need repo overview"),
            message("a1", "assistant", "Calling bash", tool_call_id="tool-1"),
            message("t1", "tool", "bash result" * 20, name="bash", tool_call_id="tool-1"),
            message("u2", "user", "Anything else?"),
            message("a2", "assistant", "Some follow-up"),
            message("u3", "user", "Keep only the recent round"),
            message("a3", "assistant", "Recent answer"),
        ]
    )

    compacted = s06.context_collapse(
        state,
        summarizer,
        collapse_threshold=40,
        keep_recent_groups=1,
    )

    assert compacted.model_messages[0].content == "[context-collapse]\nsummary:u1,a1,t1,u2,a2"
    assert [message.id for message in compacted.model_messages[1:]] == ["u3", "a3"]
    assert compacted.compact_boundaries[-1].kind == "context_collapse"
    assert {"a1", "t1"}.issubset(compacted.compact_boundaries[-1].source_message_ids)


def test_auto_compact_if_needed_builds_summary_boundary() -> None:
    state = s06.ContextCompressionState(
        messages=[
            message(f"m{index}", "user" if index % 2 else "assistant", f"content {index} " * 20)
            for index in range(1, 7)
        ]
    )

    compacted = s06.auto_compact_if_needed(
        state,
        summarizer,
        threshold=120,
        keep_recent=2,
    )

    assert compacted.model_messages[0].content.startswith("[auto-compact]")
    assert [message.id for message in compacted.model_messages[1:]] == ["m5", "m6"]
    assert compacted.compact_boundaries[-1].kind == "auto_compact"


def test_reactive_compact_on_overflow_attempts_collapse_before_fallback() -> None:
    base_state = s06.ContextCompressionState(
        messages=[
            message("u1", "user", "Old context" * 20),
            message("a1", "assistant", "Old answer" * 20),
            message("u2", "user", "Recent context" * 20),
            message("a2", "assistant", "Recent answer" * 20),
        ]
    )
    collapsed = s06.context_collapse(
        base_state,
        lambda messages: "S" * 400,
        collapse_threshold=60,
        keep_recent_groups=1,
    )

    recovered = s06.reactive_compact_on_overflow(
        collapsed,
        s06.PromptTooLongError("prompt too long"),
        summarizer,
        threshold=90,
        keep_recent=1,
        drain_summary_budget=180,
    )

    assert recovered.transitions.index("collapse_drain_retry") < recovered.transitions.index(
        "reactive_compact_retry"
    )
    assert recovered.compact_boundaries[-1].kind == "reactive_compact"
    assert recovered.model_messages[0].content.startswith("[reactive-compact]")


def test_metadata_matches_readme_disclosure() -> None:
    readme = Path("agents_deepagents/README.md").read_text(encoding="utf-8")

    for stage in s06.SOURCE_BACKED_STAGES:
        assert f"`{stage}`" in readme
    for stage in s06.INFERRED_STAGES:
        assert f"`{stage}`" in readme
    for keyword in [
        "Character counts stand in for exact tokenizer budgets.",
        "Persisted tool outputs are stored as plain text files instead of provider",
        "Snip projection and context collapse are honest teaching equivalents",
        "Auto compact omits session-memory extraction",
    ]:
        assert keyword in readme
