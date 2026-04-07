# s19: MCP & Plugin

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > [ s19 ]`

## What You'll Learn
- How MCP (Model Context Protocol -- a standard way for the agent to talk to external capability servers) lets your agent gain new tools without changing its core code
- How tool name normalization with a `mcp__{server}__{tool}` prefix keeps external tools from colliding with native ones
- How a unified router dispatches tool calls to local handlers or remote servers through the same path
- How plugin manifests let external capability servers be discovered and launched automatically

Up to this point, every tool your agent uses -- bash, read, write, edit, tasks, worktrees -- lives inside your Python harness. You wrote each one by hand. That works well for a teaching codebase, but a real agent needs to talk to databases, browsers, cloud services, and tools that do not exist yet. Hard-coding every possible capability is not sustainable. This chapter shows how external programs can join your agent through the same tool-routing plane you already built.

## The Problem

Your agent is powerful, but its capabilities are frozen at build time. If you want it to query a Postgres database, you write a new Python handler. If you want it to control a browser, you write another handler. Every new capability means changing the core harness, re-testing the tool router, and redeploying. Meanwhile, other teams are building specialized servers that already know how to talk to these systems. You need a standard protocol so those external servers can expose their tools to your agent, and your agent can call them as naturally as it calls its own native tools -- without rewriting the core loop every time.

## The Solution

MCP gives your agent a standard way to connect to external capability servers over stdio. The agent starts a server process, asks what tools it provides, normalizes their names with a prefix, and routes calls to that server -- all through the same tool pipeline that handles native tools.

```text
LLM
  |
  | asks to call a tool
  v
Agent tool router
  |
  +-- native tool  -> local Python handler
  |
  +-- MCP tool     -> external MCP server
                        |
                        v
                    return result
```

## Read Together

- If you want to understand how MCP fits into the broader capability surface beyond just tools (resources, prompts, plugin discovery), [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md) covers the full platform boundary.
- If you want to confirm that external capabilities still return through the same execution surface as native tools, pair this chapter with [`s02b-tool-execution-runtime.md`](./s02b-tool-execution-runtime.md).
- If query control and external capability routing are drifting apart in your mental model, [`s00a-query-control-plane.md`](./s00a-query-control-plane.md) ties them together.

## How It Works

There are three essential pieces. Once you understand them, MCP stops being mysterious.

**Step 1.** Build an `MCPClient` that manages the connection to one external server. It starts the server process over stdio, sends a handshake, and caches the list of available tools.

```python
class MCPClient:
    def __init__(self, server_name, command, args=None, env=None):
        self.server_name = server_name
        self.command = command
        self.args = args or []
        self.process = None
        self._tools = []

    def connect(self):
        self.process = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        self._send({"method": "initialize", "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "teaching-agent", "version": "1.0"},
        }})
        response = self._recv()
        if response and "result" in response:
            self._send({"method": "notifications/initialized"})
            return True
        return False

    def list_tools(self):
        self._send({"method": "tools/list", "params": {}})
        response = self._recv()
        if response and "result" in response:
            self._tools = response["result"].get("tools", [])
        return self._tools

    def call_tool(self, tool_name, arguments):
        self._send({"method": "tools/call", "params": {
            "name": tool_name, "arguments": arguments,
        }})
        response = self._recv()
        if response and "result" in response:
            content = response["result"].get("content", [])
            return "\n".join(c.get("text", str(c)) for c in content)
        return "MCP Error: no response"
```

**Step 2.** Normalize external tool names with a prefix so they never collide with native tools. The convention is simple: `mcp__{server}__{tool}`.

```text
mcp__postgres__query
mcp__browser__open_tab
```

This prefix serves double duty: it prevents name collisions, and it tells the router exactly which server should handle the call.

```python
def get_agent_tools(self):
    agent_tools = []
    for tool in self._tools:
        prefixed_name = f"mcp__{self.server_name}__{tool['name']}"
        agent_tools.append({
            "name": prefixed_name,
            "description": tool.get("description", ""),
            "input_schema": tool.get("inputSchema", {
                "type": "object", "properties": {}
            }),
        })
    return agent_tools
```

**Step 3.** Build one unified router. The router does not care whether a tool is native or external beyond the dispatch decision. If the name starts with `mcp__`, route to the MCP server; otherwise, call the local handler. This keeps the agent loop untouched -- it just sees a flat list of tools.

```python
if tool_name.startswith("mcp__"):
    return mcp_router.call(tool_name, arguments)
else:
    return native_handler(arguments)
```

**Step 4.** Add plugin discovery. If MCP answers "how does the agent talk to an external capability server," plugins answer "how are those servers discovered and configured?" A minimal plugin is a manifest file that tells the harness which servers to launch:

```json
{
  "name": "my-db-tools",
  "version": "1.0.0",
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"]
    }
  }
}
```

This lives in `.claude-plugin/plugin.json`. The `PluginLoader` scans for these manifests, extracts the server configs, and hands them to the `MCPToolRouter` for connection.

**Step 5.** Enforce the safety boundary. This is the most important rule of the entire chapter: external tools must still pass through the same permission gate as native tools. If MCP tools bypass permission checks, you have created a security backdoor at the edge of your system.

```python
decision = permission_gate.check(block.name, block.input or {})
# Same check for "bash", "read_file", and "mcp__postgres__query"
```

## How It Plugs Into The Full Harness

MCP gets confusing when it is treated like a separate universe. The cleaner model is:

```text
startup
  ->
plugin loader finds manifests
  ->
server configs are extracted
  ->
MCP clients connect and list tools
  ->
external tools are normalized into the same tool pool

runtime
  ->
LLM emits tool_use
  ->
shared permission gate
  ->
native route or MCP route
  ->
result normalization
  ->
tool_result returns to the same loop
```

Different entry point, same control plane and execution plane.

## Plugin vs Server vs Tool

| Layer | What it is | What it is for |
|---|---|---|
| plugin manifest | a config declaration | tells the harness which servers to discover and launch |
| MCP server | an external process / connection | exposes a set of capabilities |
| MCP tool | one callable capability from that server | the concrete thing the model invokes |

Shortest memory aid:

- plugin = discovery
- server = connection
- tool = invocation

## Key Data Structures

### Server config

```python
{
    "command": "npx",
    "args": ["-y", "..."],
    "env": {}
}
```

### Normalized external tool definition

```python
{
    "name": "mcp__postgres__query",
    "description": "Run a SQL query",
    "input_schema": {...}
}
```

### Client registry

```python
clients = {
    "postgres": mcp_client_instance
}
```

## What Changed From s18

| Component          | Before (s18)                      | After (s19)                                      |
|--------------------|-----------------------------------|--------------------------------------------------|
| Tool sources       | All native (local Python)         | Native + external MCP servers                    |
| Tool naming        | Flat names (`bash`, `read_file`)  | Prefixed for externals (`mcp__postgres__query`)  |
| Routing            | Single handler map                | Unified router: native dispatch + MCP dispatch   |
| Capability growth  | Edit harness code for each tool   | Add a plugin manifest or connect a server        |
| Permission scope   | Native tools only                 | Native + external tools through same gate        |

## Try It

```sh
cd learn-claude-code
python agents/s19_mcp_plugin.py
```

1. Watch how external tools are discovered from plugin manifests at startup.
2. Type `/tools` to see native and MCP tools listed side by side in one flat pool.
3. Type `/mcp` to see which MCP servers are connected and how many tools each provides.
4. Ask the agent to use a tool and notice how results return through the same loop as local tools.

## What You've Mastered

At this point, you can:

- Connect to external capability servers using the MCP stdio protocol
- Normalize external tool names with a `mcp__{server}__{tool}` prefix to prevent collisions
- Route tool calls through a unified dispatcher that handles both native and MCP tools
- Discover and launch MCP servers automatically through plugin manifests
- Enforce the same permission checks on external tools as on native ones

## The Full Picture

You have now walked through the complete design backbone of a production coding agent, from s01 to s19.

You started with a bare agent loop that calls an LLM and appends tool results. You added tool use, then a persistent task list, then subagents, skill loading, and context compaction. You built a permission system, a hook system, and a memory system. You constructed the system prompt pipeline, added error recovery, and gave agents a full task board with background execution and cron scheduling. You organized agents into teams with coordination protocols, made them autonomous, gave each task its own isolated worktree, and finally opened the door to external capabilities through MCP.

Each chapter added exactly one idea to the system. None of them required you to throw away what came before. The agent you have now is not a toy -- it is a working model of the same architectural decisions that shape real production agents.

If you want to test your understanding, try rebuilding the complete system from scratch. Start with the agent loop. Add tools. Add tasks. Keep going until you reach MCP. If you can do that without looking back at the chapters, you understand the design. And if you get stuck somewhere in the middle, the chapter that covers that idea will be waiting for you.

## Key Takeaway

> External capabilities should enter the same tool pipeline as native ones -- same naming, same routing, same permissions -- so the agent loop never needs to know the difference.
