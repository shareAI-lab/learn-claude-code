# Core Data Structures (核心数据结构总表)

> 学习 agent，最容易迷路的地方不是功能太多，而是不知道“状态到底放在哪”。这份文档把主线章节和桥接章节里反复出现的关键数据结构集中列出来，方便你把整套系统看成一张图。

## 推荐联读

建议把这份总表当成“状态地图”来用：

- 先不懂词，就回 [`glossary.md`](./glossary.md)。
- 先不懂边界，就回 [`entity-map.md`](./entity-map.md)。
- 如果卡在 `TaskRecord` 和 `RuntimeTaskState`，继续看 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)。
- 如果卡在 MCP 为什么还有 resource / prompt / elicitation，继续看 [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)。

## 先记住两个总原则

### 原则 1：区分“内容状态”和“流程状态”

- `messages`、`tool_result`、memory 正文，属于内容状态。
- `turn_count`、`transition`、`pending_classifier_check`，属于流程状态。

很多初学者会把这两类状态混在一起。  
一混，后面就很难看懂为什么一个结构完整的系统会需要控制平面。

### 原则 2：区分“持久状态”和“运行时状态”

- task、memory、schedule 这类状态，通常会落盘，跨会话存在。
- runtime task、当前 permission decision、当前 MCP connection 这类状态，通常只在系统运行时活着。

## 1. 查询与对话控制状态

### Message

作用：保存当前对话和工具往返历史。

最小形状：

```python
message = {
    "role": "user" | "assistant",
    "content": "...",
}
```

支持工具调用后，`content` 常常不再只是字符串，而会变成块列表，其中可能包含：

- text block
- `tool_use`
- `tool_result`

相关章节：

- `s01`
- `s02`
- `s06`
- `s10`

### NormalizedMessage

作用：把不同来源的消息整理成统一、稳定、可送给模型 API 的消息格式。

最小形状：

```python
message = {
    "role": "user" | "assistant",
    "content": [
        {"type": "text", "text": "..."},
    ],
}
```

它和普通 `Message` 的区别是：

- `Message` 偏“系统内部记录”
- `NormalizedMessage` 偏“准备发给模型之前的统一输入”

相关章节：

- `s10`
- [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md)

### CompactSummary

作用：上下文太长时，用摘要替代旧消息原文。

最小形状：

```python
summary = {
    "task_overview": "...",
    "current_state": "...",
    "key_decisions": ["..."],
    "next_steps": ["..."],
}
```

相关章节：

- `s06`
- `s11`

### SystemPromptBlock

作用：把 system prompt 从一整段大字符串，拆成若干可管理片段。

最小形状：

```python
block = {
    "text": "...",
    "cache_scope": None,
}
```

你可以把它理解成：

- `text`：这一段提示词正文
- `cache_scope`：这一段是否可以复用缓存

相关章节：

- `s10`
- [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md)

### PromptParts

作用：在真正拼成 system prompt 之前，先把各部分拆开管理。

最小形状：

```python
parts = {
    "core": "...",
    "tools": "...",
    "skills": "...",
    "memory": "...",
    "claude_md": "...",
    "dynamic": "...",
}
```

相关章节：

- `s10`

### QueryParams

作用：进入查询主循环时，外部一次性传进来的输入集合。

最小形状：

```python
params = {
    "messages": [...],
    "system_prompt": "...",
    "user_context": {...},
    "system_context": {...},
    "tool_use_context": {...},
    "fallback_model": None,
    "max_output_tokens_override": None,
    "max_turns": None,
}
```

它的重要点在于：

- 这是“本次 query 的入口输入”
- 它和循环内部不断变化的状态，不是同一层

相关章节：

- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)

### QueryState

作用：保存一条 query 在多轮循环之间不断变化的流程状态。

最小形状：

```python
state = {
    "messages": [...],
    "tool_use_context": {...},
    "turn_count": 1,
    "max_output_tokens_recovery_count": 0,
    "has_attempted_reactive_compact": False,
    "max_output_tokens_override": None,
    "pending_tool_use_summary": None,
    "stop_hook_active": False,
    "transition": None,
}
```

这类字段的共同特点是：

- 它们不是对话内容
- 它们是“这一轮该怎么继续”的控制状态

相关章节：

- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)
- `s11`

### TransitionReason

作用：记录“上一轮为什么继续了，而不是结束”。

最小形状：

```python
transition = {
    "reason": "next_turn",
}
```

在更完整的 query 状态里，这个 `reason` 常见会有这些类型：

- `next_turn`
- `reactive_compact_retry`
- `token_budget_continuation`
- `max_output_tokens_recovery`
- `stop_hook_continuation`

它的价值不是炫技，而是让：

- 日志更清楚
- 测试更清楚
- 恢复链路更清楚

相关章节：

- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)
- `s11`

## 2. 工具、权限与 hook 执行状态

### ToolSpec

作用：告诉模型“有哪些工具、每个工具要什么输入”。

最小形状：

```python
tool = {
    "name": "read_file",
    "description": "Read file contents.",
    "input_schema": {...},
}
```

相关章节：

- `s02`
- `s19`

### ToolDispatchMap

作用：把工具名映射到真实执行函数。

最小形状：

```python
handlers = {
    "read_file": run_read,
    "write_file": run_write,
    "bash": run_bash,
}
```

相关章节：

- `s02`

### ToolUseContext

作用：把工具运行时需要的共享环境打成一个总线。

最小形状：

```python
tool_use_context = {
    "tools": handlers,
    "permission_context": {...},
    "mcp_clients": [],
    "messages": [...],
    "app_state": {...},
    "cwd": "...",
    "read_file_state": {...},
    "notifications": [],
}
```

这层很关键。  
因为在更完整的工具执行环境里，工具拿到的不只是 `tool_input`，还包括：

- 当前权限环境
- 当前消息
- 当前 app state
- 当前 MCP client
- 当前文件读取缓存

相关章节：

- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)
- `s07`
- `s19`

### PermissionRule

作用：描述某类工具调用命中后该怎么处理。

最小形状：

```python
rule = {
    "tool_name": "bash",
    "rule_content": "rm -rf *",
    "behavior": "deny",
}
```

相关章节：

- `s07`

### PermissionRuleSource

作用：标记一条权限规则是从哪里来的。

最小形状：

```python
source = (
    "userSettings"
    | "projectSettings"
    | "localSettings"
    | "flagSettings"
    | "policySettings"
    | "cliArg"
    | "command"
    | "session"
)
```

这个结构的意义是：

- 你不只知道“有什么规则”
- 还知道“这条规则是谁加进来的”

相关章节：

- `s07`

### PermissionDecision

作用：表示一次工具调用当前该允许、拒绝还是提问。

最小形状：

```python
decision = {
    "behavior": "allow" | "deny" | "ask",
    "reason": "matched deny rule",
}
```

在更完整的权限流里，`ask` 结果还可能带：

- 修改后的输入
- 建议写回哪些规则更新
- 一个后台自动分类检查

相关章节：

- `s07`

### PermissionUpdate

作用：描述“这次权限确认之后，要把什么改回配置里”。

最小形状：

```python
update = {
    "type": "addRules" | "removeRules" | "setMode" | "addDirectories",
    "destination": "userSettings" | "projectSettings" | "localSettings" | "session",
    "rules": [],
}
```

它解决的是一个很容易被漏掉的问题：

用户这次点了“允许”，到底只是这一次放行，还是要写回会话、项目，甚至用户级配置。

相关章节：

- `s07`

### HookContext

作用：把某个 hook 事件发生时的上下文打包给外部脚本。

最小形状：

```python
context = {
    "event": "PreToolUse",
    "tool_name": "bash",
    "tool_input": {...},
    "tool_result": "...",
}
```

相关章节：

- `s08`

### RecoveryState

作用：记录恢复流程已经尝试到哪里。

最小形状：

```python
state = {
    "continuation_attempts": 0,
    "compact_attempts": 0,
    "transport_attempts": 0,
}
```

相关章节：

- `s11`

## 3. 持久化工作状态

### TodoItem

作用：当前会话里的轻量计划项。

最小形状：

```python
todo = {
    "content": "Read parser.py",
    "status": "pending" | "completed",
}
```

相关章节：

- `s03`

### MemoryEntry

作用：保存跨会话仍然有价值的信息。

最小形状：

```python
memory = {
    "name": "prefer_tabs",
    "description": "User prefers tabs for indentation",
    "type": "user" | "feedback" | "project" | "reference",
    "scope": "private" | "team",
    "body": "...",
}
```

这里最重要的不是字段多，而是边界清楚：

- 只存不容易从当前项目状态重新推出来的东西
- 记忆可能会过时，要验证

相关章节：

- `s09`

### TaskRecord

作用：磁盘上的工作图任务节点。

最小形状：

```python
task = {
    "id": 12,
    "subject": "Implement auth module",
    "description": "",
    "status": "pending",
    "blockedBy": [],
    "blocks": [],
    "owner": "",
    "worktree": "",
}
```

重点字段：

- `blockedBy`：谁挡着我
- `blocks`：我挡着谁
- `owner`：谁认领了
- `worktree`：在哪个隔离目录里做

相关章节：

- `s12`
- `s17`
- `s18`
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

### ScheduleRecord

作用：记录未来要触发的调度任务。

最小形状：

```python
schedule = {
    "id": "job_001",
    "cron": "0 9 * * 1",
    "prompt": "Generate weekly report",
    "recurring": True,
    "durable": True,
    "created_at": 1710000000.0,
    "last_fired_at": None,
}
```

相关章节：

- `s14`

## 4. 运行时执行状态

### RuntimeTaskState

作用：表示系统里一个“正在运行的执行单元”。

最小形状：

```python
runtime_task = {
    "id": "b8k2m1qz",
    "type": "local_bash",
    "status": "running",
    "description": "Run pytest",
    "start_time": 1710000000.0,
    "end_time": None,
    "output_file": ".task_outputs/b8k2m1qz.txt",
    "notified": False,
}
```

这和 `TaskRecord` 不是一回事：

- `TaskRecord` 管工作目标
- `RuntimeTaskState` 管当前执行槽位

相关章节：

- `s13`
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

### TeamMember

作用：记录一个持久队友是谁、在做什么。

最小形状：

```python
member = {
    "name": "alice",
    "role": "coder",
    "status": "idle",
}
```

相关章节：

- `s15`
- `s17`

### MessageEnvelope

作用：队友之间传递结构化消息。

最小形状：

```python
message = {
    "type": "message" | "shutdown_request" | "plan_approval",
    "from": "lead",
    "to": "alice",
    "request_id": "req_001",
    "content": "...",
    "payload": {},
    "timestamp": 1710000000.0,
}
```

相关章节：

- `s15`
- `s16`

### RequestRecord

作用：追踪一个协议请求当前走到哪里。

最小形状：

```python
request = {
    "request_id": "req_001",
    "kind": "shutdown" | "plan_review",
    "status": "pending" | "approved" | "rejected" | "expired",
    "from": "lead",
    "to": "alice",
}
```

相关章节：

- `s16`

### WorktreeRecord

作用：记录一个任务绑定的隔离工作目录。

最小形状：

```python
worktree = {
    "name": "auth-refactor",
    "path": ".worktrees/auth-refactor",
    "branch": "wt/auth-refactor",
    "task_id": 12,
    "status": "active",
}
```

相关章节：

- `s18`

### WorktreeEvent

作用：记录 worktree 生命周期事件，便于恢复和排查。

最小形状：

```python
event = {
    "event": "worktree.create.after",
    "task_id": 12,
    "worktree": "auth-refactor",
    "ts": 1710000000.0,
}
```

相关章节：

- `s18`

## 5. 外部平台与 MCP 状态

### ScopedMcpServerConfig

作用：描述一个 MCP server 应该如何连接，以及它的配置来自哪个作用域。

最小形状：

```python
config = {
    "name": "postgres",
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "..."],
    "scope": "project",
}
```

这个 `scope` 很重要，因为 server 配置可能来自：

- 本地
- 用户
- 项目
- 动态注入
- 插件或托管来源

相关章节：

- `s19`
- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

### MCPServerConnectionState

作用：表示一个 MCP server 当前连到了哪一步。

最小形状：

```python
server_state = {
    "name": "postgres",
    "type": "connected",   # pending / failed / needs-auth / disabled
    "config": {...},
}
```

这层特别重要，因为“有没有接上”不是布尔值，而是多种状态：

- `connected`
- `pending`
- `failed`
- `needs-auth`
- `disabled`

相关章节：

- `s19`
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

### MCPToolSpec

作用：把外部 MCP 工具转换成 agent 内部统一工具定义。

最小形状：

```python
mcp_tool = {
    "name": "mcp__postgres__query",
    "description": "Run a SQL query",
    "input_schema": {...},
}
```

相关章节：

- `s19`

### ElicitationRequest

作用：表示 MCP server 反过来向用户请求额外输入。

最小形状：

```python
request = {
    "server_name": "some-server",
    "message": "Please provide additional input",
    "requested_schema": {...},
}
```

它提醒你一件事：

- MCP 不只是“模型主动调工具”
- 外部 server 也可能反过来请求补充输入

相关章节：

- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

## 最后用一句话把它们串起来

如果你只想记一条总线索，可以记这个：

```text
messages / prompt / query state
  管本轮输入和继续理由

tools / permissions / hooks
  管动作怎么安全执行

memory / task / schedule
  管跨轮、跨会话的持久工作

runtime task / team / worktree
  管当前执行车道

mcp
  管系统怎样向外接能力
```

这份总表最好配合 [`s00-architecture-overview.md`](./s00-architecture-overview.md) 和 [`entity-map.md`](./entity-map.md) 一起看。

## 教学边界

这份总表只负责做两件事：

- 帮你确认一个状态到底属于哪一层
- 帮你确认这个状态大概长什么样

它不负责穷举真实系统里的每一个字段、每一条兼容分支、每一种产品化补丁。

如果你已经知道某个状态归谁管、什么时候创建、什么时候销毁，再回到对应章节看执行路径，理解会顺很多。
