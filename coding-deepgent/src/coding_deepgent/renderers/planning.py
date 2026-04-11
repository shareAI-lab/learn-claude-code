from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from coding_deepgent.state import TodoItemState

PLAN_REMINDER_INTERVAL = 3


class PlanRenderer(Protocol):
    """Render planning state for a display surface."""

    def render_plan_items(self, items: list[TodoItemState]) -> str:
        """Return display text for the current session plan."""
        ...

    def reminder_text(
        self,
        items: list[TodoItemState],
        rounds_since_update: int,
    ) -> str | None:
        """Return reminder text when the current plan is stale."""
        ...


@dataclass(frozen=True)
class TerminalPlanRenderer:
    """Terminal-compatible renderer for the TodoWrite planning display."""

    reminder_interval: int = PLAN_REMINDER_INTERVAL

    def render_plan_items(self, items: list[TodoItemState]) -> str:
        if not items:
            return "No session plan yet."

        lines: list[str] = []
        for item in items:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[
                item["status"]
            ]
            line = f"{marker} {item['content']}"
            active_form = item.get("activeForm", "")
            if item["status"] == "in_progress" and active_form:
                line += f" ({active_form})"
            lines.append(line)

        completed = sum(1 for item in items if item["status"] == "completed")
        lines.append(f"\n({completed}/{len(items)} completed)")
        return "\n".join(lines)

    def reminder_text(
        self,
        items: list[TodoItemState],
        rounds_since_update: int,
    ) -> str | None:
        if not items or rounds_since_update < self.reminder_interval:
            return None
        return "<reminder>Refresh your current plan before continuing.</reminder>"


DEFAULT_PLAN_RENDERER = TerminalPlanRenderer()


def render_plan_items(
    items: list[TodoItemState],
    renderer: PlanRenderer = DEFAULT_PLAN_RENDERER,
) -> str:
    """Compatibility wrapper for the default planning renderer."""

    return renderer.render_plan_items(items)


def reminder_text(
    items: list[TodoItemState],
    rounds_since_update: int,
    renderer: PlanRenderer = DEFAULT_PLAN_RENDERER,
) -> str | None:
    """Compatibility wrapper for the default planning reminder."""

    return renderer.reminder_text(items, rounds_since_update)
