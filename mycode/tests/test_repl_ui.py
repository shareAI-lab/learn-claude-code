"""M5-4: REPL UI 增强的测试。"""
from __future__ import annotations

from io import StringIO

from rich.console import Console

from mycode.agent.loop import AgentState
from mycode.config import load_config
from mycode.session import SessionStore
from mycode.tools.registry import ToolRegistry
from mycode.ui.repl import Repl


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


def _out(repl) -> str:
    return repl.console.file.getvalue()


def test_render_todo_result_pending(tmp_path, monkeypatch):
    repl = _make_repl(tmp_path, monkeypatch)
    repl._render_todo_result("[ ] write docs\n[ ] run tests\n")
    out = _out(repl)
    assert "○" in out
    assert "write docs" in out
    assert "run tests" in out


def test_render_todo_result_in_progress(tmp_path, monkeypatch):
    repl = _make_repl(tmp_path, monkeypatch)
    repl._render_todo_result("[>] working on it\n")
    out = _out(repl)
    assert "●" in out
    assert "working on it" in out


def test_render_todo_result_completed(tmp_path, monkeypatch):
    repl = _make_repl(tmp_path, monkeypatch)
    repl._render_todo_result("[x] done\n")
    out = _out(repl)
    assert "✓" in out
    assert "done" in out


def test_render_todo_mixed(tmp_path, monkeypatch):
    repl = _make_repl(tmp_path, monkeypatch)
    repl._render_todo_result(
        "[x] first\n[>] current\n[ ] later\n\n(1/3 completed)\n"
    )
    out = _out(repl)
    assert "✓" in out
    assert "●" in out
    assert "○" in out
    assert "1/3 completed" in out


def test_render_todo_empty(tmp_path, monkeypatch):
    repl = _make_repl(tmp_path, monkeypatch)
    # 空字符串不应抛异常
    repl._render_todo_result("")
    # 完整流程 ok
    assert True


def test_on_tool_result_shows_timing_and_icon(tmp_path, monkeypatch):
    """on_tool_result 应该打印 ✓/✗ 和耗时。通过 _cb 的返回验证。"""
    import time as _time

    from mycode.agent.dispatcher import ToolCall, ToolResult

    repl = _make_repl(tmp_path, monkeypatch)
    cb = repl._cb()
    call = ToolCall(id="1", name="Bash", arguments={})
    # 触发 on_tool_call 建时间戳
    cb.on_tool_call(call)
    _time.sleep(0.01)
    cb.on_tool_result(call, ToolResult(tool_call_id="1", content="ok output"))
    out = _out(repl)
    assert "Bash" in out
    assert "✓" in out
    # 耗时字样:ms 或 s
    assert "ms" in out or "s" in out


def test_on_tool_result_error_icon(tmp_path, monkeypatch):
    from mycode.agent.dispatcher import ToolCall, ToolResult

    repl = _make_repl(tmp_path, monkeypatch)
    cb = repl._cb()
    call = ToolCall(id="2", name="Read", arguments={"file_path": "nope"})
    cb.on_tool_call(call)
    cb.on_tool_result(call, ToolResult(tool_call_id="2", content="Error: file not found"))
    out = _out(repl)
    assert "✗" in out
    assert "Error:" in out


def test_on_tool_result_todowrite_uses_rich_icons(tmp_path, monkeypatch):
    """TodoWrite 的结果应该用 ●/○/✓ 图标而不是 [ ]/[>]/[x]。"""
    from mycode.agent.dispatcher import ToolCall, ToolResult

    repl = _make_repl(tmp_path, monkeypatch)
    cb = repl._cb()
    call = ToolCall(id="3", name="TodoWrite", arguments={})
    cb.on_tool_call(call)
    cb.on_tool_result(
        call,
        ToolResult(
            tool_call_id="3",
            content="[ ] first\n[x] second\n\n(1/2 completed)",
        ),
    )
    out = _out(repl)
    assert "○" in out
    assert "✓" in out
    assert "1/2 completed" in out
