import ast
import os
import runpy
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from test_skill_loading import load_lesson


ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "skills" / "agent-builder" / "scripts" / "init_agent.py"
SOURCE_FILES = tuple(sorted({
    *ROOT.glob("s[0-9][0-9]_*/code.py"),
    *ROOT.glob("agents/*.py"),
    *(ROOT / "skills" / "agent-builder").rglob("*.py"),
}))


def child_command(expression: str, stream: str = "stdout") -> str:
    script = f"import sys; sys.{stream}.buffer.write({expression})"
    args = [sys.executable, "-c", script]
    return subprocess.list2cmdline(args) if os.name == "nt" else shlex.join(args)


@pytest.mark.parametrize(
    ("encoding", "payload", "expected"),
    [
        ("utf-8", "'中文'.encode('utf-8')", "中文"),
        ("gbk", "'中文'.encode('gbk')", "中文"),
        ("gbk", "bytes([0xff])", "\ufffd"),
    ],
)
def test_s07_bash_decodes_output_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
    encoding: str,
    payload: str,
    expected: str,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))
        monkeypatch.setattr(lesson.subprocess.locale, "getencoding", lambda: encoding)

        assert lesson.run_bash(child_command(payload)) == expected


def test_s07_bash_handles_stderr_and_empty_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))
        monkeypatch.setattr(lesson.subprocess.locale, "getencoding", lambda: "gbk")

        assert lesson.run_bash(child_command("bytes([0xff])", "stderr")) == "\ufffd"
        assert lesson.run_bash(child_command("b''")) == "(no output)"


def test_s07_bash_preserves_timeout_message(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lesson = load_lesson(Path(tmp))

        def time_out(*args, **kwargs):
            raise subprocess.TimeoutExpired(args[0], 120)

        monkeypatch.setattr(lesson.subprocess, "run", time_out)
        assert lesson.run_bash("slow command") == "Error: Timeout (120s)"


def find_missing_policy(tree: ast.AST, source: str) -> list[str]:
    missing_policy: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not (
            isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.func.attr in {"run", "Popen"}
        ):
            continue

        keywords = {keyword.arg: keyword.value for keyword in node.keywords}
        text_mode = keywords.get("text")
        if not (isinstance(text_mode, ast.Constant) and text_mode.value is True):
            continue

        errors = keywords.get("errors")
        if not (isinstance(errors, ast.Constant) and errors.value == "replace"):
            missing_policy.append(f"{source}:{node.lineno}")
    return missing_policy


def test_subprocess_text_calls_replace_decode_errors() -> None:
    missing_policy: list[str] = []

    for path in SOURCE_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        missing_policy.extend(find_missing_policy(tree, str(path.relative_to(ROOT))))

    templates = runpy.run_path(str(SCAFFOLD))["TEMPLATES"]
    for level, template in templates.items():
        generated = template.format(name="test_agent")
        missing_policy.extend(
            find_missing_policy(ast.parse(generated), f"generated agent level {level}")
        )

    assert not missing_policy, (
        "subprocess text output must use errors=\"replace\": "
        + ", ".join(missing_policy)
    )
