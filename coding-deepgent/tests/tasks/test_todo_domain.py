from __future__ import annotations

import ast
from pathlib import Path

from coding_deepgent.middleware.planning import (
    PlanContextMiddleware as CompatibilityMiddleware,
)
from coding_deepgent.renderers.planning import (
    render_plan_items as compatibility_render_plan_items,
)
from coding_deepgent.todo import (
    PlanContextMiddleware,
    TerminalPlanRenderer,
    render_plan_items,
)
from coding_deepgent.todo.service import normalize_todos

ROOT = Path(__file__).resolve().parents[2]
TODO_ROOT = ROOT / "src" / "coding_deepgent" / "todo"


def test_todo_domain_package_exists_with_expected_modules() -> None:
    expected = {
        TODO_ROOT / "__init__.py",
        TODO_ROOT / "middleware.py",
        TODO_ROOT / "renderers.py",
        TODO_ROOT / "schemas.py",
        TODO_ROOT / "service.py",
        TODO_ROOT / "state.py",
        TODO_ROOT / "tools.py",
    }

    missing = sorted(
        str(path.relative_to(ROOT)) for path in expected if not path.exists()
    )
    assert not missing, f"missing expected todo domain files: {missing}"


def test_todo_domain_public_contract_matches_current_owning_modules() -> None:
    assert CompatibilityMiddleware is PlanContextMiddleware
    assert compatibility_render_plan_items is render_plan_items


def test_todo_domain_renderer_output_stays_stable() -> None:
    renderer = TerminalPlanRenderer()

    assert renderer.render_plan_items(
        [
            {
                "content": "Inspect repo",
                "status": "completed",
                "activeForm": "Inspecting",
            },
            {
                "content": "Implement renderer seam",
                "status": "in_progress",
                "activeForm": "Implementing",
            },
            {
                "content": "Verify behavior",
                "status": "pending",
                "activeForm": "Verifying",
            },
        ]
    ) == (
        "[x] Inspect repo\n"
        "[>] Implement renderer seam (Implementing)\n"
        "[ ] Verify behavior\n"
        "\n"
        "(1/3 completed)"
    )


def test_todo_domain_rejects_overlong_short_term_plan() -> None:
    todos = [
        {
            "content": f"Task {index}",
            "status": "pending",
            "activeForm": f"Working {index}",
        }
        for index in range(13)
    ]

    try:
        normalize_todos(todos)
    except ValueError as exc:
        assert "max 12 todos" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("normalize_todos should reject more than 12 todos")


def test_todo_domain_does_not_import_cross_domain_packages() -> None:
    offenders: list[str] = []

    for path in sorted(TODO_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(
                        (
                            "coding_deepgent.containers",
                            "coding_deepgent.filesystem",
                            "coding_deepgent.sessions",
                        )
                    ):
                        offenders.append(f"{path.name}:{alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith(
                    (
                        "coding_deepgent.containers",
                        "coding_deepgent.filesystem",
                        "coding_deepgent.sessions",
                    )
                ):
                    offenders.append(f"{path.name}:{module}")

    assert offenders == []
