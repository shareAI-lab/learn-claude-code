from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "coding_deepgent"
TESTS = ROOT / "tests"
STAGE_1 = "stage-1-todowrite-foundation"
STAGE_3 = "stage-3-professional-domain-runtime-foundation"
STAGE_4 = "stage-4-control-plane-foundation"
STAGE_5 = "stage-5-memory-context-compact-foundation"
STAGE_6 = "stage-6-skills-subagents-task-graph"
STAGE_7 = "stage-7-mcp-plugin-extension-foundation"
STAGE_8 = "stage-8-recovery-evidence-runtime-continuation"
STAGE_9 = "stage-9-permission-trust-boundary-hardening"
STAGE_10 = "stage-10-hooks-lifecycle-expansion"
STAGE_11 = "stage-11-mcp-plugin-real-loading"
TUTORIAL_PACKAGE = "agents_" + "deepagents"


def _python_files() -> list[Path]:
    return sorted([*SRC.rglob("*.py"), *TESTS.rglob("*.py")])


def _status() -> dict[str, object]:
    return json.loads((ROOT / "project_status.json").read_text(encoding="utf-8"))


def test_project_avoids_tutorial_track_imports() -> None:
    offenders: list[str] = []

    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(TUTORIAL_PACKAGE):
                        offenders.append(f"{path}:{alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith(TUTORIAL_PACKAGE):
                    offenders.append(f"{path}:{module}")

    assert offenders == []


def test_product_status_uses_stage_language_not_chapter_gate() -> None:
    status = _status()
    stage = str(status["current_product_stage"])

    assert stage in {
        STAGE_1,
        STAGE_3,
        STAGE_4,
        STAGE_5,
        STAGE_6,
        STAGE_7,
        STAGE_8,
        STAGE_9,
        STAGE_10,
        STAGE_11,
    }
    assert (
        status["compatibility_anchor"]
        == {
            STAGE_1: "s03",
            STAGE_3: "professional-domain-runtime-foundation",
            STAGE_4: "control-plane-foundation",
            STAGE_5: "memory-context-compact-foundation",
            STAGE_6: "skills-subagents-task-graph",
            STAGE_7: "mcp-plugin-extension-foundation",
            STAGE_8: "recovery-evidence-runtime-continuation",
            STAGE_9: "permission-trust-boundary-hardening",
            STAGE_10: "hooks-lifecycle-expansion",
            STAGE_11: "mcp-plugin-real-loading",
        }[stage]
    )
    assert status["shape"] == "staged_langchain_cc_product"
    upgrade_policy = str(status["upgrade_policy"])
    assert "product-stage plan approval" in upgrade_policy
    assert "chapter is complete" not in upgrade_policy


def test_package_does_not_expose_stage_named_modules() -> None:
    package_files = {path.name for path in SRC.glob("*.py")}

    assert not any(name.startswith("s0") for name in package_files)
