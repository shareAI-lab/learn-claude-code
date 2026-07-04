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


def test_all_lessons_import_shared_modules() -> None:
    """Every lesson except the bootstrap origins must import shared code.

    First-appearance rule (issue #349): the lesson that INTRODUCES a concept
    inlines it; later lessons import the abstraction. s01 is the origin of
    init_env/run_repl (inlined, self-contained — no common import). All other
    lessons must import from common (boilerplate) and/or mechanisms (reused
    mechanisms) rather than re-inlining everything.
    """
    for path in LESSON_FILES:
        if path.parent.name == "s01_agent_loop":
            continue  # bootstrap origin: self-contained by design
        text = path.read_text(encoding="utf-8")
        assert ("from common import" in text
                or "from mechanisms" in text), (
            f"{path.relative_to(ROOT)} imports neither common nor mechanisms")


def test_task_system_not_reduplicated() -> None:
    """The Task System mechanism must be imported, not re-inlined (issue #349).

    Only s12 (the origin lesson) may define ``class Task`` inline. Every other
    lesson must import from mechanisms/tasks.py. s17-s20 override ``claim_task``
    locally (they teach the owner-check enhancement), but the dataclass and the
    other 7 functions come from the shared module.
    """
    origins = {"s12_task_system"}  # s12 introduces the Task System inline
    for path in LESSON_FILES:
        if path.parent.name in origins:
            continue
        text = path.read_text(encoding="utf-8")
        assert "class Task:" not in text, (
            f"{path.parent.name} re-inlines the Task System — "
            "import from mechanisms/tasks.py instead (issue #349)")
