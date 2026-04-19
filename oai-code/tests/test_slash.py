"""M2-4: REPL slash 命令辅助方法测试 (不起真 LLM)。"""
from __future__ import annotations

from io import StringIO

from rich.console import Console

from oai_code.agent.loop import AgentState
from oai_code.config import load_config
from oai_code.session import SessionStore
from oai_code.tools.registry import ToolRegistry
from oai_code.ui.repl import Repl


def _make_repl(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    registry = ToolRegistry(cfg)
    store = SessionStore(cfg)
    store.new_session()

    repl = Repl(
        cfg,
        llm=None,
        registry=registry,
        system_prompt="SYSTEM",
        session_store=store,
    )
    repl.console = Console(file=StringIO(), force_terminal=False, width=120)
    return repl


def _output(repl) -> str:
    return repl.console.file.getvalue()


def test_system_prompt_rendered(tmp_path, monkeypatch):
    repl = _make_repl(tmp_path, monkeypatch)
    repl._print_system()
    out = _output(repl)
    assert "system prompt" in out
    assert "SYSTEM" in out


def test_history_rendered(tmp_path, monkeypatch):
    repl = _make_repl(tmp_path, monkeypatch)
    repl.state.messages.extend(
        [
            {"role": "user", "content": "hi there"},
            {"role": "assistant", "content": "hello"},
        ]
    )
    repl._print_history(10)
    out = _output(repl)
    assert "user" in out
    assert "hi there" in out
    assert "assistant" in out


def test_debug_status_includes_metrics(tmp_path, monkeypatch):
    repl = _make_repl(tmp_path, monkeypatch)
    repl.state.messages.append({"role": "user", "content": "x" * 400})
    repl._print_debug_status()
    out = _output(repl)
    assert "messages=" in out
    assert "est_tokens=" in out


def test_list_sessions_shows_current(tmp_path, monkeypatch):
    repl = _make_repl(tmp_path, monkeypatch)
    repl._session_store.append_new_messages([{"role": "user", "content": "first"}])
    repl._list_sessions()
    out = _output(repl)
    assert repl._session_store.session_id in out
    assert "●" in out


def test_save_slash(tmp_path, monkeypatch):
    repl = _make_repl(tmp_path, monkeypatch)
    repl.state.messages.append({"role": "user", "content": "hello"})
    repl._handle_slash("/save")
    out = _output(repl)
    assert "saved session" in out
    # jsonl 实际落盘
    assert repl._session_store.path().exists()
    assert "hello" in repl._session_store.path().read_text()


def test_help_grouped(tmp_path, monkeypatch):
    repl = _make_repl(tmp_path, monkeypatch)
    repl._handle_slash("/help")
    out = _output(repl)
    assert "session" in out
    assert "inspect" in out
    assert "model" in out
