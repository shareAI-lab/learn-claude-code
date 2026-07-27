# BaseAgent s14/s16-s19 增量编码提示设计

## 背景

`homework/BaseAgent.py` 已经以累加方式整合了 s01-s13 和 s15 的主要能力，
但 s14 Cron Scheduler 尚未落地，s16 Team Protocols 只有未完成草稿，
s17-s19 尚未整合。用户希望自己完成编码，因此本次交付物是编码需求与实现
提示，而不是功能实现。

现有 `homework/REQUIREMENTS_s11_s15.md` 已经详细定义 s14。本次文档应复用
该规范，避免产生第二套相互冲突的 Cron 要求。

## 目标

新增 `homework/REQUIREMENTS_s14_s19_INCREMENTAL.md`，把以下课程内容转换为
可以逐步执行的增量编码提示：

1. s14 Cron Scheduler
2. s16 Team Protocols
3. s17 Autonomous Agents
4. s18 Worktree Isolation
5. s19 MCP Tools

文档还应在最后对比目标状态与 `s20_comprehensive/code.py`，识别
`BaseAgent.py` 中除必要安全、并发和正确性措施以外的功能冗余。

## 非目标

- 不修改 `homework/BaseAgent.py`。
- 不替用户实现 s14 或 s16-s19。
- 不复制课程代码形成可直接粘贴的完整答案。
- 不把 s20 的简化 `agent_loop()` 覆盖到 BaseAgent。
- 不要求实现真实 MCP transport、OAuth、分布式锁或自动合并 worktree。
- 不把已有未提交修改还原、覆盖或格式化。

## 交付结构

### 1. 使用方式与全局约束

开篇说明这是一份按顺序执行的编码指南。每完成一个阶段，都必须运行该阶段
新增测试和此前所有 BaseAgent 回归测试。

全局约束包括：

- 保持 s01-s15 已有能力累加存在。
- 所有 LLM 路径继续使用既有错误恢复、上下文压缩、记忆、动态 prompt 和
  tool-use/tool-result 配对规则。
- teammate、background、cron 和用户输入不能并发写同一份主 history。
- 新线程必须是 daemon 或具有可测试的停止机制。
- 共享字典、队列和文件的读改写必须受锁保护。
- 新工具必须同时接入工具 schema、handler、动态工具目录和权限/hook 管线。
- 测试不得调用真实 API、真实远程 MCP 服务或修改开发者已有 worktree。

### 2. 编码前基线检查

提示用户先运行现有测试并审查当前 s16 草稿。文档应明确指出当前草稿中需要
测试驱动修复的已知不一致：

- `ProtocolState.requested_id` 与课程接口 `request_id` 不一致。
- `match_resposne` 拼写错误，应统一为 `match_response`。
- `MessageBus.send()` 的消息类型白名单不包含新增协议类型。
- teammate inbox 分支检查了错误的 plan 消息方向。
- `consume_lead_inbox()` 与 `collect_lead_inbox()` 会竞争消费同一邮箱。
- 协议工具还没有完整加入 tool schemas 和 handlers。
- 文件中存在重复的 `agent_loop` 声明。

这些项目属于开始增量功能前的兼容性基线，不提供直接修复代码。

### 3. 每章固定模板

每个阶段使用相同结构：

1. **目标**：本阶段新增的可观察行为。
2. **与现有 BaseAgent 的连接点**：应修改或复用的现有状态、函数和循环位置。
3. **必须实现**：数据结构、函数、工具 schema、handler 和 prompt 状态。
4. **实现提示**：控制流、锁边界、错误处理和常见错误。
5. **不要照搬的简化**：指出课程 demo 中不能覆盖 BaseAgent 完整能力的部分。
6. **TDD 顺序**：列出由小到大的失败测试及预期行为，不给完整实现答案。
7. **手动验证 prompt**：给出可在 BaseAgent CLI 中输入的操作提示。
8. **完成标准**：可逐项勾选的验收清单。

## 各阶段设计

### s14：Cron Scheduler

以 `homework/REQUIREMENTS_s11_s15.md` 的 s14 章节为权威规范。本增量文档只
提供执行顺序和集成导航：

- 先完成 cron 字段校验与匹配纯函数。
- 再实现 durable job 存取和同一分钟去重。
- 再实现 scheduler producer，不允许在线程中调用 LLM。
- 最后实现统一 agent turn 锁和空闲交付。

测试重点是五字段语法、DOM/DOW OR 语义、跨日期 minute marker、one-shot、
损坏持久化记录、import 不启动线程，以及用户 turn 与 cron turn 的单 history
写入者约束。

### s16：Team Protocols

在现有 MessageBus 与 teammate permission handoff 上增加通用 request-response
协议，不另起第二套邮箱系统。

必须覆盖：

- `ProtocolState`、唯一 `request_id`、`pending_requests` 和状态迁移。
- shutdown request/response。
- plan approval request/response。
- 重复响应、未知 ID 和响应类型不匹配的拒绝。
- teammate WORK/IDLE 两种状态中的协议分发。
- Lead 的单一 inbox consumer，同时路由 permission 和 protocol 消息。

计划审批的教学版默认只演示协议，不声称已经实现强制执行门控。文档应明确：
若用户选择实现门控，必须作为额外挑战单独测试，不能仅依赖 prompt 自觉等待。

### s17：Autonomous Agents

在 s16 生命周期上增加任务板轮询和自动认领：

- `scan_unclaimed_tasks()` 只返回 pending、无 owner、依赖已完成的任务。
- `idle_poll()` 优先处理 inbox，再扫描任务板。
- teammate 生命周期为 WORK → IDLE → WORK/SHUTDOWN。
- teammate 获得 list/claim/complete task 工具。
- 压缩后应通过稳定 system prompt 或显式身份重注入保持身份。

并发认领是本阶段的正确性边界。文档不接受只在锁外检查 owner；应提示用户
让 `claim_task()` 的读、校验、修改和保存处于同一锁或等价原子临界区。

### s18：Worktree Isolation

在 Task 中增加可选 `worktree` 字段，并让 teammate 工具显式接收其当前 cwd：

- worktree 名称白名单和路径边界。
- create/bind/keep/remove 生命周期。
- 绑定 worktree 不隐式 claim 或 complete task。
- teammate claim 后更新自身 cwd；complete 后清理 cwd。
- bash/read/write/edit/glob 使用 teammate cwd，同时保留 hook 与权限流程。
- 删除前检查未提交修改和本地提交；默认拒绝丢弃工作。
- 生命周期事件只在 Git 操作成功后写入。

课程代码中的强制删除只能作为显式 `discard_changes=true` 的最终路径，不能成为
默认行为。

### s19：MCP Tools

实现教学版 late-bound MCP 工具池：

- `MCPClient` 的 discover/register/call 抽象。
- mock server factory 和连接注册表。
- `normalize_mcp_name()`。
- `mcp__server__tool` 命名空间。
- `assemble_tool_pool()` 每轮合并 builtin schema/handler 与已连接 MCP 工具。
- `connect_mcp` 后下一轮立即刷新工具池和 system prompt。

动态 MCP handler 必须正确绑定 server/client/tool，避免循环 lambda 的 late
binding 错误。名称规范化后发生冲突时应拒绝或给出确定性处理，不能静默覆盖。

MCP 工具和内置工具必须经过同一 PreToolUse/PostToolUse 分发管线。read-only
和 destructive annotation 不能只作为 description 文案；破坏性工具至少要
映射到现有确认流程。真实 transport、OAuth 和配置优先级只作为扩展阅读。

## 跨阶段集成检查

文档末尾提供一条完整测试路径：

1. 创建带依赖关系的任务。
2. 为可并行任务创建并绑定不同 worktree。
3. 启动两个 teammate，让其自动认领。
4. teammate 提交计划，Lead 审批后继续工作。
5. teammate 完成任务并进入 IDLE。
6. Lead 使用结构化 shutdown 协议结束 teammate。
7. 注册 one-shot cron，让其在主 Agent 空闲时产生工作。
8. 连接 mock MCP server，确认下一轮出现动态工具并经过 hook。

该路径只用于手动集成验证；自动测试仍应分别 stub 时间、线程、LLM、Git 和 MCP。

## s20 冗余分析方法

冗余分析以“目标 BaseAgent 已完成 s14/s16-s19”为前提，分三类报告，避免把
增强功能与死代码混为一谈。

### A. 真正冗余

满足以下任一条件：

- 重复声明或存在两个竞争入口。
- 无调用方的函数、常量或状态。
- 同一信息通过两个渠道重复注入模型。
- 同一事件被两个 consumer 竞争消费。
- 新动态工具池建立后仍保留一套不会更新的静态分发源。

当前应重点核查重复 `agent_loop`、两个 Lead inbox consumer、
`build_memory_system()`、`print_response_text()`、`MAX_REACTIVE_RETRIES`，
以及 memory index 与 relevant memories 的重复注入。

### B. 超出 s20 教学基线但可保留

这类能力不是 s20 的核心教学实现，但可能对实际使用有价值：

- 流式输出及 partial-stream continuation。
- LLM 驱动的记忆选择、提取和 consolidation。
- 会话 todo 的磁盘恢复。
- 比 s20 更高的 retry/continuation 上限和更细错误分类。
- 更丰富的 transcript、大结果落盘和可观测日志。
- system prompt 稳定键缓存。

报告应说明成本、收益和建议保留场景，不能直接称为死代码。

### C. 不得按冗余删除

以下即使 s20 教学代码更简单，也属于必要安全、并发或协议正确性：

- workspace、mailbox、worktree 名称和路径验证。
- destructive command/MCP 权限确认和 diff preview。
- teammate guarded tool permission handoff。
- tool_use/tool_result 成对修复。
- task claim、mailbox、cron queue、history 和共享 registry 的锁。
- durable 文件的原子写入与损坏恢复。
- 后台线程停止、超时和 daemon 约束。

最终结论应给出“删除、合并、可选保留、必须保留”四种建议，而不是简单列出
BaseAgent 比 s20 多出的所有函数。

## 文档验证

制作完成后执行以下静态检查：

- 所有五个阶段均包含固定模板的八个部分。
- 每个新增工具同时提到 schema、handler、prompt/catalog 和 hook。
- s14 要求与既有需求文档无冲突。
- s16 不会绕过 permission 消息。
- s17 claim 原子性被明确要求。
- s18 destructive cleanup 默认拒绝。
- s19 动态工具经过统一权限分发。
- 所有手动 prompt 都能对应一个明确可观察结果。
- 冗余分析使用四类建议，并排除必要安全措施。

## 成功标准

- 用户能按文档逐阶段自行编码，不需要从课程 demo 猜测集成位置。
- 文档强调增量整合，不会诱导用户用后续课程的简化循环覆盖已有能力。
- 每阶段都有先失败后通过的测试提示和手动操作提示。
- s20 对比能区分真正重复、可选增强和不可删除的安全/正确性措施。
- 本次交付不改变 BaseAgent 的运行行为。
