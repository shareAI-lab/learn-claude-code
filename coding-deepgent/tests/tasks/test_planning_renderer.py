from __future__ import annotations

from coding_deepgent.renderers.planning import (
    TerminalPlanRenderer,
    reminder_text,
    render_plan_items,
)
from coding_deepgent.todo.state import TodoItemState


def test_terminal_plan_renderer_golden_output() -> None:
    items: list[TodoItemState] = [
        {"content": "Inspect repo", "status": "completed", "activeForm": "Inspecting"},
        {
            "content": "Implement renderer seam",
            "status": "in_progress",
            "activeForm": "Implementing",
        },
        {"content": "Verify behavior", "status": "pending", "activeForm": "Verifying"},
    ]

    assert render_plan_items(items) == (
        "[x] Inspect repo\n"
        "[>] Implement renderer seam (Implementing)\n"
        "[ ] Verify behavior\n"
        "\n"
        "(1/3 completed)"
    )


def test_terminal_plan_renderer_empty_plan_and_reminder_threshold() -> None:
    renderer = TerminalPlanRenderer()
    items: list[TodoItemState] = [
        {"content": "Keep going", "status": "pending", "activeForm": "Keeping"}
    ]

    assert renderer.render_plan_items([]) == "No session plan yet."
    assert reminder_text([], 99) is None
    assert renderer.reminder_text(items, 2) is None
    assert renderer.reminder_text(items, 3) == (
        "<reminder>Refresh your current plan before continuing.</reminder>"
    )
