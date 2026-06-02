# s14: MCP Tools (DeepWiki)

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > [ s14 ] s15 > s16 > s17 > s18 > s19`

> *"Tools from outside the agent process"* -- connect to remote tool providers.
>
> **Harness layer**: External tool integration -- tools from outside the agent process, merged with local tools.

## Problem

By s13, the agent has local tools (bash, read, write). But what if you need tools that live on a remote server? Every agent would need to reimplement web scraping, API calls, and authentication.

MCP (Model Context Protocol) standardizes how agents discover and use remote tools. To the model, a remote tool looks identical to a local tool.

## Solution

```
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
```

## How It Works

1. **Discover tools from MCP server.** JSON-RPC call to get the tool catalog.

```python
def deepwiki_discover_tools() -> list:
    return [
        {
            "name": "ask_question",
            "description": "Ask any question about a GitHub repository.",
            "input_schema": { ... },
            "mcp_server": "deepwiki",
        },
        ...
    ]
```

2. **Merge with local tools.** The model sees one unified tool list.

```python
ALL_TOOLS = LOCAL_TOOLS + mcp_client.get_tools()
```

3. **Route calls.** Local tools use local handlers, MCP tools route to remote servers.

```python
if block.name in LOCAL_HANDLERS:
    output = LOCAL_HANDLERS[block.name](**block.input)
elif block.name in MCP_NAMES:
    output = mcp_client.route_tool(block.name, block.input)
```

## Try It

```sh
cd learn-claude-code
python agents/s14_mcp_deepwiki.py
```

Try asking about a real GitHub repository:

1. `Ask DeepWiki: what is the architecture of ansible/ansible?`
2. `Show me the wiki structure for tensorflow/tensorflow`
