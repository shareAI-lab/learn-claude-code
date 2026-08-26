import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LESSON_PATHS = (
    ROOT / "s03_permission" / "code.py",
    ROOT / "s04_hooks" / "code.py",
    ROOT / "s05_todo_write" / "code.py",
    ROOT / "s06_subagent" / "code.py",
    ROOT / "s07_skill_loading" / "code.py",
    ROOT / "s08_context_compact" / "code.py",
    ROOT / "s09_memory" / "code.py",
    ROOT / "s10_task_system" / "code.py",
    ROOT / "s11_background_tasks" / "code.py",
    ROOT / "s12_cron_scheduler" / "code.py",
    ROOT / "s13_agent_teams" / "code.py",
    ROOT / "s14_mcp_plugin" / "code.py",
    ROOT / "s17_goal_loop" / "code.py",
)

DESTRUCTIVE_COMMANDS = [
    # Direct standalone commands
    "rm test.txt",
    "del test.txt",
    "rmdir /s /q build",
    "erase file.txt",
    "DEL test.txt",
    "RM -rf build",
    "RMDIR temp",
    "del",
    "rm",
    # Windows flags attached without space
    "del/f test.txt",
    "del/f/q/s test.txt",
    "rmdir/s/q build",
    "erase/p old.txt",
    # Commands after chaining delimiters
    "echo hello && del test.txt",
    "echo hello && rm test.txt",
    "echo hello && del/f test.txt",
    "echo hello || rm test.txt",
    "echo hello || del test.txt",
    "echo hello; rm test.txt",
    "echo hello; del test.txt",
    "echo hello & del test.txt",
    "echo hello & rm test.txt",
    "echo hello | rm test.txt",
    "echo hello | del test.txt",
    "echo hello\ndel test.txt",
    "echo hello\nrm test.txt",
    "  del test.txt",
    "   rm -rf /tmp/test",
    "cd dir; del *",
    "cd dir &&  rmdir /s /q temp",
    # System modification patterns
    "> /etc/passwd",
    "echo root > /etc/shadow",
    "chmod 777 script.sh",
    "chmod 777 file.py",
]

NON_DESTRUCTIVE_COMMANDS = [
    # Commands with keywords as arguments (e.g. echo, git, grep)
    "echo del test.txt",
    "echo rm test.txt",
    "echo rmdir build",
    "echo erase everything",
    'git commit -m "del test.txt"',
    'git commit -m "rm test.txt"',
    'git commit -m "rmdir temp"',
    "grep rm test.py",
    "grep del test.py",
    "grep rmdir test.py",
    'python -c "print(\'del\')"',
    'node -e "console.log(\'rm\')"',
    # Substring in identifiers / variable names
    "transform_data()",
    "model_version = 'v1'",
    "order_items = []",
    "delivery_status = 'pending'",
    "format_string()",
    "term_count = 10",
    "karma_points = 5",
    "erase_mode = False",
    "del_flag = True",
    "rm_option = 0",
]


def extract_destructive_pattern(file_path: Path) -> str:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DESTRUCTIVE_PATTERN":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    raise ValueError(f"DESTRUCTIVE_PATTERN not found in {file_path}")


@pytest.mark.parametrize("lesson_path", LESSON_PATHS, ids=lambda p: p.parent.name)
def test_destructive_pattern_exists_in_lessons(lesson_path: Path):
    pattern = extract_destructive_pattern(lesson_path)
    assert pattern, f"Pattern missing in {lesson_path}"


@pytest.mark.parametrize("cmd", DESTRUCTIVE_COMMANDS)
def test_destructive_commands_flagged_across_lessons(cmd: str):
    for lesson_path in LESSON_PATHS:
        pattern_str = extract_destructive_pattern(lesson_path)
        pattern = re.compile(pattern_str, re.IGNORECASE)
        assert pattern.search(cmd), f"Expected destructive match for '{cmd}' using {lesson_path.parent.name} pattern"


@pytest.mark.parametrize("cmd", NON_DESTRUCTIVE_COMMANDS)
def test_non_destructive_commands_not_flagged(cmd: str):
    for lesson_path in LESSON_PATHS:
        pattern_str = extract_destructive_pattern(lesson_path)
        pattern = re.compile(pattern_str, re.IGNORECASE)
        assert not pattern.search(cmd), f"False positive for safe command '{cmd}' using {lesson_path.parent.name} pattern"
