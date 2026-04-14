from __future__ import annotations

import ast
import json
import re
import tomllib
from pathlib import Path
from collections.abc import Mapping
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "coding_deepgent"
README = ROOT / "README.md"
PYPROJECT = ROOT / "pyproject.toml"
STAGE_3 = "stage-3-professional-domain-runtime-foundation"
STAGE_4 = "stage-4-control-plane-foundation"
STAGE_5 = "stage-5-memory-context-compact-foundation"
STAGE_6 = "stage-6-skills-subagents-task-graph"
STAGE_7 = "stage-7-mcp-plugin-extension-foundation"
STAGE_8 = "stage-8-recovery-evidence-runtime-continuation"
STAGE_9 = "stage-9-permission-trust-boundary-hardening"
STAGE_10 = "stage-10-hooks-lifecycle-expansion"
STAGE_11 = "stage-11-mcp-plugin-real-loading"
FUTURE_SESSION_DOMAINS = (
    "tasks",
    "subagents",
)
FUTURE_TOOL_SYSTEM_DOMAINS = (
    "tasks",
    "subagents",
)
FORBIDDEN_RUNTIME_DEPENDENCIES = {
    "fastapi",
    "plug" + "gy",
    "open" + "telemetry",
    "sqlalchemy",
    "alembic",
}


def _status() -> dict[str, object]:
    return json.loads((ROOT / "project_status.json").read_text(encoding="utf-8"))


def _is_runtime_foundation_or_later() -> bool:
    return _status()["current_product_stage"] in {
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


def _require_runtime_foundation_or_later() -> None:
    if not _is_runtime_foundation_or_later():
        pytest.skip(
            "runtime foundation contract activates only after "
            "the stage marker is selected"
        )


def _pyproject() -> dict[str, object]:
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)


def _dependency_names(group: str) -> set[str]:
    project = cast(Mapping[str, object], _pyproject()["project"])
    if group == "dependencies":
        raw = project.get("dependencies", [])
    else:
        optional = cast(Mapping[str, object], project.get("optional-dependencies", {}))
        raw = optional.get(group, [])
    dependencies = cast(list[str], raw)
    return {
        re.split(r"[<>=!~;\[\s]", spec, maxsplit=1)[0].lower() for spec in dependencies
    }


def _module_name(path: Path) -> str:
    return ".".join(("coding_deepgent", *path.relative_to(SRC).with_suffix("").parts))


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    package_parts = _module_name(path).split(".")[:-1]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                module = node.module or ""
            else:
                trim = max(0, node.level - 1)
                anchor = package_parts[: len(package_parts) - trim]
                module = (
                    ".".join([*anchor, *(node.module.split("."))])
                    if node.module
                    else ".".join(anchor)
                )
            if module:
                imported.add(module)

    return imported


def _assert_no_import_prefix(paths: list[Path], prefixes: tuple[str, ...]) -> list[str]:
    offenders: list[str] = []
    for path in paths:
        for module in _imported_modules(path):
            if module.startswith(prefixes):
                offenders.append(f"{path.relative_to(ROOT)} -> {module}")
    return offenders


def test_readme_stage_metadata_matches_project_status() -> None:
    status = _status()
    readme = README.read_text(encoding="utf-8")

    assert str(status["current_product_stage"]) in readme
    assert str(status["compatibility_anchor"]) in readme


def test_runtime_foundation_dependency_contracts() -> None:
    runtime_dependencies = _dependency_names("dependencies")
    dev_dependencies = _dependency_names("dev")

    if _is_runtime_foundation_or_later():
        assert {
            "dependency-injector",
            "pydantic-settings",
            "typer",
            "rich",
            "structlog",
        } <= runtime_dependencies
        assert {"ruff", "mypy"} <= dev_dependencies
        assert runtime_dependencies.isdisjoint(FORBIDDEN_RUNTIME_DEPENDENCIES)
        return

    assert {"langchain", "langchain-openai", "python-dotenv"} <= runtime_dependencies
    assert "pytest" in dev_dependencies


def test_no_forbidden_runtime_foundation_mirror_modules_or_custom_tool_base() -> None:
    forbidden_paths = (
        SRC / "runtime" / "query.py",
        SRC / ("tool_" + "executor.py"),
        SRC / ("app_state_" + "store.py"),
    )
    missing = [path for path in forbidden_paths if path.exists()]
    assert missing == []

    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Tool":
                offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_stage3_domain_packages_do_not_import_containers() -> None:
    _require_runtime_foundation_or_later()

    domain_paths = [
        *sorted((SRC / "todo").rglob("*.py")),
        *sorted((SRC / "filesystem").rglob("*.py")),
        *sorted((SRC / "sessions").rglob("*.py")),
        *sorted((SRC / "tool_system").rglob("*.py")),
        *sorted((SRC / "permissions").rglob("*.py")),
        *sorted((SRC / "hooks").rglob("*.py")),
        *sorted((SRC / "prompting").rglob("*.py")),
        *sorted((SRC / "memory").rglob("*.py")),
        *sorted((SRC / "compact").rglob("*.py")),
        *sorted((SRC / "skills").rglob("*.py")),
        *sorted((SRC / "tasks").rglob("*.py")),
        *sorted((SRC / "subagents").rglob("*.py")),
        *sorted((SRC / "mcp").rglob("*.py")),
        *sorted((SRC / "plugins").rglob("*.py")),
    ]

    offenders = _assert_no_import_prefix(domain_paths, ("coding_deepgent.containers",))
    assert offenders == []


def test_stage3_ui_imports_stay_out_of_domain_core_modules() -> None:
    _require_runtime_foundation_or_later()

    core_paths = [
        path
        for path in SRC.rglob("*.py")
        if path.parent.name
        in {
            "todo",
            "filesystem",
            "sessions",
            "tool_system",
            "permissions",
            "hooks",
            "prompting",
        }
        and path.name in {"schemas.py", "state.py", "service.py"}
    ]

    offenders = _assert_no_import_prefix(core_paths, ("rich", "typer"))
    assert offenders == []


def test_stage3_future_domain_boundaries() -> None:
    _require_runtime_foundation_or_later()

    session_offenders = _assert_no_import_prefix(
        sorted((SRC / "sessions").rglob("*.py")),
        tuple(f"coding_deepgent.{domain}" for domain in FUTURE_SESSION_DOMAINS),
    )
    tool_system_offenders = _assert_no_import_prefix(
        sorted((SRC / "tool_system").rglob("*.py")),
        tuple(f"coding_deepgent.{domain}" for domain in FUTURE_TOOL_SYSTEM_DOMAINS),
    )

    assert session_offenders == []
    assert tool_system_offenders == []


def test_stage3_pydantic_settings_stays_centralized() -> None:
    _require_runtime_foundation_or_later()

    offenders = _assert_no_import_prefix(
        [
            path
            for path in SRC.rglob("*.py")
            if path.relative_to(SRC) != Path("settings.py")
        ],
        ("pydantic_settings",),
    )
    assert offenders == []
