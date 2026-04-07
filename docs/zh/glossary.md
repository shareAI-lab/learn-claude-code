# Glossary (术语表)

> 这份术语表只收录本仓库主线里最重要、最容易让初学者卡住的词。  
> 如果某个词你看着眼熟但说不清它到底是什么，先回这里。

## 推荐联读

如果你不是单纯查词，而是已经开始分不清“这些词分别活在哪一层”，建议按这个顺序一起看：

- 先看 [`entity-map.md`](./entity-map.md)：搞清每个实体属于哪一层。
- 再看 [`data-structures.md`](./data-structures.md)：搞清这些词真正落成什么状态结构。
- 如果你卡在“任务”这个词上，再看 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)。
- 如果你卡在 MCP 不只等于 tools，再看 [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)。

## Agent

在这套仓库里，`agent` 指的是：  
**一个能根据输入做判断，并且会调用工具去完成任务的模型。**

你可以简单理解成：

- 模型负责思考
- harness 负责给模型工作环境

## Harness

`harness` 可以理解成“给 agent 准备好的工作台”。

它包括：

- 工具
- 文件系统
- 权限
- 提示词
- 记忆
- 任务系统

模型本身不是 harness。  
harness 也不是模型。

## Agent Loop

`agent loop` 是系统反复执行的一条主循环：

1. 把当前上下文发给模型
2. 看模型是要直接回答，还是要调工具
3. 如果调工具，就执行工具
4. 把工具结果写回上下文
5. 再继续下一轮

没有这条循环，就没有 agent 系统。

## Message / Messages

`message` 是一条消息。  
`messages` 是消息列表。

它通常包含：

- 用户消息
- assistant 消息
- tool_result 消息

这份列表就是 agent 最主要的工作记忆。

## Tool

`tool` 是模型可以调用的一种动作。

例如：

- 读文件
- 写文件
- 改文件
- 跑 shell 命令
- 搜索文本

模型并不直接执行系统命令。  
模型只是说“我要调哪个工具、传什么参数”，真正执行的是你的代码。

## Tool Schema

`tool schema` 是工具的输入说明。

它告诉模型：

- 这个工具叫什么
- 这个工具做什么
- 需要哪些参数
- 参数是什么类型

可以把它想成“工具使用说明书”。

## Dispatch Map

`dispatch map` 是一张映射表：

```python
{
    "read_file": read_file_handler,
    "write_file": write_file_handler,
    "bash": bash_handler,
}
```

意思是：

- 模型说要调用 `read_file`
- 代码就去表里找到 `read_file_handler`
- 然后执行它

## Stop Reason

`stop_reason` 是模型这一轮为什么停下来的原因。

常见的有：

- `end_turn`：模型说完了
- `tool_use`：模型要调用工具
- `max_tokens`：模型输出被截断了

它决定主循环下一步怎么走。

## Context

`context` 是模型当前能看到的信息总和。

包括：

- `messages`
- system prompt
- 动态补充信息
- tool_result

上下文不是永久记忆。  
上下文是“这一轮工作时当前摆在桌上的东西”。

## Compact / Compaction

`compact` 指压缩上下文。

因为对话越长，模型能看到的历史就越多，成本和混乱也会一起增加。

压缩的目标不是“删除有用信息”，而是：

- 保留真正关键的内容
- 去掉重复和噪声
- 给后面的轮次腾空间

## Subagent

`subagent` 是从当前 agent 派生出来的一个子任务执行者。

它最重要的价值是：

**把一个大任务放到独立上下文里处理，避免污染父上下文。**

## Fork

`fork` 在本仓库语境里，指一种子 agent 启动方式：

- 不是从空白上下文开始
- 而是先继承父 agent 的已有上下文

这适合“子任务必须理解当前讨论背景”的场景。

## Permission

`permission` 就是“这个工具调用能不能执行”。

一个好的权限系统通常要回答三件事：

- 应不应该直接拒绝
- 能不能自动允许
- 剩下的是不是要问用户

## Permission Mode

`permission mode` 是权限系统的工作模式。

例如：

- `default`：默认询问
- `plan`：只允许读，不允许写
- `auto`：简单安全的操作自动过，危险操作再问

## Hook

`hook` 是一个插入点。

意思是：  
在不改主循环代码的前提下，在某个时机额外执行一段逻辑。

例如：

- 工具调用前先检查一下
- 工具调用后追加一条审计信息

## Memory

`memory` 是跨会话保存的信息。

但不是所有东西都该存 memory。

适合存 memory 的，通常是：

- 用户长期偏好
- 多次出现的重要反馈
- 未来别的会话仍然有价值的信息

## System Prompt

`system prompt` 是系统级说明。

它告诉模型：

- 你是谁
- 你能做什么
- 你有哪些规则
- 你应该如何协作

它比普通用户消息更稳定。

## System Reminder

`system reminder` 是每一轮临时追加的动态提醒。

例如：

- 当前目录
- 当前日期
- 某个本轮才需要的额外上下文

它和稳定的 system prompt 不是一回事。

## Task

`task` 是持久化任务系统里的一个任务节点。

一个 task 通常不只是一句待办事项，还会带：

- 状态
- 描述
- 依赖关系
- owner

## Dependency Graph

`dependency graph` 指任务之间的依赖关系图。

最简单的理解：

- A 做完，B 才能开始
- C 和 D 可以并行
- E 要等 C 和 D 都完成

这类结构能帮助 agent 判断：

- 现在能做什么
- 什么被卡住了
- 什么能同时做

## Worktree

`worktree` 是 Git 提供的一个机制：

同一个仓库，可以在多个不同目录里同时展开多个工作副本。

它的价值是：

- 并行做多个任务
- 不互相污染文件改动
- 便于多 agent 并行工作

## MCP

`MCP` 是 Model Context Protocol。

你可以先把它理解成一套统一接口，让 agent 能接入外部工具。

它解决的核心问题是：

- 工具不必都写死在主程序里
- 可以通过统一协议接入外部能力

如果你已经知道“能接外部工具”，但开始分不清 server、connection、tool、resource、prompt 这些层，继续看：

- [`data-structures.md`](./data-structures.md)
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md)

## Runtime Task

`runtime task` 指的是：

> 系统当前正在运行、等待完成、或者刚刚结束的一条执行单元。

例如：

- 一个后台 `pytest`
- 一个正在工作的 teammate
- 一个正在运行的 monitor

它和 `task` 不一样。

- `task` 更像工作目标
- `runtime task` 更像执行槽位

如果你总把这两个词混掉，不要只在正文里来回翻，直接去看：

- [`entity-map.md`](./entity-map.md)
- [`data-structures.md`](./data-structures.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

## Teammate

`teammate` 是长期存在的队友 agent。

它和 `subagent` 的区别是：

- `subagent`：一次性委派，干完就结束
- `teammate`：长期存在，可以反复接任务

如果你发现自己开始把这两个词混用，说明你需要回看：

- `s04`
- `s15`
- `entity-map.md`

## Protocol

`protocol` 就是一套提前约好的协作规则。

它回答的是：

- 消息应该长什么样
- 收到以后要怎么处理
- 批准、拒绝、超时这些状态怎么记录

在团队章节里，它最常见的形状是：

```text
request
  ->
response
  ->
status update
```

## Envelope

`envelope` 本意是“信封”。

在程序里，它表示：

> 把正文和一些元信息一起包起来的一条结构化记录。

例如一条协议消息里，正文之外还会附带：

- `from`
- `to`
- `request_id`
- `timestamp`

这整包东西，就可以叫一个 `envelope`。

## State Machine

`state machine` 不是很玄的高级理论。

你可以先把它理解成：

> 一张“状态可以怎么变化”的规则表。

例如：

```text
pending -> approved
pending -> rejected
pending -> expired
```

这就是一个最小状态机。

## Router

`router` 可以简单理解成“分发器”。

它的任务是：

- 看请求属于哪一类
- 把它送去正确的处理路径

例如工具层里：

- 本地工具走本地 handler
- `mcp__...` 工具走 MCP client

## Control Plane

`control plane` 可以理解成“负责协调和控制的一层”。

它通常不直接产出最终业务结果，  
而是负责决定：

- 谁来执行
- 在什么环境里执行
- 有没有权限
- 执行后要不要通知别的模块

这个词第一次看到容易怕。  
但在本仓库里，你只需要把它先记成：

> 不直接干活，负责协调怎么干活的一层。

## Capability

`capability` 就是“能力项”。

例如在 MCP 里，能力不只可能是工具，还可能包括：

- tools
- resources
- prompts
- elicitation

所以 `capability` 比 `tool` 更宽。

## Resource

`resource` 可以理解成：

> 一个可读取、可引用、但不一定是“执行动作”的外部内容入口。

例如：

- 一份文档
- 一个只读配置
- 一块可被模型读取的数据内容

它和 `tool` 的区别是：

- `tool` 更像动作
- `resource` 更像可读取内容

## Elicitation

`elicitation` 可以先理解成：

> 外部系统反过来向用户要补充输入。

也就是说，不再只是 agent 主动调用外部能力。  
外部能力也可能说：

“我还缺一点信息，请你补一下。”

## 最容易混的几对词

如果你是初学者，下面这几对词最值得一起记。

| 词对 | 最简单的区分方法 |
|---|---|
| `message` vs `system prompt` | 一个更像对话内容，一个更像系统说明 |
| `todo` vs `task` | 一个更像临时步骤，一个更像持久化工作节点 |
| `task` vs `runtime task` | 一个管目标，一个管执行 |
| `subagent` vs `teammate` | 一个一次性，一个长期存在 |
| `tool` vs `resource` | 一个更像动作，一个更像内容 |
| `permission` vs `hook` | 一个决定能不能做，一个决定要不要额外插入行为 |

---

如果读文档时又遇到新词卡住，优先回这里，不要硬顶着往后读。
