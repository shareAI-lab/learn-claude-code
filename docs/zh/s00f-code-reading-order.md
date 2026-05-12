# s00f: 本仓库代码阅读顺序

> 这份文档不是让你“多看代码”。  
> 它专门解决另一个问题：
>
> **当你已经知道章节顺序是对的以后，本仓库代码到底应该按什么顺序读，才不会把心智重新读乱。**

## 先说结论

不要这样读代码：

- 不要从文件最长的那一章开始
- 不要随机点一个你觉得“高级”的章节开始
- 不要先钻 `web/` 再回头猜主线
- 不要把 19 个 `agents/*.py` 当成一个源码池乱翻

最稳的读法只有一句话：

**文档顺着章节读，代码也顺着章节读。**

而且每一章的代码，都先按同一个模板看：

1. 先看状态结构
2. 再看工具定义或注册表
3. 再看“这一轮怎么推进”的主函数
4. 最后才看 CLI 入口和试运行方式

## 为什么需要这份文档

很多读者不是看不懂某一章文字，而是会在真正打开代码以后重新乱掉。

典型症状是：

- 一上来先盯住 300 行以上的文件底部
- 先看一堆 `run_*` 函数，却不知道它们挂在哪条主线上
- 先看“最复杂”的平台章节，然后觉得前面的章节好像都太简单
- 把 `task`、`runtime task`、`teammate`、`worktree` 在代码里重新混成一团

这份阅读顺序就是为了防止这种情况。

## 读每个 agent 文件时，都先按同一个模板

不管你打开的是哪一章，本仓库里的 `agents/sXX_*.py` 都建议先按下面顺序读：

### 第一步：先看文件头注释

先回答两个问题：

- 这一章到底在教什么
- 它故意没有教什么

如果连这一步都没建立，后面你会把每个函数都看成同等重要。

### 第二步：先看状态结构或管理器类

优先找这些东西：

- `LoopState`
- `PlanningState`
- `CompactState`
- `TaskManager`
- `BackgroundManager`
- `TeammateManager`
- `WorktreeManager`

原因很简单：

**先知道系统到底记住了什么，后面才看得懂它为什么要这样流动。**

### 第三步：再看工具列表或注册表

优先找这些入口：

- `TOOLS`
- `TOOL_HANDLERS`
- 各种 `run_*`
- `build_tool_pool()`

这一层回答的是：

- 模型到底能调用什么
- 这些调用会落到哪条执行面上

### 第四步：最后才看主推进函数

重点函数通常长这样：

- `run_one_turn(...)`
- `agent_loop(...)`
- 某个 `handle_*`

这一步要回答的是：

- 这一章新机制到底接在主循环哪一环
- 哪个分支是新增的
- 新状态是在哪里写入、回流、继续的

### 第五步：最后再看 `if __name__ == "__main__"`

CLI 入口当然有用，但它不应该成为第一屏。

因为它通常只是在做：

- 读用户输入
- 初始化状态
- 调用 `agent_loop`

真正决定一章心智主干的，不在这里。

## 阶段 1：`s01-s06` 应该怎样读代码

这一段不是在学“很多功能”，而是在学：

**一个单 agent 主骨架到底怎样成立。**

| 章节 | 文件 | 先看什么 | 再看什么 | 读完要确认什么 |
|---|---|---|---|---|
| `s01` | `agents/s01_agent_loop.py` | `LoopState` | `TOOLS` -> `execute_tool_calls()` -> `run_one_turn()` -> `agent_loop()` | 你已经能看懂 `messages -> model -> tool_result -> next turn` |
| `s02` | `agents/s02_tool_use.py` | `safe_path()` | `run_read()` / `run_write()` / `run_edit()` -> `TOOL_HANDLERS` -> `agent_loop()` | 你已经能看懂“主循环不变，工具靠分发面增长” |
| `s03` | `agents/s03_todo_write.py` | `PlanItem` / `PlanningState` / `TodoManager` | `todo` 相关 handler -> reminder 注入 -> `agent_loop()` | 你已经能看懂“会话计划状态”怎么外显化 |
| `s04` | `agents/s04_subagent.py` | `AgentTemplate` | `run_subagent()` -> 父 `agent_loop()` | 你已经能看懂“子智能体首先是上下文隔离” |
| `s05` | `agents/s05_skill_loading.py` | `SkillManifest` / `SkillDocument` / `SkillRegistry` | `get_descriptions()` / `get_content()` -> `agent_loop()` | 你已经能看懂“先发现、再按需加载” |
| `s06` | `agents/s06_context_compact.py` | `CompactState` | `persist_large_output()` -> `micro_compact()` -> `compact_history()` -> `agent_loop()` | 你已经能看懂“压缩不是删历史，而是转移细节” |

### 这一段最值得反复看的 3 个代码点

1. `state` 在哪里第一次从“聊天内容”升级成“显式系统状态”
2. `tool_result` 是怎么一直保持为统一回流接口的
3. 新机制是怎样接进 `agent_loop()` 而不是把 `agent_loop()` 重写烂的

### 这一段读完后，最好的动作

不要立刻去看 `s07`。

先自己从空目录手写一遍下面这些最小件：

- 一个 loop
- 一个 dispatch map
- 一个会话计划状态
- 一个一次性子任务隔离
- 一个按需技能加载
- 一个最小压缩层

## 阶段 2：`s07-s11` 应该怎样读代码

这一段不是在学“又多了五种功能”。

它真正是在学：

**单 agent 的控制面是怎样长出来的。**

| 章节 | 文件 | 先看什么 | 再看什么 | 读完要确认什么 |
|---|---|---|---|---|
| `s07` | `agents/s07_permission_system.py` | `BashSecurityValidator` / `PermissionManager` | 权限判定入口 -> `run_bash()` -> `agent_loop()` | 你已经能看懂“先 gate，再 execute” |
| `s08` | `agents/s08_hook_system.py` | `HookManager` | hook 注册与触发 -> `agent_loop()` | 你已经能看懂 hook 是固定时机的插口，不是散落 if |
| `s09` | `agents/s09_memory_system.py` | `MemoryManager` / `DreamConsolidator` | `run_save_memory()` -> `build_system_prompt()` -> `agent_loop()` | 你已经能看懂 memory 是长期信息层，不是上下文垃圾桶 |
| `s10` | `agents/s10_system_prompt.py` | `SystemPromptBuilder` | `build_system_reminder()` -> `agent_loop()` | 你已经能看懂输入是流水线，不是单块 prompt |
| `s11` | `agents/s11_error_recovery.py` | `estimate_tokens()` / `auto_compact()` / `backoff_delay()` | 各恢复分支 -> `agent_loop()` | 你已经能看懂“恢复以后怎样继续下一轮” |

### 这一段读代码时，最容易重新读乱的地方

1. 把权限和 hook 混成一类
2. 把 memory 和 prompt 装配混成一类
3. 把 `s11` 看成很多异常判断，而不是“续行控制”

如果你开始混，先回：

- `docs/zh/s00a-query-control-plane.md`
- `docs/zh/s10a-message-prompt-pipeline.md`
- `docs/zh/s00c-query-transition-model.md`

## 阶段 3：`s12-s14` 应该怎样读代码

这一段开始，代码理解的关键不再是“工具多了什么”，而是：

**系统第一次真正长出会话外工作状态和运行时槽位。**

| 章节 | 文件 | 先看什么 | 再看什么 | 读完要确认什么 |
|---|---|---|---|---|
| `s12` | `agents/s12_task_system.py` | `TaskManager` | 任务创建、依赖、解锁 -> `agent_loop()` | 你已经能看懂 task 是持久工作图，不是 todo |
| `s13` | `agents/s13_background_tasks.py` | `NotificationQueue` / `BackgroundManager` | 后台执行登记 -> 通知排空 -> `agent_loop()` | 你已经能看懂 background task 是运行槽位 |
| `s14` | `agents/s14_cron_scheduler.py` | `CronLock` / `CronScheduler` | `cron_matches()` -> schedule 触发 -> `agent_loop()` | 你已经能看懂调度器只负责“未来何时开始” |

### 这一段读代码时一定要守住的边界

- `task` 是工作目标
- `runtime task` 是正在跑的执行槽位
- `schedule` 是何时触发工作

只要这三层在代码里重新混掉，后面 `s15-s19` 会一起变难。

## 阶段 4：`s15-s19` 应该怎样读代码

这一段不要当成“功能狂欢”去读。

它真正建立的是：

**平台边界。**

| 章节 | 文件 | 先看什么 | 再看什么 | 读完要确认什么 |
|---|---|---|---|---|
| `s15` | `agents/s15_agent_teams.py` | `MessageBus` / `TeammateManager` | 队友名册、邮箱、独立循环 -> `agent_loop()` | 你已经能看懂 teammate 是长期 actor，不是一次性 subagent |
| `s16` | `agents/s16_team_protocols.py` | `RequestStore` / `TeammateManager` | `handle_shutdown_request()` / `handle_plan_review()` -> `agent_loop()` | 你已经能看懂 request-response + `request_id` |
| `s17` | `agents/s17_autonomous_agents.py` | `RequestStore` / `TeammateManager` | `is_claimable_task()` / `claim_task()` / `ensure_identity_context()` -> `agent_loop()` | 你已经能看懂自治主线：空闲检查 -> 安全认领 -> 恢复工作 |
| `s18` | `agents/s18_worktree_task_isolation.py` | `TaskManager` / `WorktreeManager` / `EventBus` | `worktree_enter` 相关生命周期 -> `agent_loop()` | 你已经能看懂 task 管目标，worktree 管执行车道 |
| `s19` | `agents/s19_mcp_plugin.py` | `CapabilityPermissionGate` / `MCPClient` / `PluginLoader` / `MCPToolRouter` | `build_tool_pool()` / `handle_tool_call()` / `normalize_tool_result()` -> `agent_loop()` | 你已经能看懂外部能力如何接回同一控制面 |

### 这一段最容易误读的地方

1. 把 `s15` 的 teammate 当成 `s04` 的 subagent 放大版
2. 把 `s17` 自治看成“agent 自己乱跑”
3. 把 `s18` worktree 看成一个 git 小技巧
4. 把 `s19` MCP 缩成“只是远程 tools”

## 代码阅读时，哪些文件不要先看

如果你的目标是建立主线心智，下面这些内容不要先看：

- `web/` 里的可视化实现细节
- `web/src/data/generated/*`
- `.next/` 或其他构建产物
- `agents/s_full.py`

原因不是它们没价值。

而是：

- `web/` 解决的是展示与学习界面
- `generated` 是抽取结果，不是机制本身
- `s_full.py` 是整合参考，不适合第一次建立边界

## 最推荐的“文档 + 代码 + 运行”循环

每一章最稳的学习动作不是只看文档，也不是只看代码。

推荐固定走这一套：

1. 先读这一章正文
2. 再读这一章的桥接资料
3. 再打开对应 `agents/sXX_*.py`
4. 按“状态 -> 工具 -> 主推进函数 -> CLI 入口”的顺序看
5. 跑一次这章的 demo
6. 自己从空目录重写一个最小版本

只要你每章都这样走一次，代码理解会非常稳。

## 初学者最容易犯的 6 个代码阅读错误

### 1. 先看最长文件

这通常只会先把自己看晕。

### 2. 先盯 `run_bash()` 这种工具细节

工具实现细节不是主干。

### 3. 不先找状态结构

这样你永远不知道系统到底记住了什么。

### 4. 把 `agent_loop()` 当成唯一重点

主循环当然重要，但每章真正新增的边界，往往在状态容器和分支入口。

### 5. 读完代码不跑 demo

不实际跑一次，很难建立“这一章到底新增了哪条回路”的感觉。

### 6. 一口气连看三四章代码，不停下来自己重写

这样最容易出现“我好像都看过，但其实自己不会写”的错觉。

## 一句话记住

**代码阅读顺序也必须服从教学顺序：先看边界，再看状态，再看主线如何推进，而不是随机翻源码。**
