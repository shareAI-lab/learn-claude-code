#!/usr/bin/env python3
# Harness: external tool providers -- tools from outside the agent process.
"""
s06_mcp_tools.py - MCP (Model Context Protocol) Tools

Connect to an external MCP server that provides additional tools.
The agent discovers MCP tools at startup and merges them with local tools.

    Local Tools                    MCP Server (external process)
    +------------------+           +------------------+
    | bash             |           | get_weather      |
    | read_file        |           | search_web       |
    | write_file       |           |                  |
    +------------------+           +------------------+
            |                                |
            ----------- merge --------------
                         |
                         v
                   All tools presented
                   to the model

Key insight: "MCP tools look identical to local tools from the model's perspective."
"""

import os
import subprocess
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]


# -- Mock MCP Server --
# In real usage, this would be an external process communicating via stdio/HTTP.
# For teaching purposes, we simulate it with in-process functions.

class MockMcpServer:
    """Simulates an MCP server that provides weather and search tools."""

    def __init__(self):
        self.name = "mock-mcp-server"
        self.tools = self._discover_tools()

    def _discover_tools(self) -> list:
        """MCP servers expose their tools via a discover/list endpoint."""
        return [
            {
                "name": "get_weather",
                "description": "Get current weather for a city.",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string", "description": "City name"}},
                    "required": ["city"],
                },
                "mcp_server": self.name,  # Mark as MCP tool for routing
            },
            {
                "name": "search_web",
                "description": "Search the web for information.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"],
                },
                "mcp_server": self.name,
            },
        ]

    def call_tool(self, name: str, args: dict) -> str:
        """Execute a tool on the MCP server."""
        if name == "get_weather":
            city = args.get("city", "Unknown")
            # Simulated weather data
            weather_data = {
                "北京": {"temp": 22, "condition": "晴", "humidity": 45},
                "上海": {"temp": 25, "condition": "多云", "humidity": 70},
                "东京": {"temp": 18, "condition": "雨", "humidity": 85},
            }
            w = weather_data.get(city, {"temp": 20, "condition": "未知", "humidity": 60})
            return f"{city}: {w['temp']}°C, {w['condition']}, 湿度 {w['humidity']}%"
        elif name == "search_web":
            query = args.get("query", "")
            return f"搜索结果 for '{query}': [模拟] 没有找到相关结果"
        else:
            return f"Error: Unknown MCP tool '{name}'"


# -- MCP Client: discovers tools and routes calls --

class MccClient:
    """Connects to MCP servers and integrates their tools into the agent."""

    def __init__(self):
        self.servers = {}

    def connect(self, server: MockMcpServer):
        """Connect to an MCP server and register its tools."""
        print(f"Connecting to MCP server: {server.name}")
        self.servers[server.name] = server
        self.tools = []
        for server in self.servers.values():
            self.tools.extend(server.tools)
        print(f"  Discovered {len(self.tools)} tools: {[t['name'] for t in self.tools]}")

    def get_tools(self) -> list:
        """Return all MCP tools for merging with local tools."""
        return self.tools

    def route_tool(self, name: str, args: dict) -> str:
        """Find which server owns this tool and call it."""
        for server_name, server in self.servers.items():
            for tool in server.tools:
                if tool["name"] == name:
                    return server.call_tool(name, args)
        return f"Error: Tool '{name}' not found in any MCP server"


# -- Local tool implementations (same as s05) --

def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {path}")
    return path


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def run_read(path: str, limit: int | None = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes"
    except Exception as e:
        return f"Error: {e}"


LOCAL_TOOLS = [
    {
        "name": "bash",
        "description": "Run a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read file contents.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
]

LOCAL_HANDLERS = {
    "bash": lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
}


# -- Setup MCP connection --

mcp_client = MccClient()
mcp_client.connect(MockMcpServer())

# Merge local tools + MCP tools
ALL_TOOLS = LOCAL_TOOLS + mcp_client.get_tools()

# Build description list for system prompt
TOOL_LISTING = "\n".join(f"  - {t['name']}: {t['description']}" for t in ALL_TOOLS)
LOCAL_NAMES = {t["name"] for t in LOCAL_TOOLS}
MCP_NAMES = {t["name"] for t in mcp_client.get_tools()}

SYSTEM = f"""You are a coding agent at {WORKDIR}.
Available tools:
{TOOL_LISTING}

Local tools (bash, read_file, write_file) work normally.
MCP tools (get_weather, search_web) connect to external services."""


def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=ALL_TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                # Route: local tools -> local handlers, MCP tools -> MCP client
                if block.name in LOCAL_HANDLERS:
                    handler = LOCAL_HANDLERS[block.name]
                    output = handler(**block.input)
                    source = "local"
                elif block.name in MCP_NAMES:
                    output = mcp_client.route_tool(block.name, block.input)
                    source = "mcp"
                else:
                    output = f"Unknown tool: {block.name}"
                    source = "?"
                print(f"> {source}:{block.name}: {str(output)[:200]}")
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(output),
                    }
                )
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms06 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
