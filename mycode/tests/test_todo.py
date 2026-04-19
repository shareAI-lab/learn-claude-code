"""M1-2: TodoWrite 工具测试。"""
from __future__ import annotations

from mycode.tools.todo import MAX_TODO_ITEMS, TodoManager


def _item(content: str, status: str = "pending", active: str | None = None) -> dict:
    return {
        "content": content,
        "status": status,
        "activeForm": active or f"doing {content}",
    }


def test_empty_render():
    mgr = TodoManager()
    assert "no todos" in mgr.render()


def test_update_and_render():
    mgr = TodoManager()
    out = mgr.update([_item("a"), _item("b", "in_progress"), _item("c", "completed")])
    assert "[ ] a" in out
    assert "[>] b" in out
    assert "[x] c" in out
    assert "1/3 completed" in out


def test_reject_too_many():
    mgr = TodoManager()
    out = mgr.update([_item(f"t{i}") for i in range(MAX_TODO_ITEMS + 1)])
    assert out.startswith("Error: max")


def test_reject_multi_in_progress():
    mgr = TodoManager()
    out = mgr.update([_item("a", "in_progress"), _item("b", "in_progress")])
    assert out.startswith("Error: only one in_progress")


def test_reject_empty_content():
    mgr = TodoManager()
    out = mgr.update([{"content": "  ", "status": "pending", "activeForm": "x"}])
    assert "content required" in out


def test_reject_invalid_status():
    mgr = TodoManager()
    out = mgr.update([{"content": "a", "status": "weird", "activeForm": "x"}])
    assert "invalid status" in out


def test_has_open():
    mgr = TodoManager()
    mgr.update([_item("a", "completed"), _item("b", "pending")])
    assert mgr.has_open()
    mgr.update([_item("a", "completed")])
    assert not mgr.has_open()


def test_replace_semantics():
    mgr = TodoManager()
    mgr.update([_item("a"), _item("b")])
    mgr.update([_item("c")])
    # 后续更新是整体替换,旧 a/b 不应残留
    assert len(mgr.items) == 1
    assert mgr.items[0]["content"] == "c"
