from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / ".trellis" / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common.git_context import (  # type: ignore[import-not-found]  # noqa: E402
    get_context_json,
    get_context_record_json,
    get_context_text,
    get_context_text_record,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_repo(
    tmp_path: Path,
    *,
    current_task_path: str = ".trellis/tasks/04-19-demo-task",
    create_task: bool = True,
) -> Path:
    _write(tmp_path / ".trellis" / ".developer", "name=kun\n")
    _write(tmp_path / ".trellis" / ".current-task", f"{current_task_path}\n")
    _write(tmp_path / ".trellis" / "workspace" / "kun" / "journal-1.md", "# Journal\n")

    if create_task:
        task_dir = tmp_path / current_task_path
        task_payload: dict[str, Any] = {
            "name": "demo-task",
            "title": "Demo task",
            "status": "planning",
            "createdAt": "2026-04-19",
            "description": "Demo task description",
            "assignee": "kun",
            "children": [],
            "parent": None,
        }
        _write(task_dir / "task.json", json.dumps(task_payload),)
        _write(task_dir / "prd.md", "# Demo task\n")

    return tmp_path


def test_default_context_json_includes_current_task(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    context = get_context_json(repo_root)
    current_task = context["currentTask"]

    assert current_task is not None
    assert current_task["path"] == ".trellis/tasks/04-19-demo-task"
    assert current_task["name"] == "demo-task"
    assert current_task["status"] == "planning"
    assert current_task["createdAt"] == "2026-04-19"
    assert current_task["description"] == "Demo task description"
    assert current_task["hasPrd"] is True
    assert current_task["isValid"] is True


def test_text_and_record_modes_render_current_task(tmp_path: Path) -> None:
    repo_root = _make_repo(tmp_path)

    text = get_context_text(repo_root)
    record_text = get_context_text_record(repo_root)
    record_json = get_context_record_json(repo_root)

    assert "## CURRENT TASK" in text
    assert "Path: .trellis/tasks/04-19-demo-task" in text
    assert "Name: demo-task" in text
    assert "Status: planning" in text
    assert "Created: 2026-04-19" in text
    assert "Description: Demo task description" in text
    assert "[!] This task has prd.md - read it for task details" in text
    assert "## CURRENT TASK" in record_text
    assert "Path: .trellis/tasks/04-19-demo-task" in record_text
    assert "Name: demo-task" in record_text
    assert "Status: planning" in record_text
    assert record_json["currentTask"] is not None
    assert record_json["currentTask"]["path"] == ".trellis/tasks/04-19-demo-task"


def test_invalid_current_task_pointer_is_reported(tmp_path: Path) -> None:
    repo_root = _make_repo(
        tmp_path,
        current_task_path=".trellis/tasks/04-19-missing-task",
        create_task=False,
    )

    context = get_context_json(repo_root)
    current_task = context["currentTask"]
    text = get_context_text(repo_root)

    assert current_task is not None
    assert current_task["path"] == ".trellis/tasks/04-19-missing-task"
    assert current_task["status"] == "invalid"
    assert current_task["warning"] == "path does not exist"
    assert current_task["isValid"] is False
    assert "Path: .trellis/tasks/04-19-missing-task" in text
    assert "[!] Invalid current task pointer: path does not exist" in text
