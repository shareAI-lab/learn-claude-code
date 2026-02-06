"""
TodoManager - Structured task tracking with constraints.

Key Design Decisions:
    - Max 20 items: Prevents infinite task lists
    - One in_progress: Forces focus on one thing at a time
    - Required fields: content, status, activeForm

The activeForm field is the PRESENT TENSE form of what's happening,
shown when status is "in_progress". Example:
    content="Add tests", activeForm="Adding unit tests..."
"""


class TodoManager:
    """Task list manager with enforced constraints."""

    def __init__(self):
        self.items = []

    def update(self, items: list) -> str:
        """
        Validate and update the todo list.

        Args:
            items: List of dicts with content, status, activeForm

        Returns:
            Rendered text view of the todo list

        Raises:
            ValueError: If validation fails
        """
        validated = []
        in_progress = 0

        for i, item in enumerate(items):
            content = str(item.get("content", "")).strip()
            status = str(item.get("status", "pending")).lower()
            active = str(item.get("activeForm", "")).strip()

            if not content or not active:
                raise ValueError(f"Item {i}: content and activeForm required")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Item {i}: invalid status")
            if status == "in_progress":
                in_progress += 1

            validated.append({
                "content": content,
                "status": status,
                "activeForm": active
            })

        if in_progress > 1:
            raise ValueError("Only one task can be in_progress")

        self.items = validated[:20]
        return self.render()

    def render(self) -> str:
        """Render the todo list as human-readable text."""
        if not self.items:
            return "No todos."
        lines = []
        for t in self.items:
            mark = "[x]" if t["status"] == "completed" else \
                   "[>]" if t["status"] == "in_progress" else "[ ]"
            lines.append(f"{mark} {t['content']}")
        done = sum(1 for t in self.items if t["status"] == "completed")
        return "\n".join(lines) + f"\n({done}/{len(self.items)} done)"


# Global instance
TODO = TodoManager()
