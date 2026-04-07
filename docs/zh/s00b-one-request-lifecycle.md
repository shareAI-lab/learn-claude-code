# s00b: One Request Lifecycle (一次请求的完整生命周期)

> 这是一份桥接文档。  
> 它不替代主线章节，而是把整套系统串成一条真正连续的执行链。
>
> 它要回答的问题是：
>
> **用户的一句话，进入系统以后，到底是怎样一路流动、分发、执行、再回到主循环里的？**

## 为什么必须补这一篇

很多读者在按顺序看教程时，会逐章理解：

- `s01` 讲循环
- `s02` 讲工具
- `s03` 讲规划
- `s07` 讲权限
- `s09` 讲 memory
- `s12-s19` 讲任务、多 agent、MCP

每章单看都能懂。

但一旦开始自己实现，就会很容易卡住：

- 这些模块到底谁先谁后？
- 一条请求进来时，先走 prompt，还是先走 memory？
- 工具执行前，权限和 hook 在哪一层？
- task、runtime task、teammate、worktree、MCP 到底是在一次请求里的哪个阶段介入？

所以你需要一张“纵向流程图”。

## 先给一条最重要的总图

```text
用户请求
  |
  v
Query State 初始化
  |
  v
组装 system prompt / messages / reminders
  |
  v
调用模型
  |
  +-- 普通回答 -------------------------------> 结束本次请求
  |
  +-- tool_use
        |
        v
    Tool Router
        |
        +-- 权限判断
        +-- Hook 拦截/注入
        +-- 本地工具 / MCP / agent / task / team
        |
        v
    执行结果
        |
        +-- 可能写入 task / runtime task / memory / worktree 状态
        |
        v
    tool_result 写回 messages
        |
        v
    Query State 更新
        |
        v
    下一轮继续
```

你可以把整条链先理解成三层：

1. `Query Loop`
2. `Tool Control Plane`
3. `Platform State`

## 第 1 段：用户请求进入查询控制平面

当用户说：

```text
修复 tests/test_auth.py 的失败，并告诉我原因
```

系统最先做的，不是立刻跑工具，而是先为这次请求建立一份查询状态。

最小可以理解成：

```python
query_state = {
    "messages": [{"role": "user", "content": user_text}],
    "turn_count": 1,
    "transition": None,
    "tool_use_context": {...},
}
```

这里的重点是：

**这次请求不是“单次 API 调用”，而是一段可能包含很多轮的查询过程。**

如果你对这一层还不够熟，先回看：

- [`s01-the-agent-loop.md`](./s01-the-agent-loop.md)
- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)

## 第 2 段：组装本轮真正送给模型的输入

主循环不会直接把原始 `messages` 裸发出去。

在更完整的系统里，它通常会先组装：

- system prompt blocks
- 规范化后的 messages
- memory section
- 当前轮 reminder
- 工具清单

也就是说，真正发给模型的通常是：

```text
system prompt
+ normalized messages
+ tools
+ optional reminders / attachments
```

这里涉及的章节是：

- `s09` memory
- `s10` system prompt
- `s10a` message & prompt pipeline

这一段的核心心智是：

**system prompt 不是全部输入，它只是输入管道中的一段。**

## 第 3 段：模型产出两类东西

模型这一轮的输出，最关键地分成两种：

### 第一种：普通回复

如果模型直接给出结论或说明，本次请求可能就结束了。

### 第二种：动作意图

也就是工具调用。

例如：

```text
read_file("tests/test_auth.py")
bash("pytest tests/test_auth.py -q")
todo([...])
load_skill("code-review")
task_create(...)
mcp__postgres__query(...)
```

这时候系统真正收到的，不只是“文本”，而是：

> 模型想让真实世界发生某些动作。

## 第 4 段：工具路由层接管动作意图

一旦出现 `tool_use`，系统就进入工具控制平面。

这一层至少要回答：

1. 这是什么工具？
2. 它应该路由到哪类能力来源？
3. 执行前要不要先过权限？
4. hook 有没有要拦截或补充？
5. 它执行时能访问哪些共享状态？

最小图可以这样看：

```text
tool_use
  |
  v
Tool Router
  |
  +-- native tool handler
  +-- MCP client
  +-- agent/team/task handler
```

如果你对这一层不够清楚，回看：

- [`s02-tool-use.md`](./s02-tool-use.md)
- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)

## 第 5 段：权限系统决定“能不能执行”

不是所有动作意图都应该直接变成真实执行。

例如：

- 写文件
- 跑 bash
- 改工作目录
- 调外部服务

这时会先进入权限判断：

```text
deny rules
  -> mode
  -> allow rules
  -> ask user
```

权限系统处理的是：

> 这次动作是否允许发生。

相关章节：

- [`s07-permission-system.md`](./s07-permission-system.md)

## 第 6 段：Hook 可以在边上做扩展

通过权限检查以后，系统还可能在工具执行前后跑 hook。

你可以把 hook 理解成：

> 不改主循环主干，也能插入自定义行为的扩展点。

例如：

- 执行前记录日志
- 执行后做额外检查
- 根据结果注入额外提醒

相关章节：

- [`s08-hook-system.md`](./s08-hook-system.md)

## 第 7 段：真正执行动作，并影响不同层的状态

这是很多人最容易低估的一段。

工具执行结果，不只是“一段文本输出”。

它还可能修改系统别的状态层。

### 例子 1：规划状态

如果工具是 `todo`，它会更新的是当前会话计划。

相关章节：

- [`s03-todo-write.md`](./s03-todo-write.md)

### 例子 2：持久任务图

如果工具是 `task_create` / `task_update`，它会修改磁盘上的任务板。

相关章节：

- [`s12-task-system.md`](./s12-task-system.md)

### 例子 3：运行时任务

如果工具启动了后台 bash、后台 agent 或监控任务，它会创建 runtime task。

相关章节：

- [`s13-background-tasks.md`](./s13-background-tasks.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

### 例子 4：多 agent / teammate

如果工具是 `delegate`、`spawn_agent` 一类，它会在平台层生成新的执行单元。

相关章节：

- [`s15-agent-teams.md`](./s15-agent-teams.md)
- [`s16-team-protocols.md`](./s16-team-protocols.md)
- [`s17-autonomous-agents.md`](./s17-autonomous-agents.md)

### 例子 5：worktree

如果系统要为某个任务提供隔离工作目录，这会影响文件系统级执行环境。

相关章节：

- [`s18-worktree-task-isolation.md`](./s18-worktree-task-isolation.md)

### 例子 6：MCP

如果调用的是外部 MCP 能力，那么执行主体可能根本不在本地 handler，而在外部能力端。

相关章节：

- [`s19-mcp-plugin.md`](./s19-mcp-plugin.md)
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

## 第 8 段：执行结果被包装回消息流

不管执行落在哪一层，最后都要回到同一个位置：

```text
tool_result -> messages
```

这是整个系统最核心的闭环。

因为无论工具背后多复杂，模型下一轮真正能继续工作的依据，仍然是：

> 系统把执行结果重新写回了它可见的消息流。

这也是为什么 `s01` 永远是根。

## 第 9 段：主循环根据结果决定下一轮是否继续

当 `tool_result` 写回以后，查询状态也会一起更新：

- `messages` 变了
- `turn_count` 增加了
- `transition` 被记录成某种续行原因

这时系统就进入下一轮。

如果中间发生下面这些情况，控制平面还会继续介入：

- 上下文太长，需要压缩
- 输出被截断，需要续写
- 请求失败，需要恢复

相关章节：

- [`s06-context-compact.md`](./s06-context-compact.md)
- [`s11-error-recovery.md`](./s11-error-recovery.md)

## 第 10 段：哪些信息不会跟着一次请求一起结束

这也是非常容易混的地方。

一次请求结束后，并不是所有状态都随之消失。

### 会跟着当前请求结束的

- 当前轮 messages 中的临时推进过程
- 会话内 todo 状态
- 当前轮 reminder

### 可能跨请求继续存在的

- memory
- 持久任务图
- runtime task 输出
- worktree
- MCP 连接状态

所以你要逐渐学会区分：

```text
query-scope state
session-scope state
project-scope state
platform-scope state
```

## 用一个完整例子串一次

还是用这个请求：

```text
修复 tests/test_auth.py 的失败，并告诉我原因
```

系统可能会这样流动：

1. 用户请求进入 `QueryState`
2. system prompt + memory + tools 被组装好
3. 模型先调用 `todo`，写出三步计划
4. 模型调用 `read_file("tests/test_auth.py")`
5. 工具路由到本地文件读取 handler
6. 读取结果包装成 `tool_result` 写回消息流
7. 下一轮模型调用 `bash("pytest tests/test_auth.py -q")`
8. 权限系统判断这条命令是否可执行
9. 执行测试，输出太长则先落盘并留预览
10. 失败日志回到消息流
11. 模型再读实现文件并修改代码
12. 修改后再跑测试
13. 如果对话变长，`s06` 触发压缩
14. 如果任务被拆给子 agent，`s15-s17` 介入
15. 最后模型输出结论，本次请求结束

你会发现：

**整套系统再复杂，也始终没有脱离“输入 -> 动作意图 -> 执行 -> 结果写回 -> 下一轮”这条主骨架。**

## 读这篇时最该记住的三件事

### 1. 所有模块都不是平铺摆在那里的

它们是在一次请求的不同阶段依次介入的。

### 2. 真正的闭环只有一个

那就是：

```text
tool_result 回到 messages
```

### 3. 很多高级机制，本质上只是围绕这条闭环加的保护层

例如：

- 权限是执行前保护层
- hook 是扩展层
- compact 是上下文预算保护层
- recovery 是出错后的恢复层
- task/team/worktree/MCP 是更大的平台能力层

## 一句话记住

**一次请求的完整生命周期，本质上就是：系统围绕同一条主循环，把不同模块按阶段接进来，最终持续把真实执行结果送回模型继续推理。**
