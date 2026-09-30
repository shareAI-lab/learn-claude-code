"""Every chapter REPL quits only on an explicit command (issue #567).

An empty line used to be a silent exit with status 0, which contradicted the
"Type q to quit" banner and, combined with VS Code's environment-activation
line being injected into stdin, made a debugged chapter vanish right after its
banner. An empty line is now ignored and the prompt comes back.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAPTER_FILES = sorted(ROOT.glob("s*/code.py"))


def _quit_checks(source: str) -> list[ast.Compare]:
    """Return every `X.strip().lower() in (...)` / `in {...}` comparison."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1 or not isinstance(node.ops[0], ast.In):
            continue
        left = node.left
        if (
            isinstance(left, ast.Call)
            and isinstance(left.func, ast.Attribute)
            and left.func.attr == "lower"
            and isinstance(left.func.value, ast.Call)
            and isinstance(left.func.value.func, ast.Attribute)
            and left.func.value.func.attr == "strip"
        ):
            found.append(node)
    return found


def test_every_chapter_has_a_repl_quit_check():
    assert len(CHAPTER_FILES) >= 17
    for path in CHAPTER_FILES:
        assert _quit_checks(path.read_text(encoding="utf-8")), f"{path}: no quit command check found"


def test_empty_line_is_never_a_quit_command():
    for path in CHAPTER_FILES:
        for check in _quit_checks(path.read_text(encoding="utf-8")):
            container = check.comparators[0]
            assert isinstance(container, (ast.Tuple, ast.Set)), f"{path}:{check.lineno}"
            values = [c.value for c in container.elts if isinstance(c, ast.Constant)]
            assert "" not in values, f"{path}:{check.lineno}: empty input still quits the REPL"
            assert "q" in values, f"{path}:{check.lineno}: q must still quit"


def test_blank_input_is_skipped_before_the_quit_check():
    pattern = re.compile(r"if not (\w+)\.strip\(\):\n\s+continue\n\s+if \1\.strip\(\)\.lower\(\) in", re.M)
    for path in CHAPTER_FILES:
        if path.parent.name.startswith("s17"):
            continue  # s17 already handled blank input before this change
        assert pattern.search(path.read_text(encoding="utf-8")), f"{path}: blank input is not skipped"
