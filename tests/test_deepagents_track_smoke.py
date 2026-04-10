from __future__ import annotations

import importlib
from pathlib import Path
import py_compile

import pytest


ROOT = Path(__file__).resolve().parents[1]
LANGCHAIN_DIR = ROOT / "agents_deepagents"
LANGCHAIN_FILES = sorted(
    path for path in LANGCHAIN_DIR.glob("*.py") if path.name != "__init__.py"
)
LANGCHAIN_IDS = [path.name for path in LANGCHAIN_FILES]


@pytest.mark.parametrize("agent_path", LANGCHAIN_FILES, ids=LANGCHAIN_IDS)
def test_langchain_agent_scripts_compile(agent_path: Path) -> None:
    _ = py_compile.compile(str(agent_path), doraise=True)


def test_langchain_agent_scripts_exist() -> None:
    assert LANGCHAIN_FILES, "expected Deep Agents teaching scripts"
    for filename in [
        "s01_agent_loop.py",
        "s02_tool_use.py",
        "s03_todo_write.py",
        "s04_subagent.py",
        "s05_skill_loading.py",
        "s06_context_compact.py",
    ]:
        assert LANGCHAIN_DIR.joinpath(filename).exists()


def test_pure_helpers_import_without_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    common = importlib.import_module("agents_deepagents.common")
    s03 = importlib.import_module("agents_deepagents.s03_todo_write")

    assert common.langchain_model_name()
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        common.build_openai_model()

    todo = s03.TodoManager()
    rendered = todo.update([
        {"content": "Inspect task", "status": "completed"},
        {"content": "Implement", "status": "in_progress", "activeForm": "Implementing"},
    ])
    assert "[x] Inspect task" in rendered
    assert "[>] Implement (Implementing)" in rendered


def test_safe_path_rejects_workspace_escape() -> None:
    common = importlib.import_module("agents_deepagents.common")

    with pytest.raises(ValueError, match="escapes workspace"):
        common.safe_path("../outside.txt")


def test_skill_registry_parses_frontmatter(tmp_path: Path) -> None:
    s05 = importlib.import_module("agents_deepagents.s05_skill_loading")
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\nname: demo\ndescription: Demo skill\n---\n\nUse this skill.\n",
        encoding="utf-8",
    )

    registry = s05.SkillRegistry(tmp_path)

    assert "- demo: Demo skill" in registry.describe_available()
    assert "Use this skill." in registry.load_full_text("demo")
