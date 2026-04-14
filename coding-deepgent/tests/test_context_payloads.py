from __future__ import annotations

from coding_deepgent.context_payloads import (
    DEFAULT_MAX_CHARS,
    TRUNCATION_MARKER,
    ContextPayload,
    merge_system_message_content,
    render_context_payloads,
)


def test_render_context_payloads_is_deterministic_and_sorts_by_priority() -> None:
    payloads = [
        ContextPayload(kind="memory", text="Memory B", source="mem.b", priority=200),
        ContextPayload(kind="todo", text="Todo A", source="todo.a", priority=100),
        ContextPayload(
            kind="todo_reminder",
            text="Reminder C",
            source="todo.reminder",
            priority=110,
        ),
    ]

    rendered = render_context_payloads(list(reversed(payloads)))

    assert rendered == [
        {"type": "text", "text": "Todo A"},
        {"type": "text", "text": "Reminder C"},
        {"type": "text", "text": "Memory B"},
    ]


def test_render_context_payloads_dedupes_same_kind_source_and_text() -> None:
    rendered = render_context_payloads(
        [
            ContextPayload(kind="memory", text="Same", source="memory.project"),
            ContextPayload(kind="memory", text="Same", source="memory.project"),
            ContextPayload(kind="memory", text="Same", source="memory.other"),
        ]
    )

    assert rendered == [
        {"type": "text", "text": "Same"},
        {"type": "text", "text": "Same"},
    ]


def test_render_context_payloads_bounds_output_with_truncation_marker() -> None:
    text = "x" * (DEFAULT_MAX_CHARS + 100)
    rendered = render_context_payloads(
        [ContextPayload(kind="memory", text=text, source="memory.project")]
    )

    assert len(rendered) == 1
    assert len(rendered[0]["text"]) == DEFAULT_MAX_CHARS
    assert rendered[0]["text"].endswith(TRUNCATION_MARKER)
    assert "x" * 100 not in rendered[0]["text"][-100:]


def test_merge_system_message_content_preserves_existing_blocks() -> None:
    current = [{"type": "text", "text": "Base"}]
    merged = merge_system_message_content(
        current,
        [ContextPayload(kind="todo", text="Current session todos:\n- one", source="todo.current")],
    )

    assert merged == [
        {"type": "text", "text": "Base"},
        {"type": "text", "text": "Current session todos:\n- one"},
    ]
