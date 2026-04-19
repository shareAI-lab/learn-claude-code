"""M2-3: MCP 客户端测试 (不起真实 server,只测纯逻辑部分)。"""
from __future__ import annotations

import pytest

from oai_code.mcp import _prefixed_tool_name, _resolve_env


# ---------- tool 名前缀策略 ----------

def test_short_name_uses_verbatim():
    assert _prefixed_tool_name("linear", "create_issue") == "mcp__linear__create_issue"


def test_long_name_is_hashed():
    very_long = "x" * 80
    out = _prefixed_tool_name("srv", very_long)
    assert out.startswith("mcp__srv__")
    # 原工具名不应完整出现
    assert very_long not in out
    assert len(out) <= 64


def test_hash_is_deterministic():
    name = "y" * 100
    assert _prefixed_tool_name("s", name) == _prefixed_tool_name("s", name)


# ---------- _env 规则 ----------

def test_env_suffix_resolves_from_os_env(monkeypatch):
    monkeypatch.setenv("MY_SECRET", "s3cret")
    out = _resolve_env({"API_KEY_env": "MY_SECRET", "LOG_LEVEL": "debug"})
    assert out == {"API_KEY": "s3cret", "LOG_LEVEL": "debug"}


def test_env_missing_raises(monkeypatch):
    monkeypatch.delenv("NOPE", raising=False)
    with pytest.raises(RuntimeError, match="NOPE"):
        _resolve_env({"API_KEY_env": "NOPE"})


def test_env_literal_passthrough():
    out = _resolve_env({"FLAG": "yes"})
    assert out == {"FLAG": "yes"}


# ---------- MCPManager 未启动时的调用 ----------

def test_call_without_connection_returns_error(tmp_path, monkeypatch):
    from oai_code.config import load_config
    from oai_code.mcp import MCPManager

    monkeypatch.chdir(tmp_path)
    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    mgr = MCPManager(cfg)
    out = mgr.call_tool("unknown", "doit", {})
    assert out.startswith("Error: mcp server 'unknown' not connected")


def test_summary_empty():
    from oai_code.config import load_config
    from oai_code.mcp import MCPManager

    cfg = load_config(cli_overrides={"model": "test", "provider": "custom"})
    mgr = MCPManager(cfg)
    assert "no mcp servers" in mgr.summary()
