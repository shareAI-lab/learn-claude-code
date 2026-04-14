from __future__ import annotations

import ast
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "src" / "coding_deepgent"
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
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def _status() -> dict[str, object]:
    return json.loads(
        (PROJECT_ROOT / "project_status.json").read_text(encoding="utf-8")
    )


def test_project_contains_responsibility_modules() -> None:
    stage = str(_status()["current_product_stage"])
    expected = {
        PROJECT_ROOT / "pyproject.toml",
        PROJECT_ROOT / "project_status.json",
    }

    if stage == STAGE_1:
        expected.update(
            {
                PACKAGE_ROOT / "config.py",
                PACKAGE_ROOT / "state.py",
                PACKAGE_ROOT / "app.py",
                PACKAGE_ROOT / "cli.py",
                PACKAGE_ROOT / "tools" / "filesystem.py",
                PACKAGE_ROOT / "tools" / "planning.py",
                PACKAGE_ROOT / "middleware" / "planning.py",
            }
        )
    elif stage in {
        STAGE_3,
        STAGE_4,
        STAGE_5,
        STAGE_6,
        STAGE_7,
        STAGE_8,
        STAGE_9,
        STAGE_10,
        STAGE_11,
    }:
        expected.update(
            {
                PACKAGE_ROOT / "app.py",
                PACKAGE_ROOT / "cli.py",
                PACKAGE_ROOT / "settings.py",
                PACKAGE_ROOT / "containers" / "__init__.py",
                PACKAGE_ROOT / "containers" / "app.py",
                PACKAGE_ROOT / "containers" / "runtime.py",
                PACKAGE_ROOT / "containers" / "tool_system.py",
                PACKAGE_ROOT / "containers" / "filesystem.py",
                PACKAGE_ROOT / "containers" / "todo.py",
                PACKAGE_ROOT / "containers" / "sessions.py",
                PACKAGE_ROOT / "runtime" / "__init__.py",
                PACKAGE_ROOT / "runtime" / "context.py",
                PACKAGE_ROOT / "runtime" / "state.py",
                PACKAGE_ROOT / "tool_system" / "__init__.py",
                PACKAGE_ROOT / "tool_system" / "capabilities.py",
                PACKAGE_ROOT / "tool_system" / "policy.py",
                PACKAGE_ROOT / "tool_system" / "middleware.py",
                PACKAGE_ROOT / "filesystem" / "__init__.py",
                PACKAGE_ROOT / "filesystem" / "schemas.py",
                PACKAGE_ROOT / "filesystem" / "tools.py",
                PACKAGE_ROOT / "todo" / "__init__.py",
                PACKAGE_ROOT / "todo" / "schemas.py",
                PACKAGE_ROOT / "todo" / "state.py",
                PACKAGE_ROOT / "todo" / "tools.py",
                PACKAGE_ROOT / "todo" / "middleware.py",
                PACKAGE_ROOT / "todo" / "renderers.py",
                PACKAGE_ROOT / "sessions" / "__init__.py",
                PACKAGE_ROOT / "sessions" / "records.py",
                PACKAGE_ROOT / "sessions" / "store_jsonl.py",
                PACKAGE_ROOT / "sessions" / "resume.py",
                PACKAGE_ROOT / "sessions" / "langgraph.py",
                PACKAGE_ROOT / "permissions" / "__init__.py",
                PACKAGE_ROOT / "permissions" / "manager.py",
                PACKAGE_ROOT / "permissions" / "modes.py",
                PACKAGE_ROOT / "permissions" / "rules.py",
                PACKAGE_ROOT / "hooks" / "__init__.py",
                PACKAGE_ROOT / "hooks" / "events.py",
                PACKAGE_ROOT / "hooks" / "registry.py",
                PACKAGE_ROOT / "prompting" / "__init__.py",
                PACKAGE_ROOT / "prompting" / "builder.py",
                PACKAGE_ROOT / "memory" / "__init__.py",
                PACKAGE_ROOT / "memory" / "schemas.py",
                PACKAGE_ROOT / "memory" / "store.py",
                PACKAGE_ROOT / "memory" / "recall.py",
                PACKAGE_ROOT / "memory" / "tools.py",
                PACKAGE_ROOT / "compact" / "__init__.py",
                PACKAGE_ROOT / "compact" / "budget.py",
                PACKAGE_ROOT / "skills" / "__init__.py",
                PACKAGE_ROOT / "skills" / "schemas.py",
                PACKAGE_ROOT / "skills" / "loader.py",
                PACKAGE_ROOT / "skills" / "tools.py",
                PACKAGE_ROOT / "tasks" / "__init__.py",
                PACKAGE_ROOT / "tasks" / "schemas.py",
                PACKAGE_ROOT / "tasks" / "store.py",
                PACKAGE_ROOT / "tasks" / "tools.py",
                PACKAGE_ROOT / "subagents" / "__init__.py",
                PACKAGE_ROOT / "subagents" / "schemas.py",
                PACKAGE_ROOT / "subagents" / "tools.py",
            }
        )
        if stage in {STAGE_3, STAGE_4, STAGE_5, STAGE_6, STAGE_7, STAGE_8, STAGE_9, STAGE_10}:
            expected.update(
                {
                    PACKAGE_ROOT / "config.py",
                    PACKAGE_ROOT / "state.py",
                }
            )
        if stage in {STAGE_7, STAGE_8, STAGE_9, STAGE_10, STAGE_11}:
            expected.update(
                {
                    PACKAGE_ROOT / "mcp" / "__init__.py",
                    PACKAGE_ROOT / "mcp" / "schemas.py",
                    PACKAGE_ROOT / "mcp" / "adapters.py",
                    PACKAGE_ROOT / "plugins" / "__init__.py",
                    PACKAGE_ROOT / "plugins" / "schemas.py",
                    PACKAGE_ROOT / "plugins" / "loader.py",
                    PACKAGE_ROOT / "plugins" / "registry.py",
                }
            )
        if stage == STAGE_11:
            expected.update(
                {
                    PACKAGE_ROOT / "bootstrap.py",
                    PACKAGE_ROOT / "agent_runtime_service.py",
                    PACKAGE_ROOT / "agent_loop_service.py",
                    PACKAGE_ROOT / "cli_service.py",
                    PACKAGE_ROOT / "extensions_service.py",
                    PACKAGE_ROOT / "startup.py",
                    PACKAGE_ROOT / "filesystem" / "service.py",
                    PACKAGE_ROOT / "hooks" / "dispatcher.py",
                    PACKAGE_ROOT / "sessions" / "service.py",
                }
            )
    else:
        raise AssertionError(f"unexpected product stage: {stage}")

    missing = sorted(
        str(path.relative_to(PROJECT_ROOT)) for path in expected if not path.exists()
    )
    assert not missing, f"missing expected project files: {missing}"


def test_project_has_no_public_stage_modules() -> None:
    staged_modules = sorted(path.name for path in PACKAGE_ROOT.glob("s[0-9][0-9]_*.py"))
    assert staged_modules == []


def test_project_status_declares_product_stage() -> None:
    marker = _status()
    stage = str(marker["current_product_stage"])

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
        marker["compatibility_anchor"]
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
    assert marker["shape"] == "staged_langchain_cc_product"
    assert "product-stage plan approval" in str(marker["upgrade_policy"])
    assert marker["public_entrypoints"] == ["coding-deepgent"]


def test_source_tree_stays_independent_from_tutorial_track() -> None:
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
                assert all(not name.startswith(TUTORIAL_PACKAGE) for name in names), (
                    path
                )
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not module.startswith(TUTORIAL_PACKAGE), path
