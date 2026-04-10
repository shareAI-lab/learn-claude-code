from __future__ import annotations

import ast
import py_compile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LANGCHAIN_AGENTS_DIR = ROOT / "agents_langchain"

EXPECTED_CHAPTERS = [
    "s01_agent_loop.py",
    "s02_tool_use.py",
    "s03_todo_write.py",
    "s04_subagent.py",
    "s05_skill_loading.py",
    "s06_context_compact.py",
]
EXPECTED_FILES = [LANGCHAIN_AGENTS_DIR / name for name in EXPECTED_CHAPTERS]


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _top_level_calls(tree: ast.Module) -> list[str]:
    calls: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.If):
            # Calls under `if __name__ == "__main__"` are direct-run CLI code, not
            # import-time behavior, so they are allowed for these teaching scripts.
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                calls.append(_call_name(child))
    return calls


def test_langchain_track_files_exist() -> None:
    assert LANGCHAIN_AGENTS_DIR.is_dir(), "expected parallel agents_langchain/ track"
    assert (LANGCHAIN_AGENTS_DIR / "__init__.py").is_file()
    assert (LANGCHAIN_AGENTS_DIR / "README.md").is_file()
    missing = [path.name for path in EXPECTED_FILES if not path.is_file()]
    assert missing == []


@pytest.mark.parametrize("agent_path", EXPECTED_FILES, ids=EXPECTED_CHAPTERS)
def test_langchain_agent_scripts_compile_without_openai_credentials(
    agent_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    _ = py_compile.compile(str(agent_path), doraise=True)


def test_langchain_track_uses_openai_interface_not_anthropic() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8") for path in EXPECTED_FILES
    )

    assert "anthropic" not in sources.lower()
    assert "OPENAI_API_KEY" in sources
    assert "OPENAI_MODEL" in sources
    assert "OPENAI_BASE_URL" in sources


@pytest.mark.parametrize("agent_path", EXPECTED_FILES, ids=EXPECTED_CHAPTERS)
def test_langchain_agent_scripts_do_not_start_models_at_import(
    agent_path: Path,
) -> None:
    tree = _parse(agent_path)
    top_level_calls = set(_top_level_calls(tree))

    assert "ChatOpenAI" not in top_level_calls
    assert "init_chat_model" not in top_level_calls
    assert "create_agent" not in top_level_calls
    assert "invoke" not in top_level_calls


def test_tool_track_keeps_workspace_path_guard_visible() -> None:
    tree = _parse(LANGCHAIN_AGENTS_DIR / "s02_tool_use.py")
    functions = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }

    assert "safe_path" in functions
    safe_path_body = "\n".join(
        ast.dump(node, include_attributes=False)
        for node in functions["safe_path"].body
    )
    assert "resolve" in safe_path_body
    assert "is_relative_to" in safe_path_body or "relative_to" in safe_path_body


def test_planning_track_exposes_pure_todo_manager_contract() -> None:
    tree = _parse(LANGCHAIN_AGENTS_DIR / "s03_todo_write.py")
    classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}

    assert "PlanItem" in classes
    assert "PlanningState" in classes
    assert "TodoManager" in classes

    manager = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "TodoManager"
    )
    method_names = {
        node.name for node in manager.body if isinstance(node, ast.FunctionDef)
    }
    assert {"update", "render"} <= method_names
