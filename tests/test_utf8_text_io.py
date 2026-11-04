import ast
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = tuple(sorted([
    *ROOT.glob("s*/code.py"),
    *ROOT.glob("agents/*.py"),
    *ROOT.glob("skills/agent-builder/**/*.py"),
]))


def missing_encoding(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    missing = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        path_method = (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"read_text", "write_text"}
        )
        builtin_open = isinstance(node.func, ast.Name) and node.func.id == "open"
        path_open = (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "open"
            and not (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
            )
        )
        if not (path_method or builtin_open or path_open):
            continue
        if not any(keyword.arg == "encoding" for keyword in node.keywords):
            mode_index = 1 if builtin_open else 0
            mode = node.args[mode_index] if len(node.args) > mode_index else None
            if (isinstance(mode, ast.Constant) and isinstance(mode.value, str)
                    and "b" in mode.value):
                continue
            label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
            missing.append(f"{label}:{node.lineno}")
    return missing


def test_teaching_sources_declare_text_encoding() -> None:
    missing = [item for path in SOURCE_FILES for item in missing_encoding(path)]
    assert not missing, "text operations missing encoding:\n" + "\n".join(missing)


def test_agent_builder_generates_utf8_text_tools(tmp_path: Path) -> None:
    script = ROOT / "skills" / "agent-builder" / "scripts" / "init_agent.py"
    spec = importlib.util.spec_from_file_location("agent_builder_init", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.create_agent("utf8-agent", 2, tmp_path)

    generated = tmp_path / "utf8-agent" / "utf8-agent.py"
    assert not missing_encoding(generated)
