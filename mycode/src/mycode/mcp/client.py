"""MCP 客户端: 仅 stdio 传输,list_tools + call_tool。

行为:
- 启动时按 cfg.mcp_servers 中 enabled=True 的 server 起子进程
- 在 per-server AsyncExitStack 里维护 ClientSession 生命周期
- 同步接口通过背景 asyncio 线程调度(兼容现有同步 tool handler 模型)
- 拉 list_tools → 注册为 mcp__<server>__<tool>;长度 >64 则哈希缩短
- _env / *_env 规则: key 后缀 _env 表示从环境变量取值
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import threading
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from ..config.models import Config, MCPServerConfig
from ..tools.registry import Tool, ToolRegistry


TOOL_NAME_MAX = 64


def _resolve_env(env_dict: dict[str, str]) -> dict[str, str]:
    """应用 CONFIG §3.7 的 _env 后缀规则。"""
    out: dict[str, str] = {}
    for k, v in env_dict.items():
        if k.endswith("_env"):
            real_key = k[: -len("_env")]
            val = os.environ.get(v)
            if val is None:
                raise RuntimeError(
                    f"mcp env: environment variable '{v}' (for key '{real_key}') is not set"
                )
            out[real_key] = val
        else:
            out[k] = v
    return out


def _prefixed_tool_name(server: str, tool: str) -> str:
    name = f"mcp__{server}__{tool}"
    if len(name) <= TOOL_NAME_MAX:
        return name
    h = hashlib.sha1(tool.encode()).hexdigest()[:8]
    return f"mcp__{server}__{h}"


@dataclass
class MCPServerHandle:
    server_name: str
    cfg: MCPServerConfig
    session: ClientSession
    tools: list[Any] = field(default_factory=list)  # mcp.types.Tool


class MCPManager:
    """在独立线程里跑 asyncio event loop,管理所有 MCP server 连接。"""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stack: AsyncExitStack | None = None
        self._handles: dict[str, MCPServerHandle] = {}
        self._ready = threading.Event()

    # ---------- 生命周期 ----------

    def start(self) -> list[str]:
        """阻塞式启动: 连上全部 enabled server,返回就绪服务器名列表。失败只打警告不抛。"""
        if self._thread is not None:
            return list(self._handles.keys())
        self._thread = threading.Thread(target=self._run, daemon=True, name="mycode-mcp")
        self._thread.start()
        self._ready.wait(timeout=30)
        return list(self._handles.keys())

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._boot())
            self._ready.set()
            self._loop.run_forever()
        except Exception as e:
            print(f"[mcp] fatal: {type(e).__name__}: {e}")
            self._ready.set()

    async def _boot(self) -> None:
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        for name, sc in self.cfg.mcp_servers.items():
            if not sc.enabled:
                continue
            if sc.type not in ("stdio", "sse", "http"):
                print(f"[mcp:{name}] skipped: unknown transport '{sc.type}'")
                continue
            try:
                await self._connect(name, sc)
            except Exception as e:
                print(f"[mcp:{name}] connect failed: {type(e).__name__}: {e}")

    async def _connect(self, name: str, sc: MCPServerConfig) -> None:
        if sc.type == "stdio":
            if not sc.command:
                raise RuntimeError("stdio mcp server missing 'command'")
            env = _resolve_env(sc.env) if sc.env else None
            params = StdioServerParameters(command=sc.command, args=sc.args, env=env)
            ctx = stdio_client(params)
            streams = await self._stack.enter_async_context(ctx)
            read, write = streams[0], streams[1]
        elif sc.type == "sse":
            if not sc.url:
                raise RuntimeError("sse mcp server missing 'url'")
            headers = _resolve_env(sc.headers) if sc.headers else None
            ctx = sse_client(sc.url, headers=headers, timeout=sc.timeout_sec)
            read, write = await self._stack.enter_async_context(ctx)
        elif sc.type == "http":
            if not sc.url:
                raise RuntimeError("http mcp server missing 'url'")
            headers = _resolve_env(sc.headers) if sc.headers else None
            ctx = streamablehttp_client(sc.url, headers=headers, timeout=sc.timeout_sec)
            streams = await self._stack.enter_async_context(ctx)
            read, write = streams[0], streams[1]  # (read, write, get_session_id)
        else:
            raise RuntimeError(f"unknown mcp transport '{sc.type}'")

        session = await self._stack.enter_async_context(ClientSession(read, write))
        await asyncio.wait_for(session.initialize(), timeout=sc.timeout_sec)
        result = await asyncio.wait_for(session.list_tools(), timeout=sc.timeout_sec)
        self._handles[name] = MCPServerHandle(
            server_name=name, cfg=sc, session=session, tools=list(result.tools)
        )
        print(f"[mcp:{name}] connected via {sc.type}; {len(result.tools)} tools")

    def stop(self) -> None:
        if self._loop is None:
            return
        # stack 必须在 loop 线程内关闭
        async def _close() -> None:
            if self._stack is not None:
                await self._stack.__aexit__(None, None, None)
            self._loop.stop()

        try:
            fut = asyncio.run_coroutine_threadsafe(_close(), self._loop)
            fut.result(timeout=5)
        except Exception:
            pass

    # ---------- 同步调用入口 ----------

    def call_tool(self, server: str, tool: str, args: dict) -> str:
        handle = self._handles.get(server)
        if not handle:
            return f"Error: mcp server '{server}' not connected"
        if self._loop is None:
            return "Error: mcp loop not running"

        async def _do() -> str:
            try:
                res = await asyncio.wait_for(
                    handle.session.call_tool(tool, args),
                    timeout=handle.cfg.timeout_sec,
                )
            except asyncio.TimeoutError:
                return f"Error: mcp call_tool timeout ({handle.cfg.timeout_sec}s)"
            # res.content 是 list[TextContent | ImageContent | ...]
            chunks: list[str] = []
            for part in res.content or []:
                text = getattr(part, "text", None)
                if text:
                    chunks.append(text)
            if res.isError:
                return "Error: " + ("\n".join(chunks) or "(mcp returned error with no content)")
            return "\n".join(chunks) or "(mcp returned no text content)"

        try:
            fut = asyncio.run_coroutine_threadsafe(_do(), self._loop)
            return fut.result(timeout=handle.cfg.timeout_sec + 5)
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    # ---------- registry 注册 ----------

    def register_into(self, registry: ToolRegistry) -> list[tuple[str, str]]:
        """把所有已连 server 的 tools 注册进 registry,返回 [(原名, 注册名), ...]。"""
        out: list[tuple[str, str]] = []
        for server_name, handle in self._handles.items():
            for t in handle.tools:
                tool_name = t.name
                reg_name = _prefixed_tool_name(server_name, tool_name)
                schema = t.inputSchema or {
                    "type": "object",
                    "properties": {},
                }
                desc = t.description or f"MCP tool {server_name}/{tool_name}"

                # 用默认值捕获避免闭包陷阱
                def _handler(_srv=server_name, _t=tool_name, **kw):  # noqa
                    return self.call_tool(_srv, _t, kw)

                registry.register(
                    Tool(
                        name=reg_name,
                        description=f"[mcp:{server_name}] {desc}",
                        input_schema=schema,
                        handler=_handler,
                        requires=["network"],
                    )
                )
                out.append((f"{server_name}/{tool_name}", reg_name))
        return out

    def summary(self) -> str:
        if not self._handles:
            return "(no mcp servers connected)"
        lines = []
        for name, h in self._handles.items():
            lines.append(f"  {name}  ({len(h.tools)} tools)")
            for t in h.tools[:10]:
                lines.append(f"    - {t.name}: {(t.description or '')[:60]}")
            if len(h.tools) > 10:
                lines.append(f"    ... {len(h.tools) - 10} more")
        return "\n".join(lines)
