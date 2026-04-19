"""M3-2: 退出总结写 .mycode/MEMORY.md 测试。"""
from __future__ import annotations

from mycode.config import load_config
from mycode.memory import summarize_to_memory


class _StubLLM:
    def __init__(self, content="- user prefers Chinese\n- use uv for deps"):
        self._content = content

    def call(self, messages, tools=None):
        class R:
            content = self._content
            tool_calls: list = []
            finish_reason = "stop"
            raw = None
        r = R()
        r.content = self._content
        return r


def _cfg(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    return load_config(cli_overrides={"model": "test", "provider": "custom"})


def test_empty_conversation(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    out = summarize_to_memory([], cfg, _StubLLM())
    assert "no conversation" in out
    assert not (tmp_path / ".mycode" / "MEMORY.md").exists()


def test_system_only_returns_no_convo(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    out = summarize_to_memory(
        [{"role": "system", "content": "sys"}], cfg, _StubLLM()
    )
    assert "no conversation" in out


def test_appends_with_header_on_first_write(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    msgs = [
        {"role": "user", "content": "我喜欢中文"},
        {"role": "assistant", "content": "好的"},
    ]
    out = summarize_to_memory(msgs, cfg, _StubLLM())
    mem = tmp_path / ".mycode" / "MEMORY.md"
    assert mem.exists()
    text = mem.read_text()
    assert "Auto-generated memory" in text  # header 只在第一次写
    assert "## Auto summary" in text
    assert "user prefers Chinese" in text
    assert "Appended" in out


def test_second_append_no_duplicate_header(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    msgs = [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}]
    summarize_to_memory(msgs, cfg, _StubLLM("- first"))
    summarize_to_memory(msgs, cfg, _StubLLM("- second"))
    text = (tmp_path / ".mycode" / "MEMORY.md").read_text()
    # header 只出现一次
    assert text.count("Auto-generated memory") == 1
    # 两个 Auto summary 块
    assert text.count("## Auto summary") == 2
    assert "first" in text and "second" in text


def test_nothing_new_skipped(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    out = summarize_to_memory(msgs, cfg, _StubLLM("(nothing new)"))
    assert "nothing worth saving" in out
    # 文件不应被写入(或写入但无内容块) —— 当前实现不写
    mem = tmp_path / ".mycode" / "MEMORY.md"
    assert not mem.exists() or "Auto summary" not in mem.read_text()


def test_llm_error_surfaced(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)

    class _Bad:
        def call(self, *a, **kw):
            raise RuntimeError("boom")

    out = summarize_to_memory(
        [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}],
        cfg, _Bad(),
    )
    assert out.startswith("Error: summarize failed")
