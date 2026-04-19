"""M5-2: MCP E2E 测试,真实起 stub server 跑 list_tools + call_tool。"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from oai_code.config import load_config
from oai_code.config.models import MCPServerConfig
from oai_code.mcp import MCPManager
from oai_code.tools.registry import ToolRegistry


STUB_PATH = Path(__file__).parent / "fixtures" / "stub_mcp_server.py"


def _have_fastmcp() -> bool:
    try:
        import mcp.server.fastmcp  # noqa: F401
        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _have_fastmcp(),
    reason="mcp.server.fastmcp not available",
)


def _setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    # python executable: 用当前解释器以保证 mcp 包可见
    server_cfg = MCPServerConfig(
        type="stdio",
        command=sys.executable,
        args=[str(STUB_PATH)],
        timeout_sec=10,
    )
    cfg = load_config(
        cli_overrides={
            "model": "test",
            "provider": "custom",
            "mcp_servers": {"stub": server_cfg.model_dump()},
        }
    )
    return cfg


@pytest.fixture
def connected_mgr(tmp_path, monkeypatch):
    cfg = _setup(tmp_path, monkeypatch)
    mgr = MCPManager(cfg)
    started = mgr.start()
    yield mgr, started
    mgr.stop()


def test_server_connects_and_lists_tools(connected_mgr):
    mgr, started = connected_mgr
    assert "stub" in started
    summary = mgr.summary()
    assert "stub" in summary
    # echo 和 add 都应该列出
    assert "echo" in summary
    assert "add" in summary


def test_call_echo_tool(connected_mgr):
    mgr, _ = connected_mgr
    out = mgr.call_tool("stub", "echo", {"text": "hello world"})
    assert "hello world" in out


def test_call_add_tool(connected_mgr):
    mgr, _ = connected_mgr
    out = mgr.call_tool("stub", "add", {"a": 3, "b": 4})
    assert "7" in out


def test_call_unknown_tool_on_existing_server(connected_mgr):
    mgr, _ = connected_mgr
    out = mgr.call_tool("stub", "nonexistent", {})
    # 不同 MCP SDK 版本可能返回 Error: 或异常里的错误信息
    assert out.startswith("Error") or "Unknown tool" in out or "not found" in out.lower()


def test_register_into_registry(tmp_path, monkeypatch):
    cfg = _setup(tmp_path, monkeypatch)
    mgr = MCPManager(cfg)
    mgr.start()
    try:
        reg = ToolRegistry(cfg)
        mapping = mgr.register_into(reg)
        # 至少 echo 和 add 被注册
        registered_names = {reg_name for _, reg_name in mapping}
        assert "mcp__stub__echo" in registered_names
        assert "mcp__stub__add" in registered_names

        # 通过 registry 调用也能工作
        echo_tool = reg.get("mcp__stub__echo")
        out = echo_tool.handler(text="from-registry")
        assert "from-registry" in out
    finally:
        mgr.stop()
