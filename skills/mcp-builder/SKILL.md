---
name: mcp-builder
description: 构建 MCP（Model Context Protocol）服务器，为 Claude 提供新能力。适用于创建 MCP server、添加工具、对接外部服务。
---

# MCP Server 构建技能

你现在具备 MCP（Model Context Protocol）服务端构建能力。MCP 让 Claude 通过统一协议连接外部系统。

## MCP 是什么？

MCP Server 可暴露：
- **Tools**：Claude 可调用的函数（类似 API 能力）
- **Resources**：Claude 可读取的数据（文件、数据库记录等）
- **Prompts**：预置提示词模板

## 快速开始：Python MCP Server

### 1) 项目初始化

```bash
mkdir my-mcp-server && cd my-mcp-server
python3 -m venv venv && source venv/bin/activate
pip install mcp
```

### 2) 基础模板

```python
#!/usr/bin/env python3
"""my_server.py - A simple MCP server"""

from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("my-server")

@server.tool()
async def hello(name: str) -> str:
    return f"Hello, {name}!"

@server.tool()
async def add_numbers(a: int, b: int) -> str:
    return str(a + b)

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 3) 在 Claude 中注册

写入 `~/.claude/mcp.json`：

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python3",
      "args": ["/path/to/my_server.py"]
    }
  }
}
```

## TypeScript MCP Server

### 1) 初始化

```bash
mkdir my-mcp-server && cd my-mcp-server
npm init -y
npm install @modelcontextprotocol/sdk
```

### 2) 模板

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server({ name: "my-server", version: "1.0.0" });

server.setRequestHandler("tools/list", async () => ({
  tools: [{
    name: "hello",
    description: "Say hello to someone",
    inputSchema: {
      type: "object",
      properties: { name: { type: "string", description: "Name to greet" } },
      required: ["name"],
    },
  }],
}));

server.setRequestHandler("tools/call", async (request) => {
  if (request.params.name === "hello") {
    const name = request.params.arguments.name;
    return { content: [{ type: "text", text: `Hello, ${name}!` }] };
  }
  throw new Error("Unknown tool");
});

const transport = new StdioServerTransport();
server.connect(transport);
```

## 进阶模式

### 外部 API 集成

```python
import httpx
from mcp.server import Server

server = Server("weather-server")

@server.tool()
async def get_weather(city: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.weatherapi.com/v1/current.json",
            params={"key": "YOUR_API_KEY", "q": city}
        )
        data = resp.json()
        return f"{city}: {data['current']['temp_c']}C, {data['current']['condition']['text']}"
```

### 数据库访问（只读）

```python
import sqlite3
from mcp.server import Server

server = Server("db-server")

@server.tool()
async def query_db(sql: str) -> str:
    if not sql.strip().upper().startswith("SELECT"):
        return "Error: Only SELECT queries allowed"

    conn = sqlite3.connect("data.db")
    rows = conn.execute(sql).fetchall()
    conn.close()
    return str(rows)
```

### Resources（只读数据）

```python
@server.resource("config://settings")
async def get_settings() -> str:
    return open("settings.json").read()

@server.resource("file://{path}")
async def read_file(path: str) -> str:
    return open(path).read()
```

## 测试

```bash
npx @anthropics/mcp-inspector python3 my_server.py
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 my_server.py
```

## 最佳实践

1. **工具描述清晰**：Claude 依赖描述判断何时调用
2. **输入校验**：所有外部输入都要验证与清洗
3. **错误可诊断**：返回可读的错误信息
4. **默认异步**：I/O 场景优先 async/await
5. **安全优先**：敏感操作要有权限控制
6. **幂等性**：尽量保证工具可安全重试
