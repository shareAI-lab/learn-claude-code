"""最小 MCP stub server,用于 M5-2 E2E 测试。

通过 stdio 暴露 2 个工具:
- echo(text): 原样返回
- add(a, b):  返回 a+b
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("oai-code-stub")


@mcp.tool()
def echo(text: str) -> str:
    """Echo the input verbatim."""
    return text


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


if __name__ == "__main__":
    mcp.run()
