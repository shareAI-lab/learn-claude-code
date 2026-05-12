# s02a: Tool Control Plane (工具控制平面)

> 这篇桥接文档用来回答另一个关键问题：
>
> **为什么“工具系统”不只是一个 `tool_name -> handler` 的映射表？**

## 这一篇为什么要存在

`s02` 先教你工具注册和分发，这完全正确。  
因为如果你一开始连工具调用都没做出来，后面的一切都无从谈起。

但当系统长大以后，工具层会逐渐承载越来越多的责任：

- 权限判断
- MCP 接入
- 通知发送
- subagent / teammate 共享状态
- file state cache
- 当前消息和当前会话环境
- 某些工具专属限制

这时候，“工具层”就已经不是一张函数表了。

它更像一条总线：

**模型通过工具名发出动作意图，系统通过工具控制平面决定这条意图在什么环境里执行。**

## 先解释几个名词

### 什么是工具控制平面

这里的“控制平面”可以继续沿用上一份桥接文档的理解：

> 不直接做业务结果，而是负责协调工具如何执行的一层。

它关心的问题不是“这个工具最后返回了什么”，而是：

- 它在哪执行
- 它有没有权限
- 它可不可以访问某些共享状态
- 它是本地工具还是外部工具

### 什么是执行上下文

执行上下文，就是工具运行时能看到的环境。

例如：

- 当前工作目录
- 当前 app state
- 当前消息列表
- 当前权限模式
- 当前可用 MCP client

### 什么是能力来源

不是所有工具都来自同一个地方。

系统里常见的能力来源有：

- 本地原生工具
- MCP 外部工具
- agent 工具
- task / worktree / team 这类平台工具

## 最小心智模型

工具系统可以先画成 4 层：

```text
1. ToolSpec
   模型看见的工具名字、描述、输入 schema

2. Tool Router
   根据工具名把请求送去正确的能力来源

3. ToolUseContext
   工具运行时能访问的共享环境

4. Tool Result Envelope
   把输出包装回主循环
```

最重要的升级点在第三层：

**更完整系统的核心，不是 tool table，而是 ToolUseContext。**

## 关键数据结构

### 1. ToolSpec

这还是最基础的结构：

```python
tool = {
    "name": "read_file",
    "description": "Read file contents.",
    "input_schema": {...},
}
```

### 2. ToolDispatchMap

```python
handlers = {
    "read_file": read_file,
    "write_file": write_file,
    "bash": run_bash,
}
```

这依旧需要，但它不是全部。

### 3. ToolUseContext

教学版可以先做一个简化版本：

```python
tool_use_context = {
    "tools": handlers,
    "permission_context": {...},
    "mcp_clients": {},
    "messages": [...],
    "app_state": {...},
    "notifications": [],
    "cwd": "...",
}
```

这个结构的关键点是：

- 工具不再只拿到“输入参数”
- 工具还能拿到“共享运行环境”

### 4. ToolResultEnvelope

不要把返回值只想成字符串。

更稳妥的形状是：

```python
result = {
    "ok": True,
    "content": "...",
    "is_error": False,
    "attachments": [],
}
```

这样后面你才能平滑承接：

- 普通文本结果
- 结构化结果
- 错误结果
- 附件类结果

## 为什么更完整的系统一定会出现 ToolUseContext

想象两个系统。

### 系统 A：只有 dispatch map

```python
output = handlers[tool_name](**tool_input)
```

这适合最小 demo。

### 系统 B：有 ToolUseContext

```python
output = handlers[tool_name](tool_input, tool_use_context)
```

这个版本才更接近一个真实平台。

因为工具现在不只是“做一个动作”，而是在一个复杂系统里做动作。

例如：

- `bash` 要看权限
- `mcp__postgres__query` 要找对应 client
- `agent` 工具要创建子执行环境
- `task_output` 工具可能要写磁盘并发通知

这些都要求它们共享同一个上下文总线。

## 最小实现

### 第一步：仍然保留 ToolSpec 和 handler

这个主线不要丢。

### 第二步：引入一个统一 context

```python
class ToolUseContext:
    def __init__(self):
        self.handlers = {}
        self.permission_context = {}
        self.mcp_clients = {}
        self.messages = []
        self.app_state = {}
        self.notifications = []
```

### 第三步：让所有 handler 都能看到 context

```python
def run_tool(tool_name: str, tool_input: dict, ctx: ToolUseContext):
    handler = ctx.handlers[tool_name]
    return handler(tool_input, ctx)
```

### 第四步：在 router 层分不同能力来源

```python
def route_tool(tool_name: str, tool_input: dict, ctx: ToolUseContext):
    if tool_name.startswith("mcp__"):
        return run_mcp_tool(tool_name, tool_input, ctx)
    return run_native_tool(tool_name, tool_input, ctx)
```

## 一张应该讲清楚的图

```text
LLM tool call
  |
  v
Tool Router
  |
  +-- native tools ----------> local handlers
  |
  +-- mcp tools -------------> mcp client
  |
  +-- agent/task/team tools --> platform handlers
            |
            v
       ToolUseContext
         - permissions
         - messages
         - app state
         - notifications
         - mcp clients
```

## 它和 `s02`、`s19` 的关系

- `s02` 先教你工具调用为什么成立
- 这篇解释更完整的系统里工具层为什么会长成一个控制平面
- `s19` 再把 MCP 作为外部能力来源接进来

也就是说：

**MCP 不是另一套独立系统，而是 Tool Control Plane 的一个能力来源。**

## 初学者最容易犯的错

### 1. 以为工具上下文只是 `cwd`

不是。

更完整的系统里，工具上下文往往还包含权限、状态、外部连接和通知接口。

### 2. 让每个工具自己去全局变量里找环境

这样工具层会变得非常散。

更清楚的做法，是显式传一个统一 context。

### 3. 把本地工具和 MCP 工具拆成完全不同体系

这会让系统边界越来越乱。

更好的方式是：

- 能力来源不同
- 但都汇入统一 router 和统一 result envelope

### 4. 把 tool result 永远当成纯字符串

这样后面接附件、错误、结构化信息时会很别扭。

## 教学边界

这篇最重要的，不是把工具层做成一个庞大的企业总线，而是先把下面三层边界讲清：

- tool call 不是直接执行，而是先进入统一调度入口
- 工具 handler 不应该各自去偷拿环境，而应该共享一份显式 `ToolUseContext`
- 本地工具、插件工具、MCP 工具可以来源不同，但结果都应该回到统一控制面

类型化上下文、能力注册中心、大结果存储和更细的工具限额，都是你把这条最小控制总线讲稳以后再补的扩展。

## 一句话记住

**最小工具系统靠 dispatch map，更完整的工具系统靠 ToolUseContext 这条控制总线。**
