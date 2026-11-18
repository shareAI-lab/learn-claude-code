import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = tuple(sorted([
    *ROOT.glob("s*/code.py"),
    *ROOT.glob("agents/*.py"),
]))
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def string_assignments(tree: ast.AST) -> dict[str, str]:
    values = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                values[target.id] = value.value
    return values


def input_prompts(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assignments = string_assignments(tree)
    prompts = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        is_input = isinstance(node.func, ast.Name) and node.func.id == "input"
        is_console_ask = isinstance(node.func, ast.Attribute) and node.func.attr == "ask"
        if not (is_input or is_console_ask):
            continue
        if not node.args:
            if is_console_ask and "READLINE_PROMPT" in assignments:
                prompts.append((node.lineno, assignments["READLINE_PROMPT"]))
            continue
        argument = node.args[0]
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            prompts.append((node.lineno, argument.value))
        elif isinstance(argument, ast.Name) and argument.id in assignments:
            prompts.append((node.lineno, assignments[argument.id]))
    return prompts


def test_colored_input_prompts_mark_ansi_as_zero_width() -> None:
    checked = 0
    invalid = []
    for path in SOURCE_FILES:
        for lineno, prompt in input_prompts(path):
            escapes = list(ANSI_ESCAPE.finditer(prompt))
            if not escapes:
                assert "\x01" not in prompt and "\x02" not in prompt
                continue
            checked += 1
            for escape in escapes:
                marked = (
                    prompt[escape.start() - 1:escape.start()] == "\x01"
                    and prompt[escape.end():escape.end() + 1] == "\x02"
                )
                if not marked:
                    invalid.append(f"{path.relative_to(ROOT)}:{lineno}")
                    break

    assert checked, "expected at least one colored input prompt"
    assert not invalid, "ANSI escapes missing Readline markers:\n" + "\n".join(invalid)


def test_async_redraw_prompts_keep_markers_out_of_display_text() -> None:
    for lesson in ("s15_integrated_harness", "s16_workflow_runtime"):
        path = ROOT / lesson / "code.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assignments = string_assignments(tree)
        display_prompt = assignments["PROMPT"]
        readline_prompt = assignments["READLINE_PROMPT"]

        assert "\x01" not in display_prompt and "\x02" not in display_prompt
        assert readline_prompt.replace("\x01", "").replace("\x02", "") == display_prompt
