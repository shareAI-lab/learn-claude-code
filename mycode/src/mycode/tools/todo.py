"""TodoWrite 工具: 短期 checklist。

存在内存里,不落盘。约束:
- 最多 20 条
- 最多 1 条 in_progress
- 状态: pending / in_progress / completed
对齐 TOOLS.md §3.1。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .registry import Tool, ToolRegistry


MAX_TODO_ITEMS = 20
_VALID_STATUS = {"pending", "in_progress", "completed"}


@dataclass
class TodoManager:
    items: list[dict[str, str]] = field(default_factory=list)

    def update(self, raw_items: list[dict[str, Any]]) -> str:
        validated: list[dict[str, str]] = []
        in_progress_count = 0
        for i, item in enumerate(raw_items):
            content = str(item.get("content", "")).strip()
            status = str(item.get("status", "pending")).lower().strip()
            active = str(item.get("activeForm", "")).strip()
            if not content:
                return f"Error: item {i}: content required"
            if status not in _VALID_STATUS:
                return f"Error: item {i}: invalid status '{status}'"
            if not active:
                return f"Error: item {i}: activeForm required"
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"content": content, "status": status, "activeForm": active})
        if len(validated) > MAX_TODO_ITEMS:
            return f"Error: max {MAX_TODO_ITEMS} todos, got {len(validated)}"
        if in_progress_count > 1:
            return "Error: only one in_progress allowed"
        self.items = validated
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "(no todos)"
        lines: list[str] = []
        mark = {"completed": "[x]", "in_progress": "[>]", "pending": "[ ]"}
        for item in self.items:
            m = mark.get(item["status"], "[?]")
            suffix = ""
            if item["status"] == "in_progress":
                suffix = f"  <-- {item['activeForm']}"
            lines.append(f"{m} {item['content']}{suffix}")
        done = sum(1 for t in self.items if t["status"] == "completed")
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines)

    def has_open(self) -> bool:
        return any(t["status"] != "completed" for t in self.items)


def register_todo(registry: ToolRegistry, manager: TodoManager) -> None:
    registry.register(
        Tool(
            name="TodoWrite",
            description=(
                "Maintain a short task checklist. Pass the full list each time — "
                "it replaces the prior list. Max 20 items, only one may be in_progress."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "maxItems": MAX_TODO_ITEMS,
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "status": {
                                    "type": "string",
                                    "enum": sorted(_VALID_STATUS),
                                },
                                "activeForm": {"type": "string"},
                            },
                            "required": ["content", "status", "activeForm"],
                        },
                    }
                },
                "required": ["items"],
            },
            handler=lambda **kw: manager.update(kw["items"]),
        )
    )
