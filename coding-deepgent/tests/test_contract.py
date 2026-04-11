from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "coding_deepgent"
TESTS = ROOT / "tests"


def _python_files() -> list[Path]:
    return sorted([*SRC.rglob("*.py"), *TESTS.rglob("*.py")])


def test_project_avoids_agents_deepagents_imports() -> None:
    offenders: list[str] = []

    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("agents_deepagents"):
                        offenders.append(f"{path}:{alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("agents_deepagents"):
                    offenders.append(f"{path}:{module}")

    assert offenders == []


def test_project_status_tracks_confirmed_milestone() -> None:
    status = json.loads((ROOT / "project_status.json").read_text(encoding="utf-8"))

    assert status["current_milestone"] == "s03"
    assert status["public_shape"] == "single cumulative app"
    assert "explicit user confirmation" in status["upgrade_rule"].lower()


def test_package_does_not_expose_stage_named_modules() -> None:
    package_files = {path.name for path in SRC.glob("*.py")}

    assert not any(name.startswith("s0") for name in package_files)
