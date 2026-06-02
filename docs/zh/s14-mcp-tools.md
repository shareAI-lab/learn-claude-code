# s14: MCP Tools (DeepWiki)

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > [ s14 ] s15 > s16 > s17 > s18 > s19`

> *"来自 Agent 进程外部的工具"* -- 连接远程工具提供者。
>
> **Harness 层**: 外部工具集成 -- 来自外部的工具,与本地工具合并。

## 问题

s13 之后, Agent 有本地工具 (bash, read, write)。但如果需要远程服务器上的工具呢? 每个 Agent 都得重新实现网络爬取、API 调用和认证。

MCP (Model Context Protocol) 标准化了 Agent 发现和远程工具使用的方式。对模型来说,远程工具和本地工具看起来完全一样。

## 解决方案

```
本地工具                    DeepWiki MCP 服务器 (远程)
+------------------+        +---------------------------+
| bash             |        | ask_question(repo, query) |
| read_file        |        | read_wiki_structure(repo) |
| write_file       |        | read_wiki_contents(repo)  |
+------------------+        +---------------------------+
       |                               |
       ------- 通过 HTTP 合并 ---------
                    |
                    v
              所有工具呈现给模型
```

## 工作原理

1. **从 MCP 服务器发现工具。**

```python
def deepwiki_discover_tools() -> list:
    return [
        {
            "name": "ask_question",
            "description": "Ask any question about a GitHub repository.",
            "input_schema": { ... },
            "mcp_server": "deepwiki",
        },
    ]
```

2. **与本地工具合并。** 模型看到一个统一的工具列表。

```python
ALL_TOOLS = LOCAL_TOOLS + mcp_client.get_tools()
```

3. **路由调用。** 本地工具用本地处理器, MCP 工具路由到远程服务器。

```python
if block.name in LOCAL_HANDLERS:
    output = LOCAL_HANDLERS[block.name](**block.input)
elif block.name in MCP_NAMES:
    output = mcp_client.route_tool(block.name, block.input)
```

## 试一试

```sh
cd learn-claude-code
python agents/s14_mcp_deepwiki.py
```

试试:

1. `Ask DeepWiki: what is the architecture of ansible/ansible?`
2. `Show me the wiki structure for tensorflow/tensorflow`
