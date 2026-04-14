# s19: MCP & Plugin System (MCP 与插件系统)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > [ s19 ]`

> *工具不必都写死在主程序里。外部进程也可以把能力接进你的 agent。*

## 这一章到底在讲什么

前面所有章节里，工具基本都写在你自己的 Python 代码里。

这当然是最适合教学的起点。

但真实系统走到一定阶段以后，会很自然地遇到这个需求：

> “能不能让外部程序也把工具接进来，而不用每次都改主程序？”

这就是 MCP 要解决的问题。

## 先用最简单的话解释 MCP

你可以先把 MCP 理解成：

**一套让 agent 和外部工具程序对话的统一协议。**

在教学版里，不必一开始就背很多协议细节。  
你只要先抓住这条主线：

1. 启动一个外部工具服务进程
2. 问它“你有哪些工具”
3. 当模型要用它的工具时，把请求转发给它
4. 再把结果带回 agent 主循环

这已经够理解 80% 的核心机制了。

## 为什么这一章放在最后

因为 MCP 不是主循环的起点，而是主循环稳定之后的扩展层。

如果你还没真正理解：

- agent loop
- tool call
- permission
- task
- worktree

那 MCP 只会看起来像又一套复杂接口。

但当你已经有了前面的心智，再看 MCP，你会发现它本质上只是：

**把“工具来源”从“本地硬编码”升级成“外部可插拔”。**

## 建议联读

- 如果你只把 MCP 理解成“远程 tools”，先看 [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)，把 tools、resources、prompts、plugin 中介层一起放回平台边界里。
- 如果你想确认外部能力为什么仍然要回到同一条执行面，回看 [`s02b-tool-execution-runtime.md`](./s02b-tool-execution-runtime.md)。
- 如果你开始把“query 控制平面”和“外部能力路由”完全分开理解，建议配合看 [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)。

## 最小心智模型

```text
LLM
  |
  | asks to call a tool
  v
Agent tool router
  |
  +-- native tool  -> 本地 Python handler
  |
  +-- MCP tool     -> 外部 MCP server
                        |
                        v
                    return result
```

## 最小系统里最重要的三件事

### 1. 有一个 MCP client

它负责：

- 启动外部进程
- 发送请求
- 接收响应

### 2. 有一个工具名前缀规则

这是为了避免命名冲突。

最常见的做法是：

```text
mcp__{server}__{tool}
```

比如：

```text
mcp__postgres__query
mcp__browser__open_tab
```

这样一眼就知道：

- 这是 MCP 工具
- 它来自哪个 server
- 它原始工具名是什么

### 3. 有一个统一路由器

路由器只做一件事：

- 如果是本地工具，就交给本地 handler
- 如果是 MCP 工具，就交给 MCP client

## Plugin 又是什么

如果 MCP 解决的是“外部工具怎么通信”，  
那 plugin 解决的是“这些外部工具配置怎么被发现”。

最小 plugin 可以非常简单：

```text
.claude-plugin/
  plugin.json
```

里面写：

- 插件名
- 版本
- 它提供哪些 MCP server
- 每个 server 的启动命令是什么

## 最小配置长什么样

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

这个配置并不复杂。

它本质上只是在告诉主程序：

> “如果你想接这个 server，就用这条命令把它拉起来。”

## 最小实现步骤

### 第一步：写一个 `MCPClient`

它至少要有三个能力：

- `connect()`
- `list_tools()`
- `call_tool()`

### 第二步：把外部工具标准化成 agent 能看懂的工具定义

也就是说，把 MCP server 暴露的工具，转成 agent 工具池里的统一格式。

### 第三步：加前缀

这样主程序就能区分：

- 本地工具
- 外部工具

### 第四步：写一个 router

```python
if tool_name.startswith("mcp__"):
    return mcp_router.call(tool_name, arguments)
else:
    return native_handler(arguments)
```

### 第五步：仍然走同一条权限管道

这是非常关键的一点：

**MCP 工具虽然来自外部，但不能绕开 permission。**

不然你等于在系统边上开了个安全后门。

如果你想把这一层再收得更稳，最好再把结果也标准化回同一条总线：

```python
{
    "source": "mcp",
    "server": "figma",
    "tool": "inspect",
    "status": "ok",
    "preview": "...",
}
```

这表示：

- 路由前要过共享权限闸门
- 路由后不论本地还是远程，结果都要转成主循环看得懂的统一格式

## 如何接到整个系统里

如果你读到这里还觉得 MCP 像“外挂”，通常是因为没有把它放回整条主回路里。

更完整的接法应该看成：

```text
启动时
  ->
PluginLoader 找到 manifest
  ->
得到 server 配置
  ->
MCP client 连接 server
  ->
list_tools 并标准化名字
  ->
和 native tools 一起合并进同一个工具池

运行时
  ->
LLM 产出 tool_use
  ->
统一权限闸门
  ->
native route 或 mcp route
  ->
结果标准化
  ->
tool_result 回到同一个主循环
```

这段流程里最关键的不是“外部”两个字，而是：

**进入方式不同，但进入后必须回到同一条控制面和执行面。**

## Plugin、MCP Server、MCP Tool 不要混成一层

这是初学者最容易在本章里打结的地方。

可以直接按下面三层记：

| 层级 | 它是什么 | 它负责什么 |
|---|---|---|
| plugin manifest | 一份配置声明 | 告诉系统要发现和启动哪些 server |
| MCP server | 一个外部进程 / 连接对象 | 对外暴露一组能力 |
| MCP tool | server 暴露的一项具体调用能力 | 真正被模型点名调用 |

换成一句最短的话说：

- plugin 负责“发现”
- server 负责“连接”
- tool 负责“调用”

只要这三层还分得清，MCP 这章的主体心智就不会乱。

## 这一章最关键的数据结构

### 1. server 配置

```python
{
    "command": "npx",
    "args": ["-y", "..."],
    "env": {}
}
```

### 2. 标准化后的工具定义

```python
{
    "name": "mcp__postgres__query",
    "description": "Run a SQL query",
    "input_schema": {...}
}
```

### 3. client 注册表

```python
clients = {
    "postgres": mcp_client_instance
}
```

## 初学者最容易被带偏的地方

### 1. 一上来讲太多协议细节

这章最容易失控。

因为一旦开始讲完整协议生态，很快会出现：

- transports
- auth
- resources
- prompts
- streaming
- connection recovery

这些都存在，但不该挡住主线。

主线只有一句话：

**外部工具也能像本地工具一样接进 agent。**

### 2. 把 MCP 当成一套完全不同的工具系统

不是。

它最终仍然应该汇入你原来的工具体系：

- 一样要注册
- 一样要出现在工具池里
- 一样要过权限
- 一样要返回 `tool_result`

### 3. 忽略命名与路由

如果没有统一前缀和统一路由，系统会很快乱掉。

## 教学边界

这一章正文先停在 `tools-first` 是对的。

因为教学主线最需要先讲清的是：

- 外部能力怎样被发现
- 怎样被统一命名和路由
- 怎样继续经过同一条权限与 `tool_result` 回流

只要这一层已经成立，读者就已经真正理解了：

**MCP / plugin 不是外挂，而是接回同一控制面的外部能力入口。**

transport、认证、resources、prompts、插件生命周期这些更大范围的内容，应该放到平台桥接资料里继续展开。

## 正文先停在 tools-first，平台层再看桥接文档

这一章的正文故意停在“外部工具如何接进 agent”这一层。  
这是教学上的刻意取舍，不是缺失。

如果你准备继续补平台边界，再去看：

- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

那篇会把 MCP 再往上补成一张平台地图，包括：

- server 配置作用域
- transport 类型
- 连接状态：`connected / pending / needs-auth / failed / disabled`
- tools 之外的 `resources / prompts / elicitation`
- auth 该放在哪一层理解

这样安排的好处是：

- 正文不失焦
- 读者又不会误以为 MCP 只有一个 `list_tools + call_tool`

## 这一章和全仓库的关系

如果说前 18 章都在教你把系统内部搭起来，  
那 `s19` 在教你：

**如何把系统向外打开。**

从这里开始，工具不再只来自你手写的 Python 文件，  
还可以来自别的进程、别的系统、别的服务。

这就是为什么它适合作为最后一章。

## 学完这章后，你应该能回答

- MCP 的核心到底是什么？
- 为什么它应该放在整个学习路径的最后？
- 为什么 MCP 工具也必须走同一条权限与路由逻辑？
- plugin 和 MCP 分别解决什么问题？

---

**一句话记住：MCP 的本质，不是协议名词堆砌，而是把外部工具安全、统一地接进你的 agent。**
