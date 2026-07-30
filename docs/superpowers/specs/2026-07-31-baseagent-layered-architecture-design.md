# BaseAgent 分层拆分设计

## 背景

`homework/BaseAgent.py` 当前约 3,232 行，已经在一个模块中累计实现以下能力：

- CLI 和进程生命周期；
- Agent Loop、流式响应和错误恢复；
- system prompt、动态上下文、记忆和上下文压缩；
- builtin tools、hook、权限检查和工具注册；
- Todo、持久任务、后台任务和 cron；
- subagent、agent teams、mailbox 和协作协议；
- worktree 和 MCP。

这些能力大多通过模块级全局变量、锁、队列和注册表连接。现有 BaseAgent
测试还通过 `runpy.run_path()` 和 `agent_loop.__globals__` 访问、替换内部符号。
因此，直接把注释区块剪切到多个文件会破坏测试注入，也可能把单文件内的隐式
依赖变成跨模块循环依赖。

当前工作区中的 `BaseAgent.py` 相对 Git 基线已有约 1,403 行新增和 207 行
删除。拆分实施必须先保存并确认这部分工作，不能把既有功能改动与架构迁移混成
一个不可审查的改动。

## 已确认约束

- `uv run python homework/BaseAgent.py` 在整个迁移过程中保持可运行。
- 最终的 `homework/BaseAgent.py` 只作为 CLI 入口，不作为对外 API。
- 允许引入一个内部 `RuntimeContext`，但不把现有函数大规模重写成类。
- 优先移动和复用现有实现，不重新生成大段等价代码。
- 迁移按可测试、可回滚的批次进行。
- 拆分期间不顺便改变功能语义。
- 最终测试不能依赖 `BaseAgent.py` 的模块全局命名空间。

## 目标

1. 把 CLI、核心编排、工具、业务能力和外部适配器分开。
2. 让每个模块具有单一、可描述、可独立测试的职责。
3. 用显式运行时状态替代散落的模块级可变全局变量。
4. 让新增普通工具或 feature 不需要修改 Agent Loop。
5. 隔离 Anthropic SDK、文件系统、线程和 subprocess 等副作用。
6. 保持当前实现可识别，避免为追求架构形式进行全面重写。

## 非目标

- 不把该教学项目改造成通用 agent framework。
- 不复制或声称复刻 Claude Code 的闭源内部实现。
- 不在拆分中引入 event bus framework、IoC 容器或大型异常体系。
- 不为每个函数创建 service 类。
- 不在拆分中统一重命名、格式化或优化全部现有代码。
- 不承诺 `agent_app` 内部模块具有跨版本兼容性。

## 方案比较

### 方案一：机械拆文件

按现有注释区块把代码移动到若干模块，继续使用模块级全局变量，并从
`BaseAgent.py` 重新导出原有符号。

优点是初始改动少。缺点是文件之间仍通过全局状态耦合，测试仍依赖实现细节，
`BaseAgent.py` 也会继续承担事实上的公共 API。该方案不能满足长期扩展目标。

### 方案二：内部应用包和组合根

把现有代码按领域移动到内部包，通过 `bootstrap.py` 组装
`RuntimeContext`、feature state、工具和适配器。纯函数保持纯函数，只有需要
共享状态或外部资源的函数才增加显式参数。

该方案能保留现有函数主体，同时消除最主要的全局状态和测试耦合。它是本设计的
选定方案。

### 方案三：完整端口与适配器架构

全面引入 protocol、service、repository、typed event 和依赖注入接口。

该方案隔离最强，但会产生大量新抽象和重写，不符合教学仓库的显式代码风格，
也不符合“少生成新代码”的约束。

## 目标目录结构

```text
homework/
├── BaseAgent.py
└── agent_app/
    ├── __init__.py
    ├── cli.py
    ├── bootstrap.py
    ├── config.py
    ├── runtime.py
    │
    ├── core/
    │   ├── loop.py
    │   ├── context.py
    │   ├── prompt.py
    │   ├── recovery.py
    │   └── compaction.py
    │
    ├── tools/
    │   ├── registry.py
    │   ├── executor.py
    │   ├── builtin.py
    │   └── hooks.py
    │
    ├── features/
    │   ├── todos.py
    │   ├── tasks.py
    │   ├── background.py
    │   ├── scheduler.py
    │   ├── memory.py
    │   ├── skills.py
    │   ├── subagents.py
    │   ├── worktrees.py
    │   ├── mcp.py
    │   └── teams/
    │       ├── bus.py
    │       ├── protocol.py
    │       └── teammates.py
    │
    └── adapters/
        └── anthropic.py
```

内部包不命名为 `homework/baseagent/`。当前同时保留 `BaseAgent.py`，在默认
大小写不敏感的 macOS 文件系统上使用仅大小写不同的模块名称容易造成导入解析
歧义。`agent_app` 也更准确地表达了“内部应用实现”。

## 分层职责

### CLI 层

`BaseAgent.py` 最终只导入并调用 `agent_app.cli.main()`。

`cli.py` 负责：

- 读取用户输入；
- 识别退出命令；
- 启动和停止运行时线程；
- 在 `finally` 中触发停止事件并回收线程；
- 将每次用户输入交给核心运行时。

CLI 不包含工具、任务、记忆或协作业务逻辑。

### 组合层

`bootstrap.py` 是唯一知道全部模块的组合根，负责：

- 加载配置；
- 创建 Anthropic adapter；
- 创建 session 和各 feature state；
- 创建工具与 hook registry；
- 注册 builtin 和 feature tools；
- 注册默认 hook；
- 构造 `RuntimeContext`。

模块导入期间不得自动完成这些动作。

### 核心层

`core/loop.py` 只负责编排一次 agent turn：

- 收集异步通知；
- 执行压缩流水线；
- 获取工具快照；
- 构建动态上下文和 system prompt；
- 调用 LLM adapter；
- 应用恢复策略；
- 分派工具；
- 写回消息并判断是否结束。

`core/context.py`、`prompt.py`、`recovery.py` 和 `compaction.py` 分别拥有各自
规则。它们不操作 mailbox、task 文件或 worktree。

### 工具层

`tools/registry.py` 管理工具 schema 和 handler，提供当前 schema/handler
快照。`tools/executor.py` 负责同步与后台分派。`tools/builtin.py` 保留
bash、read、write、edit、glob 等基础工具。`tools/hooks.py` 管理 hook
注册、权限、日志和 diff preview。

工具层不直接构造 feature。feature handler 与 runtime state 的绑定由
`bootstrap.py` 完成。

### Feature 层

每个 feature 拥有自己的模型、状态和操作：

- `todos.py`：当前进程中的会话 Todo；
- `tasks.py`：持久任务图及并发 claim；
- `background.py`：后台工具任务和完成通知；
- `scheduler.py`：cron 校验、持久任务和调度队列；
- `memory.py`：记忆读取、提取和整合；
- `skills.py`：skill 扫描、目录和加载；
- `subagents.py`：同步、一次性子代理；
- `worktrees.py`：worktree 创建、绑定、保留和删除；
- `mcp.py`：MCP client、工具元数据和动态注册；
- `teams/`：mailbox、协议状态和 teammate 生命周期。

Feature 不导入 CLI 或 Agent Loop。普通 feature 不能主动递归调用主循环。

### Adapter 层

`adapters/anthropic.py` 隔离 Anthropic SDK：

- 普通消息创建；
- 流式文本输出；
- partial stream error；
- SDK 请求参数。

测试通过 fake adapter 运行，不需要修改 `sys.modules` 来伪造整个
`anthropic` 包。

## RuntimeContext 设计

`RuntimeContext` 是内部组合对象，不是新的巨型 `BaseAgent` 类。它只保存
引用，不实现 feature 业务方法。

```text
RuntimeContext
├── config
├── llm
├── session
├── tools
├── hooks
├── scheduler
├── background
├── tasks
├── teams
└── mcp
```

每个 feature 在自己的模块中定义状态类型，例如 `SchedulerState`、
`BackgroundState`、`TaskStore`、`TeamState` 和 `MCPState`。

普通 feature 函数只接收自己需要的 state：

```python
create_task(task_store, subject, description)
schedule_job(scheduler_state, cron, prompt)
read_inbox(team_state, agent_name)
```

只有 `bootstrap`、CLI 生命周期和 Agent Loop 这种跨 subsystem 编排代码接收
完整 `RuntimeContext`。

以下做法被明确禁止：

- feature 导入模块级全局 runtime 单例；
- 把业务逻辑逐渐添加为 `RuntimeContext` 方法；
- 把请求中的临时变量存入 runtime；
- feature 通过 runtime 随意访问其他 feature；
- import 模块时创建 client、目录或线程。

## 配置与副作用

`AppConfig` 保存静态配置：

- repository/workspace 根目录；
- skills、memory、task、mailbox、transcript 和输出路径；
- primary/fallback model；
- context、output、retry 和 timeout 阈值。

配置对象在构造后保持只读。测试可以用 `tmp_path` 构造完整配置，避免通过
monkeypatch 替换多个模块全局路径。

启动顺序固定为：

```text
load_config
→ create_adapter
→ create_feature_states
→ create_registries
→ register_builtin_hooks
→ register_feature_tools
→ build RuntimeContext
→ start runtime threads
→ run CLI loop
→ stop and join runtime threads
```

导入内部模块不得创建持久化目录、读取并覆盖 `.env`、创建 Anthropic client、
启动线程或修改全局工具列表。

## 依赖方向

```text
BaseAgent.py
    → cli
        → bootstrap
            → core
                → tools / feature narrow interfaces
                    → adapters
```

具体约束：

- `features` 不能导入 `core.loop`。
- `features` 之间原则上不直接导入。
- 跨 feature 协调放在组合根或明确的应用协调函数中。
- `registry.py` 不主动导入所有 feature。
- `adapters` 不知道 Agent Loop 和业务 feature。
- `config.py` 不导入运行时模块。
- 为避免循环导入，feature 函数接收自己的 state，而不是导入
  `RuntimeContext`。

## 主循环数据流

```text
CLI 接收输入
→ 写入 SessionState
→ AgentLoop 收集 scheduler/background/team 通知
→ CompactionPipeline 控制上下文
→ ToolRegistry 生成工具快照
→ ContextBuilder 构建动态上下文
→ PromptBuilder 生成 system prompt
→ AnthropicAdapter 发起流式请求
→ RecoveryPolicy 处理重试、模型降级和续写
→ AgentLoop 解析响应
→ HookRegistry 执行权限和审计 hook
→ ToolExecutor 分派同步或后台工具
→ feature handler 执行能力
→ 工具结果写回消息
→ 继续下一轮或结束 turn
```

Scheduler thread 只把 `CronJob` 放入队列。Background worker 只写入完成状态。
Team mailbox 只存放消息。所有通知由 Agent Loop 在稳定边界统一 drain，避免
多个 subsystem 并发修改会话历史。

## 工具注册

当前实现通过多个 schema 列表、handler 字典、`append()` 和 MCP 动态工具
组合工具池。目标实现由 `ToolRegistry` 统一管理：

```text
bootstrap
├── register builtin tools
├── register todo/task tools
├── register scheduler/worktree tools
├── register team/subagent tools
└── merge connected MCP tools
```

Handler 在注册时绑定所需 state。Agent Loop 每轮只读取 schema snapshot 和
handler snapshot。

`compact` 是会改变会话控制流的特殊 action。它保留 schema，但不注册普通
handler，由 Agent Loop 显式处理。其他普通 feature 不得要求修改
`core/loop.py`。

## 错误处理

拆分阶段先保持当前可观察行为，不同时引入大型结果类型或异常继承树。

- 配置错误由 bootstrap 抛出并终止启动。
- 参数校验错误由 feature 返回明确错误，并转换为 tool result。
- 权限拒绝由 pre-tool hook 返回，handler 不得执行。
- 同步工具异常在 ToolExecutor 边界转换为失败结果，保持 tool use/result
  配对。
- 后台工具异常写入 `BackgroundState`，由下一轮生成 failed notification。
- LLM 临时错误只由 RecoveryPolicy 处理。
- LLM 不可恢复错误追加可见错误消息并结束当前 turn，不终止 CLI 进程。
- 持久化损坏必须返回包含路径和原因的清晰错误。
- 不使用无日志的 `except: pass` 隐藏持久化问题。
- 编程错误在单元测试中直接暴露，不在底层模块无条件吞掉。

## 分阶段迁移

### 阶段 0：校准测试基线

当前六组 BaseAgent 离线测试在手动中断前报告 `63 passed, 33 failed`。中断
原因是 teammate 测试进入真实 60 秒 idle polling。已观察到的失败类型包括：

- 测试引用已不存在的 `TOOLS`、`TOOL_HANDLERS` 和 `run_agent_turn`；
- 测试替身不接受当前 `update_context(..., tools=...)` 签名；
- `start_background_task` 等接口发生漂移；
- mailbox 命名和 teammate 初始消息存在预期差异；
- 并发测试依赖真实等待。

实施前逐项判断失败属于实现缺陷、过期测试还是尚未完成的需求。有效需求测试应
先恢复为绿色；不能用拆分掩盖既有失败。线程测试改用可控 Event、测试时钟或
短轮询配置。

同时增加 fake adapter 下的 CLI smoke test。

### 阶段 1：建立包、配置和运行时

创建内部包、`AppConfig`、各 state 类型、`RuntimeContext` 和
`build_runtime()`，但暂时不迁移 Agent Loop。`BaseAgent.py` 继续运行现有
逻辑。

### 阶段 2：迁移纯函数

优先原样移动：

- cron 校验和匹配；
- API 错误分类和 retry delay；
- message/tool block 判断；
- compaction 边界计算；
- agent/task/worktree 名称校验；
- 文本提取和格式化。

不在移动时重命名、格式化或改变算法。

### 阶段 3：迁移低耦合 feature

按以下顺序迁移：

1. Todo；
2. skills；
3. memory；
4. tasks；
5. worktrees；
6. builtin filesystem/process tools。

每次只迁移一个 feature，把路径放入配置，把可变状态放入对应 state，并在同一
批次迁移该 feature 的测试。

### 阶段 4：迁移并发和协作能力

按以下顺序迁移：

1. background；
2. scheduler；
3. team bus；
4. team protocol；
5. teammates；
6. subagents。

线程函数接收明确 state 和 `stop_event`。测试不得使用真实长时间 sleep，且
测试结束后不能遗留工作线程。

### 阶段 5：迁移工具注册、hook 和 MCP

建立 `ToolRegistry` 和 `HookRegistry`，将静态工具、feature 工具、subagent
工具和 MCP 工具改由 bootstrap 注册。去掉 import-time 的
`BUILTIN_TOOLS.append()` 模式。

### 阶段 6：迁移核心

按以下顺序迁移：

1. Anthropic adapter；
2. recovery；
3. compaction；
4. context 和 prompt；
5. Agent Loop。

Agent Loop 最后迁移，以免在依赖边界尚未稳定时同时修改所有调用。

### 阶段 7：切换薄入口

最终 `homework/BaseAgent.py` 仅保留：

```python
from agent_app.cli import main

if __name__ == "__main__":
    main()
```

删除迁移期间的临时兼容导入和 wrapper。`agent_app/__init__.py` 不聚合导出
内部函数。

## 迁移批次规则

每个批次必须：

- 只移动一个清晰职责；
- 同时迁移其测试；
- 不混入无关格式化和业务优化；
- 保持 `BaseAgent.py` 可执行；
- 不新增有效测试失败；
- 形成可以独立审查和回退的 diff；
- 在移动 Agent Loop 前先稳定所有被调用模块。

临时兼容 wrapper 只用于保持中间检查点可运行，并必须在阶段 7 删除，不能形成
新的公开兼容层。

## 测试策略

### 单元测试

直接测试纯函数和单个 feature：

- cron、错误分类和 compaction；
- Todo 和任务状态转换；
- task claim 并发；
- mailbox 和协议匹配；
- 工具 schema 和 handler 注册。

### Feature 测试

每个测试创建自己的 feature state，所有持久化路径指向 `tmp_path`。并发测试
使用 Event 和有上限的短等待，不依赖全局状态或真实 60 秒轮询。

### 核心集成测试

使用 fake adapter、fake tool registry、fake hooks 和 fake notification
source 验证：

- 完整 agent turn；
- tool use/result 配对；
- max tokens 和 partial stream continuation；
- reactive compaction；
- 同步、后台和权限拒绝分支；
- scheduler/background/team 通知注入。

### CLI smoke test

验证 `BaseAgent.py` 能：

- 通过 bootstrap 构造 runtime；
- 在 fake adapter 下启动；
- 读取退出输入；
- 停止并回收运行时线程。

### 必须移除的测试耦合

最终测试不得使用：

```python
namespace["agent_loop"].__globals__
monkeypatch.setitem(baseagent_globals, "dependency", replacement)
```

测试应导入真实所有者模块、构造独立 state，或向 bootstrap/adapter 注入替身。

## 扩展规则

新增普通 feature 时：

1. 在 `features/` 中定义状态和操作；
2. 添加独立单元测试；
3. 提供工具 schema 和 handler；
4. 在 bootstrap 注册；
5. 如有异步结果，提供 notification drain 函数。

除 `compact` 这类改变会话控制流的特殊 action 外，新增 feature 不修改
`core/loop.py`。

## 完成标准

- `homework/BaseAgent.py` 是薄 CLI 入口，不暴露内部实现。
- 现有能力按目标目录归属，不存在新的单文件总控模块。
- 模块导入无目录创建、client 创建和线程启动副作用。
- 所有可变运行时状态有明确所有者。
- Feature 不通过全局 RuntimeContext 单例互相访问。
- 工具通过 registry 和 bootstrap 注册。
- Agent Loop 不包含 feature 持久化和协议细节。
- 测试不访问 `agent_loop.__globals__`。
- 有效 BaseAgent 测试、核心集成测试和 CLI smoke test 全部通过。
- `uv run python homework/BaseAgent.py` 的交互入口保持可用。
