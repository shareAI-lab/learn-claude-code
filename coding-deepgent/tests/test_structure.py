from __future__ import annotations

import ast
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "src" / "coding_deepgent"


def _python_files() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def test_project_contains_responsibility_modules() -> None:
    expected = {
        PROJECT_ROOT / "pyproject.toml",
        PROJECT_ROOT / "project_status.json",
        PACKAGE_ROOT / "config.py",
        PACKAGE_ROOT / "state.py",
        PACKAGE_ROOT / "app.py",
        PACKAGE_ROOT / "cli.py",
        PACKAGE_ROOT / "tools" / "filesystem.py",
        PACKAGE_ROOT / "tools" / "planning.py",
        PACKAGE_ROOT / "middleware" / "planning.py",
    }
    missing = sorted(str(path.relative_to(PROJECT_ROOT)) for path in expected if not path.exists())
    assert not missing, f"missing expected project files: {missing}"


def test_project_has_no_public_stage_modules() -> None:
    staged_modules = sorted(path.name for path in PACKAGE_ROOT.glob("s[0-9][0-9]_*.py"))
    assert staged_modules == []


def test_project_status_declares_s03_gate() -> None:
    marker = json.loads((PROJECT_ROOT / "project_status.json").read_text(encoding="utf-8"))

    assert marker["current_confirmed_milestone"] == "s03"
    assert marker["shape"] == "cumulative_project"
    assert "explicit user confirmation" in marker["upgrade_policy"].lower()
    assert marker["public_entrypoints"] == ["coding-deepgent"]


def test_source_tree_stays_independent_from_agents_deepagents() -> None:
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
                assert all(not name.startswith("agents_deepagents") for name in names), path
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not module.startswith("agents_deepagents"), path
