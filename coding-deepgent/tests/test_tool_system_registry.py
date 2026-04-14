from __future__ import annotations

from pathlib import Path

from dependency_injector import providers

from coding_deepgent.containers import AppContainer
from coding_deepgent.settings import Settings


EXPECTED_MAIN_TOOL_NAMES = [
    "bash",
    "read_file",
    "write_file",
    "edit_file",
    "TodoWrite",
    "save_memory",
    "load_skill",
    "task_create",
    "task_get",
    "task_list",
    "task_update",
    "plan_save",
    "plan_get",
    "run_subagent",
]


def _container(tmp_path: Path) -> AppContainer:
    return AppContainer(
        settings=providers.Object(Settings(workdir=tmp_path)),
        model=providers.Object(object()),
        create_agent_factory=providers.Object(lambda **kwargs: object()),
    )


def test_capability_inventory_exposes_child_only_and_main_projections(
    tmp_path: Path,
) -> None:
    registry = _container(tmp_path).capability_registry()

    assert "glob" in registry.names()
    assert "grep" in registry.names()
    assert registry.child_names() == ["glob", "grep"]
    assert "glob" not in registry.main_names()
    assert "grep" not in registry.main_names()
    assert "glob" not in registry.declarable_names()
    assert "grep" not in registry.declarable_names()
    assert "save_memory" in registry.main_names()
    assert "task_create" in registry.main_names()


def test_main_projection_preserves_current_product_tool_surface(
    tmp_path: Path,
) -> None:
    registry = _container(tmp_path).capability_registry()

    tool_names = [
        getattr(tool, "name", type(tool).__name__) for tool in registry.main_tools()
    ]

    assert tool_names == EXPECTED_MAIN_TOOL_NAMES
