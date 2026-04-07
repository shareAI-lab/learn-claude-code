# s00e: 参考仓库模块映射图

> 这是一份给维护者和认真学习者用的校准文档。  
> 它不是让读者逐行读逆向源码。
>
> 它只回答一个很关键的问题：
>
> **如果把参考仓库里真正重要的模块簇，和当前教学仓库的章节顺序对照起来看，现在这套课程顺序到底合不合理？**

## 先说结论

合理。

当前这套 `s01 -> s19` 的顺序，整体上是对的，而且比“按源码目录顺序讲”更接近真实系统的设计主干。

原因很简单：

- 参考仓库里目录很多
- 但真正决定系统骨架的，是少数几簇控制、状态、任务、团队、隔离执行和外部能力模块
- 这些高信号模块，和当前教学仓库的四阶段主线基本是对齐的

所以正确动作不是把教程改成“跟着源码树走”。

正确动作是：

- 保留现在这条按依赖关系展开的主线
- 把它和参考仓库的映射关系讲明白
- 继续把低价值的产品外围细节挡在主线外

## 这份对照是怎么做的

这次对照主要看的是参考仓库里真正决定系统骨架的部分，例如：

- `Tool.ts`
- `state/AppStateStore.ts`
- `coordinator/coordinatorMode.ts`
- `memdir/*`
- `services/SessionMemory/*`
- `services/toolUseSummary/*`
- `constants/prompts.ts`
- `tasks/*`
- `tools/TodoWriteTool/*`
- `tools/AgentTool/*`
- `tools/ScheduleCronTool/*`
- `tools/EnterWorktreeTool/*`
- `tools/ExitWorktreeTool/*`
- `tools/MCPTool/*`
- `services/mcp/*`
- `plugins/*`
- `hooks/toolPermission/*`

这些已经足够判断“设计主脉络”。

没有必要为了教学，再把每个命令目录、兼容分支、UI 细节和产品接线全部拖进正文。

## 真正的映射关系

| 参考仓库模块簇 | 典型例子 | 对应教学章节 | 为什么这样放是对的 |
|---|---|---|---|
| 查询主循环 + 控制状态 | `Tool.ts`、`AppStateStore.ts`、query / coordinator 状态 | `s00`、`s00a`、`s00b`、`s01`、`s11` | 真实系统绝不只是 `messages[] + while True`。教学上先讲最小循环，再补控制平面，是对的。 |
| 工具路由与执行面 | `Tool.ts`、原生 tools、tool context、执行辅助逻辑 | `s02`、`s02a`、`s02b` | 参考仓库明确把 tools 做成统一执行面，不只是玩具版分发表。当前拆法是合理的。 |
| 会话规划 | `TodoWriteTool` | `s03` | 这是“当前会话怎么不乱撞”的小结构，应该早于持久任务图。 |
| 一次性委派 | `AgentTool` 的最小子集 | `s04` | 参考仓库的 agent 体系很大，但教学仓库先教“新上下文 + 子任务 + 摘要返回”这个最小正确版本，是对的。 |
| 技能发现与按需加载 | `DiscoverSkillsTool`、`skills/*`、相关 prompt 片段 | `s05` | 技能不是花哨外挂，而是知识注入层，所以应早于 prompt 复杂化和上下文压力。 |
| 上下文压力与压缩 | `services/toolUseSummary/*`、`services/contextCollapse/*`、compact 逻辑 | `s06` | 参考仓库明确存在显式压缩机制，把这一层放在平台化能力之前完全正确。 |
| 权限闸门 | `types/permissions.ts`、`hooks/toolPermission/*`、审批处理器 | `s07` | 执行安全是明确闸门，不是“某个 hook 顺手干的事”，所以必须早于 hook。 |
| Hook 与侧边扩展 | `types/hooks.ts`、hook runner、生命周期接线 | `s08` | 参考仓库把扩展点和权限分开。教学顺序保持“先 gate，再 extend”是对的。 |
| 持久记忆选择 | `memdir/*`、`services/SessionMemory/*`、记忆提取与筛选 | `s09` | 参考仓库把 memory 处理成“跨会话、选择性装配”的层，不是通用笔记本。 |
| Prompt 组装 | `constants/prompts.ts`、prompt sections、memory prompt 注入 | `s10`、`s10a` | 参考仓库明显把输入拆成多个 section。教学版把 prompt 讲成流水线，而不是一段大字符串，是正确的。 |
| 恢复与续行 | query transition、retry 分支、compact retry、token recovery | `s11`、`s00c` | 真实系统里“为什么继续下一轮”是显式存在的，所以恢复应当晚于 loop / tools / compact / permissions / memory / prompt。 |
| 持久工作图 | 任务记录、任务板、依赖解锁 | `s12` | 当前教程把“持久任务目标”和“会话内待办”分开，是对的。 |
| 活着的运行时任务 | `tasks/types.ts`、`LocalShellTask`、`LocalAgentTask`、`RemoteAgentTask`、`MonitorMcpTask` | `s13`、`s13a` | 参考仓库里 runtime task 是明确的联合类型，这强烈证明 `TaskRecord` 和 `RuntimeTaskState` 必须分开教。 |
| 定时触发 | `ScheduleCronTool/*`、`useScheduledTasks` | `s14` | 调度是建在 runtime work 之上的新启动条件，放在 `s13` 后非常合理。 |
| 持久队友 | `InProcessTeammateTask`、team tools、agent registry | `s15` | 参考仓库清楚地从一次性 subagent 继续长成长期 actor。把 teammate 放到后段是对的。 |
| 结构化团队协作 | send-message 流、request tracking、coordinator mode | `s16` | 协议必须建立在“已有持久 actor”之上，所以不能提前。 |
| 自治认领与恢复 | coordinator mode、任务认领、异步 worker 生命周期、resume 逻辑 | `s17` | 参考仓库里的 autonomy 不是魔法，而是建立在 actor、任务和协议之上的。 |
| Worktree 执行车道 | `EnterWorktreeTool`、`ExitWorktreeTool`、agent worktree 辅助逻辑 | `s18` | 参考仓库把 worktree 当作执行边界 + 收尾状态来处理。当前放在 tasks / teams 后是正确的。 |
| 外部能力总线 | `MCPTool`、`services/mcp/*`、`plugins/*`、MCP resources / prompts / tools | `s19`、`s19a` | 参考仓库把 MCP / plugin 放在平台最外层边界。把它放最后是合理的。 |

## 这份对照最能证明的 5 件事

### 1. `s03` 应该继续放在 `s12` 前面

参考仓库里同时存在：

- 小范围的会话计划
- 大范围的持久任务 / 运行时系统

它们不是一回事。

所以教学顺序应当继续保持：

`会话内计划 -> 持久任务图`

### 2. `s09` 应该继续放在 `s10` 前面

参考仓库里的输入装配，明确把 memory 当成输入来源之一。

也就是说：

- `memory` 先回答“内容从哪里来”
- `prompt pipeline` 再回答“这些内容怎么组装进去”

所以先讲 `s09`，再讲 `s10`，顺序不要反过来。

### 3. `s12` 必须早于 `s13`

`tasks/types.ts` 这类运行时任务联合类型，是这次对照里最强的证据之一。

它非常清楚地说明：

- 持久化的工作目标
- 当前活着的执行槽位

必须是两层不同状态。

如果先讲 `s13`，读者几乎一定会把这两层混掉。

### 4. `s15 -> s16 -> s17` 的顺序是对的

参考仓库里明确能看到：

- 持久 actor
- 结构化协作
- 自治认领 / 恢复

自治必须建立在前两者之上，所以当前顺序合理。

### 5. `s18` 应该继续早于 `s19`

参考仓库把 worktree 当作本地执行边界机制。

这应该先于：

- 外部能力提供者
- MCP server
- plugin 装配面

被讲清。

否则读者会误以为“外部能力系统比本地执行边界更核心”。

## 这套教学仓库仍然不该抄进主线的内容

参考仓库里有很多真实但不应该占据主线的内容，例如：

- CLI 命令面的完整铺开
- UI 渲染细节
- 遥测与分析分支
- 远程 / 企业产品接线
- 平台兼容层
- 文件名、函数名、行号级 trivia

这些不是假的。

但它们不该成为 0 到 1 教学路径的中心。

## 当前教学最容易漂掉的地方

### 1. 不要把 subagent 和 teammate 混成一个模糊概念

参考仓库里的 `AgentTool` 横跨了：

- 一次性委派
- 后台 worker
- 持久 worker / teammate
- worktree 隔离 worker

这恰恰说明教学仓库应该继续拆开讲：

- `s04`
- `s15`
- `s17`
- `s18`

不要在早期就把这些东西混成一个“大 agent 能力”。

### 2. 不要把 worktree 教成“只是 git 小技巧”

参考仓库里有 closeout、resume、cleanup、dirty-check 等状态。

所以 `s18` 必须继续讲清：

- lane 身份
- task 绑定
- keep / remove 收尾
- 恢复与清理

而不是只讲 `git worktree add`。

### 3. 不要把 MCP 缩成“远程 tools”

参考仓库里明显不只有工具，还有：

- resources
- prompts
- elicitation / connection state
- plugin 中介层

所以 `s19` 可以继续用 tools-first 的教学路径切入，但一定要补平台边界那一层地图。

## 最终判断

如果只拿“章节顺序是否贴近参考仓库的设计主干”这个问题来打分，那么当前这套顺序是过关而且方向正确的。

真正还能继续加分的地方，不再是再做一次大重排，而是：

- 把桥接文档补齐
- 把实体边界讲得更硬
- 把多语言内容统一到同一个心智层次
- 让 web 页面把这套学习地图展示得更清楚

## 一句话记住

**最好的教学顺序，不是源码文件出现的顺序，而是一个初学实现者真正能顺着依赖关系把系统重建出来的顺序。**
