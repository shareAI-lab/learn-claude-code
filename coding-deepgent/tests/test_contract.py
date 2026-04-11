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


def test_product_status_uses_stage_language_not_chapter_gate() -> None:
    status = json.loads((ROOT / "project_status.json").read_text(encoding="utf-8"))

    assert status["current_product_stage"] == "stage-1-todowrite-foundation"
    assert status["compatibility_anchor"] == "s03"
    assert status["shape"] == "staged_langchain_cc_product"
    assert "product-stage plan approval" in status["upgrade_policy"]
    assert "chapter is complete" not in status["upgrade_policy"]


def test_package_does_not_expose_stage_named_modules() -> None:
    package_files = {path.name for path in SRC.glob("*.py")}

    assert not any(name.startswith("s0") for name in package_files)
