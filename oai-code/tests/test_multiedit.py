"""M4-4: MultiEdit 工具测试(原子性 + 级联应用)。"""
from __future__ import annotations

from oai_code.config import load_config
from oai_code.tools.builtin import register_builtins, reset_session_state
from oai_code.tools.registry import ToolRegistry


def _reg(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_session_state()
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    reg = ToolRegistry(cfg)
    register_builtins(reg)
    return reg


def test_multiedit_two_sequential_edits(tmp_path, monkeypatch):
    reg = _reg(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("hello world\n")
    out = reg.get("MultiEdit").handler(
        file_path="a.txt",
        edits=[
            {"old_string": "hello", "new_string": "HI"},
            {"old_string": "world", "new_string": "THERE"},
        ],
    )
    assert "applied 2 edits" in out
    assert (tmp_path / "a.txt").read_text() == "HI THERE\n"


def test_multiedit_cascade_sees_prior_output(tmp_path, monkeypatch):
    """第二个 edit 应用的是第一个 edit 之后的内容。"""
    reg = _reg(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("foo\n")
    out = reg.get("MultiEdit").handler(
        file_path="a.txt",
        edits=[
            {"old_string": "foo", "new_string": "bar"},
            {"old_string": "bar", "new_string": "baz"},
        ],
    )
    assert "applied 2 edits" in out
    assert (tmp_path / "a.txt").read_text() == "baz\n"


def test_multiedit_atomic_rollback_on_miss(tmp_path, monkeypatch):
    """任何 edit 的 old_string 找不到 → 整体回滚,文件不变。"""
    reg = _reg(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("foo bar baz\n")
    out = reg.get("MultiEdit").handler(
        file_path="a.txt",
        edits=[
            {"old_string": "foo", "new_string": "FOO"},
            {"old_string": "DOES_NOT_EXIST", "new_string": "X"},
        ],
    )
    assert out.startswith("Error")
    # 文件必须未被修改
    assert (tmp_path / "a.txt").read_text() == "foo bar baz\n"


def test_multiedit_ambiguous_without_replace_all(tmp_path, monkeypatch):
    reg = _reg(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("x\nx\n")
    out = reg.get("MultiEdit").handler(
        file_path="a.txt",
        edits=[{"old_string": "x", "new_string": "y"}],
    )
    assert "matched 2 times" in out
    assert (tmp_path / "a.txt").read_text() == "x\nx\n"


def test_multiedit_replace_all(tmp_path, monkeypatch):
    reg = _reg(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("x\nx\n")
    out = reg.get("MultiEdit").handler(
        file_path="a.txt",
        edits=[{"old_string": "x", "new_string": "y", "replace_all": True}],
    )
    assert "applied 1 edits (2 replacements)" in out
    assert (tmp_path / "a.txt").read_text() == "y\ny\n"


def test_multiedit_missing_file(tmp_path, monkeypatch):
    reg = _reg(tmp_path, monkeypatch)
    out = reg.get("MultiEdit").handler(
        file_path="nope.txt",
        edits=[{"old_string": "a", "new_string": "b"}],
    )
    assert out.startswith("Error: file not found")


def test_multiedit_empty_edits_rejected(tmp_path, monkeypatch):
    reg = _reg(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("x\n")
    out = reg.get("MultiEdit").handler(file_path="a.txt", edits=[])
    assert out.startswith("Error")


def test_multiedit_denied_path(tmp_path, monkeypatch):
    reg = _reg(tmp_path, monkeypatch)
    out = reg.get("MultiEdit").handler(
        file_path="../../etc/passwd",
        edits=[{"old_string": "a", "new_string": "b"}],
    )
    assert out.startswith("Error") and "escapes workspace" in out


def test_multiedit_preserves_earlier_when_later_ambiguous(tmp_path, monkeypatch):
    """边界:第一个 edit 成功但第二个多次匹配,必须回滚。"""
    reg = _reg(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("foo x y x\n")
    out = reg.get("MultiEdit").handler(
        file_path="a.txt",
        edits=[
            {"old_string": "foo", "new_string": "bar"},
            {"old_string": "x", "new_string": "Z"},  # 会多次匹配
        ],
    )
    assert out.startswith("Error")
    assert (tmp_path / "a.txt").read_text() == "foo x y x\n"
