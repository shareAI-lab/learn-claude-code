"""Unit tests for TodoManager (s03_todo_write.py)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from conftest import load_agent_module


@pytest.fixture()
def TodoManager():
    with tempfile.TemporaryDirectory() as tmp:
        module = load_agent_module("s03_todo_write.py", Path(tmp))
        yield module.TodoManager


# -- render() --

class TestRender:
    def test_empty_renders_no_todos(self, TodoManager):
        tm = TodoManager()
        assert tm.render() == "No todos."

    def test_render_markers(self, TodoManager):
        tm = TodoManager()
        tm.update([
            {"id": "1", "text": "Plan", "status": "completed"},
            {"id": "2", "text": "Build", "status": "in_progress"},
            {"id": "3", "text": "Test", "status": "pending"},
        ])
        output = tm.render()
        assert "[x] #1: Plan" in output
        assert "[>] #2: Build" in output
        assert "[ ] #3: Test" in output

    def test_render_completion_count(self, TodoManager):
        tm = TodoManager()
        tm.update([
            {"id": "1", "text": "Done", "status": "completed"},
            {"id": "2", "text": "Todo", "status": "pending"},
        ])
        assert "(1/2 completed)" in tm.render()


# -- update() happy path --

class TestUpdateHappyPath:
    def test_single_item(self, TodoManager):
        tm = TodoManager()
        result = tm.update([{"id": "1", "text": "Hello", "status": "pending"}])
        assert "[ ] #1: Hello" in result
        assert len(tm.items) == 1

    def test_max_20_items(self, TodoManager):
        tm = TodoManager()
        items = [{"id": str(i), "text": f"Task {i}", "status": "pending"} for i in range(1, 21)]
        result = tm.update(items)
        assert "(0/20 completed)" in result

    def test_one_in_progress_allowed(self, TodoManager):
        tm = TodoManager()
        result = tm.update([
            {"id": "1", "text": "A", "status": "in_progress"},
            {"id": "2", "text": "B", "status": "pending"},
        ])
        assert "[>] #1: A" in result


# -- update() defaults --

class TestUpdateDefaults:
    def test_default_status_is_pending(self, TodoManager):
        tm = TodoManager()
        tm.update([{"id": "1", "text": "Foo"}])
        assert tm.items[0]["status"] == "pending"

    def test_default_id_from_index(self, TodoManager):
        tm = TodoManager()
        tm.update([{"text": "First"}, {"text": "Second"}])
        assert tm.items[0]["id"] == "1"
        assert tm.items[1]["id"] == "2"

    def test_status_case_insensitive(self, TodoManager):
        tm = TodoManager()
        tm.update([{"id": "1", "text": "Foo", "status": "PENDING"}])
        assert tm.items[0]["status"] == "pending"

    def test_text_stripped(self, TodoManager):
        tm = TodoManager()
        tm.update([{"id": "1", "text": "  spaced  ", "status": "pending"}])
        assert tm.items[0]["text"] == "spaced"


# -- update() validation errors --

class TestUpdateValidation:
    def test_over_20_raises(self, TodoManager):
        tm = TodoManager()
        items = [{"id": str(i), "text": f"T{i}", "status": "pending"} for i in range(21)]
        with pytest.raises(ValueError, match="Max 20"):
            tm.update(items)

    def test_empty_text_raises(self, TodoManager):
        tm = TodoManager()
        with pytest.raises(ValueError, match="text required"):
            tm.update([{"id": "1", "text": "", "status": "pending"}])

    def test_whitespace_only_text_raises(self, TodoManager):
        tm = TodoManager()
        with pytest.raises(ValueError, match="text required"):
            tm.update([{"id": "1", "text": "   ", "status": "pending"}])

    def test_invalid_status_raises(self, TodoManager):
        tm = TodoManager()
        with pytest.raises(ValueError, match="invalid status"):
            tm.update([{"id": "1", "text": "Foo", "status": "done"}])

    def test_two_in_progress_raises(self, TodoManager):
        tm = TodoManager()
        with pytest.raises(ValueError, match="Only one task"):
            tm.update([
                {"id": "1", "text": "A", "status": "in_progress"},
                {"id": "2", "text": "B", "status": "in_progress"},
            ])
