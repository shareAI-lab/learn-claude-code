"""工具派发: 并行/串行策略 (DESIGN §5) + 错误回灌 + 中断安全。"""
from __future__ import annotations

import time

from oai_code.agent.dispatcher import ToolCall, dispatch
from oai_code.config import load_config
from oai_code.tools.builtin import register_builtins, reset_session_state
from oai_code.tools.registry import ToolRegistry


def _make(tmp_path, monkeypatch, **overrides):
    monkeypatch.chdir(tmp_path)
    reset_session_state()
    cli = {"model": "test-model", "provider": "custom", **overrides}
    cfg = load_config(cli_overrides=cli)
    reg = ToolRegistry(cfg)
    register_builtins(reg)
    return cfg, reg


def test_unknown_tool_returns_error(tmp_path, monkeypatch):
    cfg, reg = _make(tmp_path, monkeypatch)
    out = dispatch([ToolCall("1", "Nope", {})], reg, cfg)
    assert out[0].content.startswith("Error:")


def test_denied_tool_returns_error(tmp_path, monkeypatch):
    cfg, reg = _make(tmp_path, monkeypatch, denied_tools=["Bash"])
    out = dispatch([ToolCall("1", "Bash", {"command": "echo hi"})], reg, cfg)
    assert "not allowed" in out[0].content


def test_result_order_matches_input(tmp_path, monkeypatch):
    cfg, reg = _make(tmp_path, monkeypatch)
    calls = [
        ToolCall("a", "Bash", {"command": "echo A"}),
        ToolCall("b", "Bash", {"command": "echo B"}),
        ToolCall("c", "Bash", {"command": "echo C"}),
    ]
    results = dispatch(calls, reg, cfg)
    assert [r.tool_call_id for r in results] == ["a", "b", "c"]
    assert "A" in results[0].content
    assert "C" in results[2].content


def test_same_path_write_serializes(tmp_path, monkeypatch):
    cfg, reg = _make(tmp_path, monkeypatch)
    f = tmp_path / "x.txt"
    f.write_text("seed")
    # 必须先 Read 才能 Write,所以先放个 Read
    calls = [
        ToolCall("r", "Read", {"file_path": "x.txt"}),
        ToolCall("w1", "Write", {"file_path": "x.txt", "content": "A"}),
        ToolCall("w2", "Write", {"file_path": "x.txt", "content": "B"}),
    ]
    results = dispatch(calls, reg, cfg)
    # 三者同路径应全部串行成功
    assert all(not r.content.startswith("Error:") for r in results)


def test_truncation_on_large_output(tmp_path, monkeypatch):
    cfg, reg = _make(tmp_path, monkeypatch, tool_result_max_bytes=1024)
    calls = [ToolCall("a", "Bash", {"command": "python3 -c 'print(\"x\"*5000)'"})]
    out = dispatch(calls, reg, cfg)
    assert "[truncated" in out[0].content
