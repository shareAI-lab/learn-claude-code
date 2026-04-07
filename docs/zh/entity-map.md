# Entity Map (系统实体边界图)

> 这份文档不是某一章的正文，而是一张“别再混词”的地图。  
> 到了仓库后半程，真正让读者困惑的往往不是代码，而是：
>
> **同一个系统里，为什么会同时出现这么多看起来很像、但其实不是一回事的实体。**

## 这张图和另外几份桥接文档怎么分工

- 这份图先回答：一个词到底属于哪一层。
- [`glossary.md`](./glossary.md) 先回答：这个词到底是什么意思。
- [`data-structures.md`](./data-structures.md) 再回答：这个词落到代码里时，状态长什么样。
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) 专门补“工作图任务”和“运行时任务”的分层。
- [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md) 专门补 MCP 平台层不是只有 tools。

## 先给一个总图

```text
对话层
  - message
  - prompt block
  - reminder

动作层
  - tool call
  - tool result
  - hook event

工作层
  - work-graph task
  - runtime task
  - protocol request

执行层
  - subagent
  - teammate
  - worktree lane

平台层
  - mcp server
  - mcp capability
  - memory record
```

## 最容易混淆的 8 对概念

### 1. Message vs Prompt Block

| 实体 | 它是什么 | 它不是什么 | 常见位置 |
|---|---|---|---|
| `Message` | 对话历史中的一条消息 | 不是长期系统规则 | `messages[]` |
| `Prompt Block` | system prompt 内的一段稳定说明 | 不是某一轮刚发生的事件 | prompt builder |

简单记法：

- message 更像“对话内容”
- prompt block 更像“系统说明”

### 2. Todo / Plan vs Task

| 实体 | 它是什么 | 它不是什么 |
|---|---|---|
| `todo / plan` | 当前轮或当前阶段的过程性安排 | 不是长期持久化工作图 |
| `task` | 持久化的工作节点 | 不是某一轮的临时思路 |

### 3. Work-Graph Task vs Runtime Task

| 实体 | 它是什么 | 它不是什么 |
|---|---|---|
| `work-graph task` | 任务板上的工作节点 | 不是系统里活着的执行单元 |
| `runtime task` | 当前正在执行的后台/agent/monitor 槽位 | 不是依赖图节点 |

这对概念是整个仓库后半程最关键的区分之一。

### 4. Subagent vs Teammate

| 实体 | 它是什么 | 它不是什么 |
|---|---|---|
| `subagent` | 一次性委派执行者 | 不是长期在线成员 |
| `teammate` | 持久存在、可重复接活的队友 | 不是一次性摘要工具 |

### 5. Protocol Request vs Normal Message

| 实体 | 它是什么 | 它不是什么 |
|---|---|---|
| `normal message` | 自由文本沟通 | 不是可追踪的审批流程 |
| `protocol request` | 带 request_id 的结构化请求 | 不是随便说一句话 |

### 6. Worktree vs Task

| 实体 | 它是什么 | 它不是什么 |
|---|---|---|
| `task` | 说明要做什么 | 不是目录 |
| `worktree` | 说明在哪做 | 不是工作目标 |

### 7. Memory vs CLAUDE.md

| 实体 | 它是什么 | 它不是什么 |
|---|---|---|
| `memory` | 跨会话仍有价值、但不易从当前代码直接推出来的信息 | 不是项目规则文件 |
| `CLAUDE.md` | 长期规则、约束和说明 | 不是用户偏好或项目动态背景 |

### 8. MCP Server vs MCP Tool

| 实体 | 它是什么 | 它不是什么 |
|---|---|---|
| `MCP server` | 外部能力提供者 | 不是单个工具定义 |
| `MCP tool` | 某个 server 暴露出来的一项具体能力 | 不是完整平台连接本身 |

## 一张“是什么 / 存在哪里”的速查表

| 实体 | 主要作用 | 典型存放位置 |
|---|---|---|
| `Message` | 当前对话历史 | `messages[]` |
| `PromptParts` | system prompt 的组装片段 | prompt builder |
| `PermissionRule` | 工具执行前的决策规则 | settings / session state |
| `HookEvent` | 某个时机触发的扩展点 | hook config |
| `MemoryEntry` | 跨会话有价值信息 | `.memory/` |
| `TaskRecord` | 持久化工作节点 | `.tasks/` |
| `RuntimeTaskState` | 正在执行的任务槽位 | runtime task manager |
| `TeamMember` | 持久队友 | `.team/config.json` |
| `MessageEnvelope` | 队友间结构化消息 | `.team/inbox/*.jsonl` |
| `RequestRecord` | 审批/关机等协议状态 | request tracker |
| `WorktreeRecord` | 隔离工作目录记录 | `.worktrees/index.json` |
| `MCPServerConfig` | 外部 server 配置 | plugin / settings |

## 后半程推荐怎么记

如果你到了 `s15` 以后开始觉得名词多，可以只记这条线：

```text
message / prompt
   管输入

tool / permission / hook
   管动作

task / runtime task / protocol
   管工作推进

subagent / teammate / worktree
   管执行者和执行车道

mcp / memory / claude.md
   管平台外延和长期上下文
```

## 初学者最容易心智打结的地方

### 1. 把“任务”这个词用在所有层

这是最常见的混乱来源。

所以建议你在写正文时，尽量直接写全：

- 工作图任务
- 运行时任务
- 后台任务
- 协议请求

不要都叫“任务”。

### 2. 把队友和子 agent 混成一类

如果生命周期不同，就不是同一类实体。

### 3. 把 worktree 当成 task 的别名

一个是“做什么”，一个是“在哪做”。

### 4. 把 memory 当成通用笔记本

它不是。它只保存很特定的一类长期信息。

## 这份图应该怎么用

最好的用法不是读一遍背下来，而是：

- 每次你发现两个词开始混
- 先来这张图里确认它们是不是一个层级
- 再回去读对应章节

如果你确认“不在一个层级”，下一步最好立刻去找它们对应的数据结构，而不是继续凭感觉读正文。

## 教学边界

这张图只解决“实体边界”这一个问题。

它不负责展开每个实体的全部字段，也不负责把所有产品化分支一起讲完。

你可以把它当成一张分层地图：

- 先确认词属于哪一层
- 再去对应章节看机制
- 最后去 [`data-structures.md`](./data-structures.md) 看状态形状

## 一句话记住

**一个结构完整的系统最怕的不是功能多，而是实体边界不清；边界一清，很多复杂度会自动塌下来。**
