"""Smoke tests for the shared-imports refactor (issue #349).

Every lesson ``s*/code.py`` must compile, and ``common.py`` must exist and be
importable with the same ``anthropic``/``dotenv`` stubs the rest of the suite
uses. This guards against syntax errors and broken ``from common import ...``
statements introduced by the refactor.
"""
from __future__ import annotations

import importlib.util
import os
import py_compile
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMMON_PATH = ROOT / "common.py"
LESSON_FILES = sorted(ROOT.glob("s*/code.py"))
LESSON_IDS = [f"{p.parent.name}/code.py" for p in LESSON_FILES]


@pytest.mark.parametrize("lesson_path", LESSON_FILES, ids=LESSON_IDS)
def test_lesson_code_compiles(lesson_path: Path) -> None:
    """Each lesson must be syntactically valid (py_compile, no exec)."""
    _ = py_compile.compile(str(lesson_path), doraise=True)


def test_common_py_exists() -> None:
    assert COMMON_PATH.is_file(), "common.py must exist at the repo root"


def test_common_py_compiles() -> None:
    _ = py_compile.compile(str(COMMON_PATH), doraise=True)


def test_common_py_is_importable() -> None:
    """common.py must import and expose the shared API used by every lesson.

    Uses the same anthropic/dotenv stub pattern as test_compaction_tool_pairs
    so no real API key or network access is required.
    """
    ant = types.ModuleType("anthropic")
    ant.Anthropic = lambda **kwargs: types.SimpleNamespace()
    sys.modules.setdefault("anthropic", ant)
    dot = types.ModuleType("dotenv")
    dot.load_dotenv = lambda **kwargs: None
    sys.modules.setdefault("dotenv", dot)

    prev_model = os.environ.get("MODEL_ID")
    prev_key = os.environ.get("ANTHROPIC_API_KEY")
    os.environ["MODEL_ID"] = "test-model"
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    try:
        sys.path.insert(0, str(ROOT))
        import common  # noqa: F401  (imported for side effects)
        assert callable(common.init_env)
        assert callable(common.make_base_tools)
        assert isinstance(common.BASE_TOOLS, list) and common.BASE_TOOLS
        assert callable(common.select_tools)
        assert callable(common.run_repl)
        # select_tools must round-trip the full set.
        names = [t["name"] for t in common.BASE_TOOLS]
        assert [t["name"] for t in common.select_tools(names)] == names
    finally:
        os.environ.pop("MODEL_ID", None)
        if prev_model is not None:
            os.environ["MODEL_ID"] = prev_model
        os.environ.pop("ANTHROPIC_API_KEY", None)
        if prev_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = prev_key


def test_all_lessons_import_common() -> None:
    """Every lesson source must import from common (the point of issue #349)."""
    for path in LESSON_FILES:
        text = path.read_text(encoding="utf-8")
        assert "from common import" in text, (
            f"{path.relative_to(ROOT)} does not import from common")
