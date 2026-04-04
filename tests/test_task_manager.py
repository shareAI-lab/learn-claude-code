"""Unit tests for TaskManager (s07_task_system.py)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from conftest import load_agent_module


@pytest.fixture()
def TaskManager():
    with tempfile.TemporaryDirectory() as tmp:
        module = load_agent_module("s07_task_system.py", Path(tmp))
        yield module.TaskManager


# -- create --

class TestCreate:
    def test_creates_task_with_defaults(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        result = json.loads(tm.create("Build feature"))
        assert result["id"] == 1
        assert result["subject"] == "Build feature"
        assert result["description"] == ""
        assert result["status"] == "pending"
        assert result["blockedBy"] == []
        assert result["owner"] == ""

    def test_sequential_ids(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        t1 = json.loads(tm.create("First"))
        t2 = json.loads(tm.create("Second"))
        t3 = json.loads(tm.create("Third"))
        assert t1["id"] == 1
        assert t2["id"] == 2
        assert t3["id"] == 3

    def test_persists_to_file(self, TaskManager, tmp_path):
        tasks_dir = tmp_path / "tasks"
        tm = TaskManager(tasks_dir)
        tm.create("Persisted task")
        assert (tasks_dir / "task_1.json").exists()
        data = json.loads((tasks_dir / "task_1.json").read_text())
        assert data["subject"] == "Persisted task"

    def test_with_description(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        result = json.loads(tm.create("Task", "Detailed description"))
        assert result["description"] == "Detailed description"


# -- get --

class TestGet:
    def test_get_existing(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        tm.create("My task")
        result = json.loads(tm.get(1))
        assert result["subject"] == "My task"

    def test_get_nonexistent_raises(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        with pytest.raises(ValueError, match="Task 999 not found"):
            tm.get(999)


# -- update --

class TestUpdate:
    def test_update_status(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        tm.create("Task")
        result = json.loads(tm.update(1, status="in_progress"))
        assert result["status"] == "in_progress"

    def test_invalid_status_raises(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        tm.create("Task")
        with pytest.raises(ValueError, match="Invalid status"):
            tm.update(1, status="done")

    def test_add_blocked_by(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        tm.create("First")
        tm.create("Second")
        result = json.loads(tm.update(2, add_blocked_by=[1]))
        assert 1 in result["blockedBy"]

    def test_add_blocked_by_deduplicates(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        tm.create("First")
        tm.create("Second")
        tm.update(2, add_blocked_by=[1])
        result = json.loads(tm.update(2, add_blocked_by=[1]))
        assert result["blockedBy"].count(1) == 1

    def test_remove_blocked_by(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        tm.create("First")
        tm.create("Second")
        tm.update(2, add_blocked_by=[1])
        result = json.loads(tm.update(2, remove_blocked_by=[1]))
        assert 1 not in result["blockedBy"]

    def test_remove_nonexistent_dependency_ok(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        tm.create("Task")
        result = json.loads(tm.update(1, remove_blocked_by=[999]))
        assert result["blockedBy"] == []


# -- _clear_dependency --

class TestClearDependency:
    def test_completing_clears_from_dependents(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        tm.create("Blocker")
        tm.create("Blocked")
        tm.update(2, add_blocked_by=[1])
        # Complete task 1 -> should remove 1 from task 2's blockedBy
        tm.update(1, status="completed")
        task2 = json.loads(tm.get(2))
        assert 1 not in task2["blockedBy"]

    def test_completing_clears_from_multiple_dependents(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        tm.create("Blocker")
        tm.create("Dep A")
        tm.create("Dep B")
        tm.update(2, add_blocked_by=[1])
        tm.update(3, add_blocked_by=[1])
        tm.update(1, status="completed")
        assert 1 not in json.loads(tm.get(2))["blockedBy"]
        assert 1 not in json.loads(tm.get(3))["blockedBy"]


# -- list_all --

class TestListAll:
    def test_empty(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        assert tm.list_all() == "No tasks."

    def test_with_items(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        tm.create("Alpha")
        tm.create("Beta")
        tm.update(1, status="completed")
        output = tm.list_all()
        assert "[x] #1: Alpha" in output
        assert "[ ] #2: Beta" in output

    def test_shows_blocked_info(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        tm.create("First")
        tm.create("Second")
        tm.update(2, add_blocked_by=[1])
        output = tm.list_all()
        assert "blocked by:" in output

    def test_sorted_by_id(self, TaskManager, tmp_path):
        tm = TaskManager(tmp_path / "tasks")
        tm.create("Third")
        tm.create("First")
        output = tm.list_all()
        lines = [l for l in output.splitlines() if l.strip()]
        assert "#1" in lines[0]
        assert "#2" in lines[1]


# -- ID continuity across instances --

class TestIdContinuity:
    def test_new_instance_resumes_ids(self, TaskManager, tmp_path):
        tasks_dir = tmp_path / "tasks"
        tm1 = TaskManager(tasks_dir)
        tm1.create("Task A")
        tm1.create("Task B")
        # New instance on same directory
        tm2 = TaskManager(tasks_dir)
        result = json.loads(tm2.create("Task C"))
        assert result["id"] == 3
