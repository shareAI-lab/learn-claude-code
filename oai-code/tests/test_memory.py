"""M1-1: memory 加载器测试。"""
from __future__ import annotations

from pathlib import Path

from oai_code.memory import load_all, load_memory_file
from oai_code.memory.loader import MEMORY_FILE_MAX_BYTES


def test_load_basic(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("project notes\n", encoding="utf-8")
    out = load_memory_file("CLAUDE.md", cwd=tmp_path)
    assert out is not None
    assert "project notes" in out
    assert "<memory path=" in out


def test_load_missing_returns_none(tmp_path):
    assert load_memory_file("NOPE.md", cwd=tmp_path) is None


def test_empty_file_returns_none(tmp_path):
    (tmp_path / "empty.md").write_text("   \n\n  ", encoding="utf-8")
    assert load_memory_file("empty.md", cwd=tmp_path) is None


def test_home_expand(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    (fake_home / "user.md").write_text("user memory", encoding="utf-8")
    monkeypatch.setenv("HOME", str(fake_home))
    out = load_memory_file("~/user.md", cwd=tmp_path)
    assert out and "user memory" in out


def test_too_large_returns_truncated_placeholder(tmp_path):
    big = "x" * (MEMORY_FILE_MAX_BYTES + 1)
    (tmp_path / "big.md").write_text(big, encoding="utf-8")
    out = load_memory_file("big.md", cwd=tmp_path)
    assert out is not None
    assert "truncated" in out
    assert "too large" in out


def test_load_all_order_and_skip_missing(tmp_path):
    (tmp_path / "a.md").write_text("A", encoding="utf-8")
    (tmp_path / "c.md").write_text("C", encoding="utf-8")
    out = load_all(["a.md", "missing.md", "c.md"], cwd=tmp_path)
    assert len(out) == 2
    assert "A" in out[0]
    assert "C" in out[1]


def test_reference_expansion(tmp_path):
    (tmp_path / "shared.md").write_text("shared content", encoding="utf-8")
    (tmp_path / "main.md").write_text("top\n@shared.md\nend\n", encoding="utf-8")
    out = load_memory_file("main.md", cwd=tmp_path)
    assert out is not None
    assert "top" in out and "end" in out
    assert "<ref path=" in out
    assert "shared content" in out


def test_reference_cycle_safe(tmp_path):
    (tmp_path / "a.md").write_text("AA\n@b.md\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("BB\n@a.md\n", encoding="utf-8")
    out = load_memory_file("a.md", cwd=tmp_path)
    assert out is not None
    # 循环引用会被 seen 拦下,不应无限展开
    assert out.count("<ref path=") <= 2


def test_reference_missing(tmp_path):
    (tmp_path / "main.md").write_text("@nope.md\n", encoding="utf-8")
    out = load_memory_file("main.md", cwd=tmp_path)
    assert out and "memory ref not found" in out
