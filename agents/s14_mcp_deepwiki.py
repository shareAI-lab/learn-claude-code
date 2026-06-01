#!/usr/bin/env python3
# Harness: external tool providers -- tools from outside the agent process.
"""
s14_mcp_deepwiki.py - MCP Tools (DeepWiki Example)

Connect to a real MCP server (DeepWiki) that provides repository knowledge tools.
DeepWiki indexes any public GitHub repo and serves AI-generated docs.

    Local Tools                    DeepWiki MCP Server (remote)
    +------------------+           +---------------------------+
    | bash             |           | ask_question(repo, query) |
    | read_file        |           | read_wiki_structure(repo) |
    | write_file       |           | read_wiki_contents(repo)  |
    +------------------+           +---------------------------+
            |                                |
            ------- merge via HTTP ---------
                         |
                         v
                   All tools presented
                   to the model

Key insight: "MCP tools look identical to local tools from the model's perspective."

DeepWiki MCP: https://mcp.deepwiki.com/mcp  (free, no auth, public repos only)
Install in Claude Code: claude mcp add -s user -t http deepwiki https://mcp.deepwiki.com/mcp
"""

import json
import os
import subprocess
import time
from pathlib import Path
from urllib import request, error as urllib_error

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

# -- DeepWiki MCP Client --
# Real MCP over HTTP (Streamable HTTP transport)
# The DeepWiki server at mcp.deepwiki.com exposes 3 tools:
#   ask_question(repoName, question) - AI-powered answer from repo docs
#   read_wiki_structure(repoName)    - Table of contents for a repo's wiki
#   read_wiki_contents(repoName)     - Full wiki content for a repo

DEEPWIKI_URL = "https://mcp.deepwiki.com/mcp"


def json_rpc(url: str, method: str, params: dict, timeout: int = 120) -> dict:
    """Send a JSON-RPC 2.0 request to an MCP server over HTTP."""
    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": method,
        "params": params,
    }
    data = repr(payload).replace("'", '"').encode()
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib_error.URLError as e:
        return {"error": {"code": -1, "message": str(e)}}
    except Exception as e:
        return {"error": {"code": -1, "message": str(e)}}


def deepwiki_discover_tools() -> list:
    """Discover tools from DeepWiki MCP server via tools/list endpoint.

    In practice, MCP clients call tools/list to get the tool catalog.
    Here we define the 3 known tools inline since DeepWiki's schema is stable.
    """
    return [
        {
            "name": "ask_question",
            "description": "Ask any question about a GitHub repository. Returns AI-powered answer from the repo's DeepWiki docs.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "repoName": {
                        "type": "string",
                        "description": "GitHub repo in format 'owner/repo', e.g. 'ansible/ansible'",
                    },
                    "question": {
                        "type": "string",
                        "description": "Your question about the repository",
                    },
                },
                "required": ["repoName", "question"],
            },
            "mcp_server": "deepwiki",
        },
        {
            "name": "read_wiki_structure",
            "description": "Get the documentation structure (table of contents) for a GitHub repository.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "repoName": {
                        "type": "string",
                        "description": "GitHub repo in format 'owner/repo'",
                    },
                },
                "required": ["repoName"],
            },
            "mcp_server": "deepwiki",
        },
        {
            "name": "read_wiki_contents",
            "description": "Get full wiki documentation content for a GitHub repository.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "repoName": {
                        "type": "string",
                        "description": "GitHub repo in format 'owner/repo'",
                    },
                },
                "required": ["repoName"],
            },
            "mcp_server": "deepwiki",
        },
    ]


def deepwiki_call_tool(name: str, args: dict) -> str:
    """Execute a tool on the DeepWiki MCP server.

    Real MCP uses SSE stream for responses. For simplicity, this teaching
    code uses HTTP POST and waits for the result. DeepWiki's ask_question
    takes 1-3 minutes to generate answers.
    """
    repo = args.get("repoName", args.get("repo", ""))
    question = args.get("question", "")

    if not repo:
        return "Error: repoName required (format: 'owner/repo')"

    # --- Real implementation using json-rpc ---
    # payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
    #            "params": {"name": name, "arguments": args}}
    # result = json_rpc(DEEPWIKI_URL, "tools/call", {"name": name, "arguments": args}, 180)
    # if "error" in result:
    #     return f"DeepWiki error: {result['error']}"
    # content = result.get("result", {}).get("content", [])
    # return content[0].get("text", "(no content)") if content else "(empty response)"

    # --- Simulated responses for teaching (no network dependency) ---
    # In production, uncomment the real implementation above.
    if name == "ask_question":
        return (
            f"[DeepWiki] ask_question('{repo}', '{question}')\n"
            f"Simulated answer: The {repo} repository uses a modular architecture.\n"
            f"For real results, connect to {DEEPWIKI_URL} (takes 1-3 min)."
        )
    elif name == "read_wiki_structure":
        return (
            f"[DeepWiki] read_wiki_structure('{repo}')\n"
            f"Simulated structure:\n"
            f"  1. Overview\n"
            f"  2. Getting Started\n"
            f"  3. Architecture\n"
            f"  4. API Reference\n"
            f"For real results, connect to {DEEPWIKI_URL}."
        )
    elif name == "read_wiki_contents":
        return (
            f"[DeepWiki] read_wiki_contents('{repo}')\n"
            f"Simulated content: Full wiki documentation for {repo}\n"
            f"For real results, connect to {DEEPWIKI_URL}."
        )
    return f"Error: Unknown DeepWiki tool '{name}'"


# -- MCP Client: discovers tools and routes calls --
class MccClient:
    """Connects to MCP servers and integrates their tools into the agent."""

    def __init__(self):
        self.servers = {}

    def connect(self, name: str, tools: list):
        """Register tools from an MCP server."""
        print(f"Connecting to MCP server: {name}")
        self.servers[name] = tools
        all_tools = []
        for server in self.servers.values():
            all_tools.extend(server)
        print(f"  Discovered {len(all_tools)} tools: {[t['name'] for t in all_tools]}")

    def get_tools(self) -> list:
        """Return all MCP tools for merging with local tools."""
        tools = []
        for server in self.servers.values():
            tools.extend(server)
        return tools

    def route_tool(self, name: str, args: dict) -> str:
        """Find which server owns this tool and call it."""
        # DeepWiki tools
        for tool in self.servers.get("deepwiki", []):
            if tool["name"] == name:
                return deepwiki_call_tool(name, args)
        return f"Error: Tool '{name}' not found in any MCP server"


# -- Local tool implementations --
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


# -- Setup MCP connection with DeepWiki --
mcp_client = MccClient()
mcp_client.connect("deepwiki", deepwiki_discover_tools())

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
MCP tools (ask_question, read_wiki_structure, read_wiki_contents) connect to DeepWiki
at {DEEPWIKI_URL} - a service that generates documentation for any public GitHub repo.
Use ask_question to learn about any project's architecture and design decisions."""


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
                # Route: local tools -> local handlers, MCP tools -> DeepWiki
                if block.name in LOCAL_HANDLERS:
                    handler = LOCAL_HANDLERS[block.name]
                    output = handler(**block.input)
                    source = "local"
                elif block.name in MCP_NAMES:
                    output = mcp_client.route_tool(block.name, block.input)
                    source = "deepwiki"
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
            query = input("\033[36ms14 >> \033[0m")
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
