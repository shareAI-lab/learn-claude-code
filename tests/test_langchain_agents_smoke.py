from __future__ import annotations

from pathlib import Path
import py_compile

import pytest


ROOT = Path(__file__).resolve().parents[1]
LANGCHAIN_DIR = ROOT / "agents_langchain"
EXPECTED_CHAPTERS = [
    "s01_agent_loop.py",
    "s02_tool_use.py",
    "s03_todo_write.py",
    "s04_subagent.py",
    "s05_skill_loading.py",
    "s06_context_compact.py",
]
PY_FILES = sorted(LANGCHAIN_DIR.glob("*.py"))


@pytest.mark.parametrize("agent_path", PY_FILES, ids=[path.name for path in PY_FILES])
def test_langchain_track_python_files_compile(agent_path: Path) -> None:
    _ = py_compile.compile(str(agent_path), doraise=True)


def test_langchain_chapter_scripts_exist() -> None:
    for filename in EXPECTED_CHAPTERS:
        assert (LANGCHAIN_DIR / filename).is_file()
    assert (LANGCHAIN_DIR / "README.md").is_file()


def test_openai_model_resolution_does_not_default_to_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents_langchain import _common

    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("MODEL_ID", "claude-sonnet-4-6")

    assert _common.resolve_openai_model() == _common.DEFAULT_OPENAI_MODEL


def test_safe_path_rejects_workspace_escape() -> None:
    from agents_langchain._common import safe_path

    with pytest.raises(ValueError, match="escapes workspace"):
        safe_path("../outside-workspace")
