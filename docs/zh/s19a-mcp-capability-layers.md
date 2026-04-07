# s19a: MCP Capability Layers (MCP 能力层地图)

> `s19` 的主线仍然应该坚持“先做 tools-first”。  
> 这篇桥接文档负责补上另一层心智：
>
> **MCP 不只是外部工具接入，它是一组能力层。**

## 建议怎么联读

如果你希望 MCP 这块既不学偏，也不学浅，推荐这样看：

- 先看 [`s19-mcp-plugin.md`](./s19-mcp-plugin.md)，先把 tools-first 主线走通。
- 再看 [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)，确认外部能力最后怎样接回统一工具总线。
- 如果状态结构开始混，再对照 [`data-structures.md`](./data-structures.md)。
- 如果概念边界开始混，再回 [`glossary.md`](./glossary.md) 和 [`entity-map.md`](./entity-map.md)。

## 为什么要单独补这一篇

如果你是为了教学，从 0 到 1 手搓一个类似系统，那么 `s19` 主线先只讲外部工具，这是对的。

因为最容易理解的入口就是：

- 连接一个外部 server
- 拿到工具列表
- 调用工具
- 把结果带回 agent

但如果你想把系统做到接近 95%-99% 的还原度，你迟早会遇到这些问题：

- server 是用 stdio、http、sse 还是 ws 连接？
- 为什么有些 server 是 connected，有些是 pending，有些是 needs-auth？
- tools 之外，resources 和 prompts 是什么位置？
- elicitation 为什么会变成一类特殊交互？
- OAuth / XAA 这种认证流程该放在哪一层理解？

这时候如果没有一张“能力层地图”，MCP 就会越学越散。

## 先解释几个名词

### 什么是能力层

能力层，就是把一个复杂系统拆成几层职责清楚的面。

这里的意思是：

> 不要把所有 MCP 细节混成一团，而要知道每一层到底解决什么问题。

### 什么是 transport

`transport` 可以理解成“连接通道”。

比如：

- stdio
- http
- sse
- websocket

### 什么是 elicitation

这个词比较生。

你可以先把它理解成：

> 外部 MCP server 反过来向用户请求额外输入的一种交互。

也就是说，不再只是 agent 主动调工具，而是 server 也能说：

“我还需要你给我一点信息，我才能继续。”

## 最小心智模型

先把 MCP 画成 6 层：

```text
1. Config Layer
   server 配置长什么样

2. Transport Layer
   用什么通道连 server

3. Connection State Layer
   现在是 connected / pending / failed / needs-auth

4. Capability Layer
   tools / resources / prompts / elicitation

5. Auth Layer
   是否需要认证，认证状态如何

6. Router Integration Layer
   如何接回 tool router / permission / notifications
```

最重要的一点是：

**tools 只是其中一层，不是全部。**

## 为什么正文仍然应该坚持 tools-first

这点非常重要。

虽然 MCP 平台本身有多层能力，但正文主线仍然应该这样安排：

### 第一步：先教外部 tools

因为它和前面的主线最自然衔接：

- 本地工具
- 外部工具
- 同一条 router

### 第二步：再告诉读者还有其他能力层

例如：

- resources
- prompts
- elicitation
- auth

### 第三步：再决定是否继续实现

这才符合你的教学目标：

**先做出类似系统，再补平台层高级能力。**

## 关键数据结构

### 1. ScopedMcpServerConfig

最小教学版建议至少让读者看到这个概念：

```python
config = {
    "name": "postgres",
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "..."],
    "scope": "project",
}
```

这里的 `scope` 很重要。

因为 server 配置不一定都来自同一个地方。

### 2. MCP Connection State

```python
server_state = {
    "name": "postgres",
    "status": "connected",   # pending / failed / needs-auth / disabled
    "config": {...},
}
```

### 3. MCPToolSpec

```python
tool = {
    "name": "mcp__postgres__query",
    "description": "...",
    "input_schema": {...},
}
```

### 4. ElicitationRequest

```python
request = {
    "server_name": "some-server",
    "message": "Please provide additional input",
    "requested_schema": {...},
}
```

这一步不是要求你主线立刻实现它，而是要让读者知道：

**MCP 不一定永远只是“模型调工具”。**

## 一张更完整但仍然清楚的图

```text
MCP Config
  |
  v
Transport
  |
  v
Connection State
  |
  +-- connected
  +-- pending
  +-- needs-auth
  +-- failed
  |
  v
Capabilities
  +-- tools
  +-- resources
  +-- prompts
  +-- elicitation
  |
  v
Router / Permission / Notification Integration
```

## Auth 为什么不要在主线里讲太多

这也是教学取舍里很重要的一点。

认证是真实系统里确实存在的能力层。  
但如果正文一开始就掉进 OAuth/XAA 流程，初学者会立刻丢主线。

所以更好的讲法是：

- 先告诉读者：有 auth layer
- 再告诉读者：connected / needs-auth 是不同连接状态
- 只有做平台层进阶时，再详细展开认证流程

这就既没有幻觉，也没有把人带偏。

## 它和 `s19`、`s02a` 的关系

- `s19` 正文继续负责 tools-first 教学
- 这篇负责补清平台层地图
- `s02a` 的 Tool Control Plane 则解释 MCP 最终怎么接回统一工具总线

三者合在一起，读者才会真正知道：

**MCP 是外部能力平台，而 tools 只是它最先进入主线的那个切面。**

## 初学者最容易犯的错

### 1. 把 MCP 只理解成“外部工具目录”

这会让后面遇到 auth / resources / prompts / elicitation 时很困惑。

### 2. 一上来就沉迷 transport 和 OAuth 细节

这样会直接打断主线。

### 3. 让 MCP 工具绕过 permission

这会在系统边上开一个很危险的后门。

### 4. 不区分 server 配置、连接状态、能力暴露

这三层一混，平台层就会越学越乱。

## 教学边界

这篇最重要的，不是把 MCP 所有外设细节都讲完，而是先守住四层边界：

- server 配置
- 连接状态
- capability 暴露
- permission / routing 接入点

只要这四层不混，你就已经能自己手搓一个接近真实系统主脉络的外部能力入口。  
认证状态机、resource/prompt 接入、server 回问和重连策略，都属于后续平台扩展。

## 一句话记住

**`s19` 主线应该先教“外部工具接入”，而平台层还需要额外理解 MCP 的能力层地图。**
