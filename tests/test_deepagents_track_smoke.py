from __future__ import annotations

import importlib
from pathlib import Path
import py_compile

import pytest


ROOT = Path(__file__).resolve().parents[1]
TRACK_DIR = ROOT / "agents_deepagents"
TRACK_FILES = sorted(
    path for path in TRACK_DIR.glob("*.py") if path.name != "__init__.py"
)
TRACK_IDS = [path.name for path in TRACK_FILES]


@pytest.mark.parametrize("agent_path", TRACK_FILES, ids=TRACK_IDS)
def test_deepagents_track_scripts_compile(agent_path: Path) -> None:
    _ = py_compile.compile(str(agent_path), doraise=True)


def test_deepagents_track_scripts_exist() -> None:
    assert TRACK_FILES, "expected Deep Agents teaching scripts"
    for filename in [
        "s01_agent_loop.py",
        "s02_tool_use.py",
        "s03_todo_write.py",
        "s04_subagent.py",
        "s05_skill_loading.py",
        "s06_context_compact.py",
    ]:
        assert TRACK_DIR.joinpath(filename).exists()


def test_pure_helpers_import_without_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    common = importlib.import_module("agents_deepagents.common")
    s03 = importlib.import_module("agents_deepagents.s03_todo_write")
    s06 = importlib.import_module("agents_deepagents.s06_context_compact")

    assert common.deepagents_model_name()
    assert s06.PIPELINE_STAGE_ORDER[0] == "apply_tool_result_budget"
    assert "reactive_compact_on_overflow" in s06.PIPELINE_STAGE_ORDER
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        common.build_openai_model()

    normalized = s03.normalize_plan_items([
        {"content": "Inspect task", "status": "completed"},
        {
            "content": "Implement",
            "status": "in_progress",
            "activeForm": "Implementing",
        },
    ])
    rendered = s03.render_plan_items(normalized)
    assert "[x] Inspect task" in rendered
    assert "[>] Implement (Implementing)" in rendered


def test_safe_path_rejects_workspace_escape() -> None:
    common = importlib.import_module("agents_deepagents.common")

    with pytest.raises(ValueError, match="escapes workspace"):
        common.safe_path("../outside.txt")


def test_s05_read_file_supports_virtual_skill_paths() -> None:
    s05 = importlib.import_module("agents_deepagents.s05_skill_loading")

    text = s05.read_file.invoke({"path": "/skills/code-review/SKILL.md"})

    assert "name: code-review" in text
    assert "description:" in text
    assert "# Code Review Skill" in text
    assert "## Review Checklist" in text
