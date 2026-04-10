from __future__ import annotations

import ast
import importlib
import py_compile
import sys
from pathlib import Path
import py_compile

import pytest


ROOT = Path(__file__).resolve().parents[1]
LANGCHAIN_DIR = ROOT / "agents_langchain"
LANGCHAIN_FILES = sorted(
    path for path in LANGCHAIN_DIR.glob("*.py") if path.name != "__init__.py"
)
LANGCHAIN_IDS = [path.name for path in LANGCHAIN_FILES]


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _import_chapter(path: Path, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    monkeypatch.syspath_prepend(str(ROOT))
    module_name = f"agents_langchain.{path.stem}"
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


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
        if isinstance(
            node,
            (
                ast.AsyncFunctionDef,
                ast.ClassDef,
                ast.FunctionDef,
            ),
        ):
            continue
        if isinstance(node, ast.If):
            # Calls under `if __name__ == "__main__"` are direct-run CLI code, not
            # import-time behavior, so they are allowed for these teaching scripts.
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                calls.append(_call_name(child))
    return calls


def _find_function(module_path: Path, function_name: str) -> ast.FunctionDef | None:
    if not module_path.is_file():
        return None

    for node in _parse(module_path).body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    return None


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


def test_langchain_agent_scripts_exist() -> None:
    assert LANGCHAIN_FILES, "expected LangChain teaching scripts"
    for filename in [
        "s01_agent_loop.py",
        "s02_tool_use.py",
        "s03_todo_write.py",
        "s04_subagent.py",
        "s05_skill_loading.py",
        "s06_context_compact.py",
    ]:
        assert LANGCHAIN_DIR.joinpath(filename).exists()


def test_pure_helpers_import_without_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    common = importlib.import_module("agents_langchain.common")
    s03 = importlib.import_module("agents_langchain.s03_todo_write")

    assert common.langchain_model_name()
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        common.build_openai_model()

    todo = s03.TodoManager()
    rendered = todo.update([
        {"content": "Inspect task", "status": "completed"},
        {"content": "Implement", "status": "in_progress", "activeForm": "Implementing"},
    ])
    assert "[x] Inspect task" in rendered
    assert "[>] Implement (Implementing)" in rendered


def test_safe_path_rejects_workspace_escape() -> None:
    common = importlib.import_module("agents_langchain.common")

    with pytest.raises(ValueError, match="escapes workspace"):
        common.safe_path("../outside.txt")


def test_skill_registry_parses_frontmatter(tmp_path: Path) -> None:
    s05 = importlib.import_module("agents_langchain.s05_skill_loading")
    skill_dir = tmp_path / "demo"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\nname: demo\ndescription: Demo skill\n---\n\nUse this skill.\n",
        encoding="utf-8",
    )

    registry = s05.SkillRegistry(tmp_path)


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
    function = None
    for module_path in [
        LANGCHAIN_AGENTS_DIR / "s02_tool_use.py",
        LANGCHAIN_AGENTS_DIR / "_common.py",
        LANGCHAIN_AGENTS_DIR / "common.py",
    ]:
        function = _find_function(module_path, "safe_path")
        if function is not None:
            break

    assert function is not None
    safe_path_body = "\n".join(
        ast.dump(node, include_attributes=False)
        for node in function.body
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


def test_todo_manager_is_importable_and_validates_state_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _import_chapter(
        LANGCHAIN_AGENTS_DIR / "s03_todo_write.py", monkeypatch
    )
    manager = module.TodoManager()

    rendered = manager.update(
        [
            {
                "content": "Write the LangChain smoke tests",
                "status": "in_progress",
                "activeForm": "Writing tests",
            },
            {"content": "Run them without a live API key", "status": "pending"},
        ]
    )
    assert "[>] Write the LangChain smoke tests (Writing tests)" in rendered
    assert "(0/2 completed)" in rendered

    with pytest.raises(ValueError, match="Only one"):
        manager.update(
            [
                {"content": "First", "status": "in_progress"},
                {"content": "Second", "status": "in_progress"},
            ]
        )
