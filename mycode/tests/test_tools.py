"""builtin 工具端到端测试 (DESIGN.md §10: 每个工具至少 1 条 e2e)。"""
from __future__ import annotations

from mycode.config import load_config
from mycode.tools.builtin import register_builtins, reset_session_state
from mycode.tools.registry import ToolRegistry


def _setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_session_state()
    cfg = load_config(cli_overrides={"model": "test-model", "provider": "custom"})
    reg = ToolRegistry(cfg)
    register_builtins(reg)
    return reg


def _run(reg: ToolRegistry, name: str, **kwargs):
    tool = reg.get(name)
    assert tool, f"tool {name} missing"
    return tool.handler(**kwargs)


def test_read_write_edit_roundtrip(tmp_path, monkeypatch):
    reg = _setup(tmp_path, monkeypatch)
    f = tmp_path / "hello.txt"
    out = _run(reg, "Write", file_path="hello.txt", content="line1\nline2\n")
    assert "Wrote" in out

    read_out = _run(reg, "Read", file_path="hello.txt")
    assert "line1" in read_out and "line2" in read_out
    assert read_out.splitlines()[0].startswith("     1")

    edit_out = _run(
        reg, "Edit",
        file_path="hello.txt",
        old_string="line1",
        new_string="LINE-1",
    )
    assert "Edited" in edit_out
    assert f.read_text().startswith("LINE-1")


def test_write_requires_prior_read(tmp_path, monkeypatch):
    reg = _setup(tmp_path, monkeypatch)
    f = tmp_path / "existing.txt"
    f.write_text("old")
    out = _run(reg, "Write", file_path="existing.txt", content="new")
    assert out.startswith("Error: must Read")

    # Read 之后允许 Write
    _run(reg, "Read", file_path="existing.txt")
    out = _run(reg, "Write", file_path="existing.txt", content="new")
    assert "Wrote" in out
    assert f.read_text() == "new"


def test_edit_ambiguous(tmp_path, monkeypatch):
    reg = _setup(tmp_path, monkeypatch)
    f = tmp_path / "dup.txt"
    f.write_text("x\nx\n")
    out = _run(reg, "Edit", file_path="dup.txt", old_string="x", new_string="y")
    assert "matched 2 times" in out
    out = _run(reg, "Edit", file_path="dup.txt", old_string="x", new_string="y", replace_all=True)
    assert "Edited" in out
    assert f.read_text() == "y\ny\n"


def test_bash_ok_and_deny(tmp_path, monkeypatch):
    reg = _setup(tmp_path, monkeypatch)
    out = _run(reg, "Bash", command="echo hi")
    assert "hi" in out
    out = _run(reg, "Bash", command="sudo ls")
    assert out.startswith("Error: command blocked")


def test_bash_exit_code(tmp_path, monkeypatch):
    reg = _setup(tmp_path, monkeypatch)
    out = _run(reg, "Bash", command="false")
    assert "[exit code: 1]" in out


def test_glob(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "b.py").write_text("y")
    (tmp_path / "c.txt").write_text("z")
    reg = _setup(tmp_path, monkeypatch)
    out = _run(reg, "Glob", pattern="*.py")
    assert "a.py" in out and "b.py" in out
    assert "c.txt" not in out


def test_grep_content(tmp_path, monkeypatch):
    (tmp_path / "src.py").write_text("def foo():\n    return 1\n")
    (tmp_path / "other.py").write_text("def bar():\n    return 2\n")
    reg = _setup(tmp_path, monkeypatch)
    out = _run(reg, "Grep", pattern="foo", output_mode="content")
    assert "def foo" in out


def test_read_binary_placeholder(tmp_path, monkeypatch):
    (tmp_path / "img.bin").write_bytes(b"\x00\x01\x02" * 100)
    reg = _setup(tmp_path, monkeypatch)
    out = _run(reg, "Read", file_path="img.bin")
    assert out.startswith("[binary")


def test_path_denied(tmp_path, monkeypatch):
    reg = _setup(tmp_path, monkeypatch)
    out = _run(reg, "Read", file_path="../../../../etc/passwd")
    assert out.startswith("Error:") and "escapes workspace" in out


def test_read_offset_limit(tmp_path, monkeypatch):
    f = tmp_path / "many.txt"
    f.write_text("\n".join(f"line{i}" for i in range(1, 21)) + "\n")
    reg = _setup(tmp_path, monkeypatch)
    out = _run(reg, "Read", file_path="many.txt", offset=10, limit=3)
    lines = [l for l in out.splitlines() if l.strip().startswith(("1", "2"))]
    # 行号前缀必须是真实的 11/12/13
    nums = [int(l.split("\t")[0].strip()) for l in out.splitlines() if "\t" in l and not l.startswith("...")]
    assert nums == [11, 12, 13]
