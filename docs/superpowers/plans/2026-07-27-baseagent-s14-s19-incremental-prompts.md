# BaseAgent s14/s16-s19 增量编码提示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一份不修改 BaseAgent 实现、但足以指导用户按 TDD 自行整合 s14 与 s16-s19 的增量编码文档，并给出基于 s20 的冗余审计结论。

**Architecture:** 最终交付是单文件 `homework/REQUIREMENTS_s14_s19_INCREMENTAL.md`。文档先固定跨阶段不变量和当前基线问题，再按 s14、s16、s17、s18、s19 顺序提供统一格式的编码提示，最后加入集成场景和按“删除/合并/可选保留/必须保留”分类的 s20 对比。

**Tech Stack:** Markdown、Python 3.13、pytest、Anthropic Messages API 教学接口、标准库 threading/datetime/subprocess/pathlib/json。

## Global Constraints

- 不修改 `homework/BaseAgent.py`、现有测试或课程示例。
- 保留工作区所有已有未提交修改，不执行 reset、checkout 或清理。
- `homework/REQUIREMENTS_s11_s15.md` 的 s14 章节是 Cron 行为的权威来源。
- 后续课程示例中的简化 Agent Loop 只能作为机制参考，不能覆盖 BaseAgent 已有 s01-s15 能力。
- 文档提供接口、控制流、边界条件、测试顺序和手动 prompt，但不提供可直接粘贴的完整实现。
- 所有新增工具提示必须同时覆盖 tool schema、handler、动态 prompt/catalog 和 hook/permission 分发。
- 并发、路径、权限、协议配对和 durable 状态措施不得在冗余分析中建议删除。
- 自动化测试提示不得依赖真实 LLM、真实远程 MCP、实际等待一分钟或开发者已有 Git worktree。

---

### Task 1: 建立文档骨架、使用方式与基线检查

**Files:**
- Create: `homework/REQUIREMENTS_s14_s19_INCREMENTAL.md`
- Reference: `docs/superpowers/specs/2026-07-27-baseagent-s14-s19-incremental-prompts-design.md`
- Reference: `homework/BaseAgent.py`

**Interfaces:**
- Consumes: 已确认设计中的固定章节模板和当前 BaseAgent 静态检查结果。
- Produces: 最终文档标题、适用基线、全局不变量、建议执行循环和编码前检查清单，供后续五章共同引用。

- [ ] **Step 1: 运行缺失文件检查，确认交付物尚未存在**

Run:

```bash
test -f homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: exit code `1`，证明检查能捕获缺失交付物。

- [ ] **Step 2: 创建标题和使用说明**

文档开头必须明确：

```markdown
# BaseAgent s14/s16-s19 增量编码指南

## 这份文档怎么用

本指南不提供完整答案代码。请严格按 s14 → s16 → s17 → s18 → s19
的顺序工作：先写一个会因目标能力缺失而失败的测试，确认失败原因正确，
再写最小实现使其通过，最后运行全部 BaseAgent 回归测试。
```

紧接着写明每阶段循环：

```text
读本阶段目标
  → 写一个最小失败测试
  → 确认因功能缺失而失败
  → 写最小实现
  → 运行本阶段测试
  → 运行所有既有 BaseAgent 测试
  → 执行手动 prompt
  → 进入下一阶段
```

- [ ] **Step 3: 写入不可破坏的全局不变量**

必须逐条说明：

- 主 Agent、同步 subagent、background worker、teammate 和 cron 产生的工作都继续经过各自既有的权限边界。
- Anthropic `tool_use` 必须有对应 `tool_result`，包括被拒绝、未知工具、后台占位和 token 截断场景。
- 后续章节不得删除 streaming、error recovery、compaction、memory、skills、todo、task graph、hooks 或动态 prompt。
- 主 history 只有一个写入者；用户 turn 与自动 turn 通过同一 `agent_lock` 和统一入口串行化。
- mailbox、task、cron、protocol、MCP registry 等共享状态有明确锁边界。
- 模块 import 不启动不可控后台线程；runtime 启动发生在 `main()` 或显式启动函数。
- 测试通过 `tmp_path`、stub client、fake clock、fake subprocess 和可控 stop event 隔离外部状态。

- [ ] **Step 4: 写入当前 BaseAgent 的编码前基线检查**

明确让用户先为以下问题写测试或静态断言：

1. `ProtocolState.requested_id` 应统一成 `request_id`。
2. `match_resposne` 应统一成 `match_response`。
3. `MessageBus.send()` 当前白名单会拒绝 shutdown/plan 协议消息。
4. teammate 当前把 plan 消息方向判断成 request，而实际需要消费 response。
5. `consume_lead_inbox()` 和 `collect_lead_inbox()` 会竞争读取并清空 Lead mailbox。
6. `request_shutdown`、`request_plan`、`review_plan` 尚未完整进入 schemas/handlers。
7. 当前文件存在重复的 `agent_loop` 声明。

为基线提供验证命令：

```bash
.venv/bin/python -m py_compile homework/BaseAgent.py
.venv/bin/python -m pytest -p no:cacheprovider tests/test_homework_baseagent_agent_teams.py -q
```

预期说明必须是：记录真实结果；若失败，先判断是否为上述现有草稿问题，不要在同一提交中顺手重构无关系统。

- [ ] **Step 5: 添加五章、集成验证和最终审计入口**

依次追加以下顶层章节；每个标题下写一行范围说明，后续任务再扩展为完整八段模板：

```markdown
## s14：Cron Scheduler

本章按既有 s14 权威需求实现调度生产、队列交付和 durable job。

## s16：Team Protocols

本章在现有 permission handoff 上增加结构化 request-response 协议。

## s17：Autonomous Agents

本章让 teammate 在 IDLE 阶段自动发现并原子认领可执行任务。

## s18：Worktree Isolation

本章把 task、teammate cwd 与 Git worktree 生命周期连接起来。

## s19：MCP Tools

本章把 mock MCP server 发现的工具增量加入主 Agent 动态工具池。

## 跨阶段集成验证

本章组合验证 cron、protocol、autonomy、worktree 和 MCP 的交互边界。

## 与 s20 的功能冗余对比

本章区分真正冗余、重复职责、可选增强和不可删除的必要措施。
```

- [ ] **Step 6: 确认骨架包含五章与最终审计入口**

Run:

```bash
rg -n '^## (s14|s16|s17|s18|s19|跨阶段集成验证|与 s20 的功能冗余对比)' homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: 此时只能看到稍后需要填写的章节入口；不存在拼写不同的重复章节。

- [ ] **Step 7: 提交文档骨架**

```bash
git add homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
git commit -m "docs: scaffold BaseAgent incremental coding guide"
```

### Task 2: 编写 s14 Cron 与 s16 Team Protocols 提示

**Files:**
- Modify: `homework/REQUIREMENTS_s14_s19_INCREMENTAL.md`
- Reference: `homework/REQUIREMENTS_s11_s15.md:690`
- Reference: `s14_cron_scheduler/code.py`
- Reference: `s16_team_protocols/code.py`
- Reference: `tests/test_homework_baseagent_agent_teams.py`

**Interfaces:**
- Consumes: BaseAgent 的 background/task/team/message bus/error recovery/agent loop。
- Produces: s14 的调度事件入口，以及 s16 的统一 Lead/teammate 协议路由；s17 将依赖 s16 的 WORK/IDLE 分发边界。

- [ ] **Step 1: 写结构失败检查**

Run:

```bash
rg -c '^### (目标|与现有 BaseAgent 的连接点|必须实现|实现提示|不要照搬的简化|TDD 顺序|手动验证 prompt|完成标准)$' homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: count 小于 `16`，因为 s14 和 s16 的两组八段模板尚未完整。

- [ ] **Step 2: 编写 s14 的八段提示**

必须包含以下实际要求：

**目标**

- 接受标准五字段 cron。
- 每个 job 每分钟最多触发一次。
- scheduler 只生产事件，不能调用 LLM。
- durable job 可恢复，session-only job 不落盘。
- Agent 空闲时由统一入口交付 `[Scheduled:<job_id>]`。

**连接点**

- `agent_loop()` 开始处的 background/team 注入区域。
- `run_agent_turn()` 或替代的统一 turn 入口。
- `TOOLS`/`TOOL_HANDLERS`，后续 s19 会将其改称 builtin pool。
- 动态 `update_context()` 与 system prompt 中的本地时区说明。

**必须实现**

- `CronJob`、`scheduled_jobs`、`cron_queue`、`cron_lock`、`agent_lock`、`_last_fired`。
- `_cron_field_matches`、`cron_matches`、`validate_cron`、durable load/save、schedule/cancel/consume。
- `schedule_cron`、`list_crons`、`cancel_cron` 三个 schema 和 handler。
- `start_runtime_threads(stop_event=None)`，防重复启动。

**实现提示**

- DOM/DOW 使用标准 OR 语义。
- minute marker 使用 `%Y-%m-%d %H:%M`。
- durable 文件原子 replace；逐条跳过损坏 job。
- one-shot 成功入队后移除；取消和移除都同步 durable 文件。
- queue consumer 获得 `agent_lock` 后再次检查队列。

**不要照搬**

- 不采用课程 s14 的简化 LLM 调用。
- 不在 import 时启动线程。
- 不让 cron、用户输入和 teammate 并发修改 history。

**TDD 顺序**

1. wildcard/number/step/list/range 字段匹配。
2. 非法字段数、越界、倒序范围、零步长。
3. DOM/DOW OR。
4. 同分钟去重和跨日期重新触发。
5. one-shot 与 recurring。
6. durable/session-only 和损坏 JSON。
7. scheduler 不调用 LLM。
8. import 不启动线程。
9. cron turn 与用户 turn 串行。

**手动 prompt**

```text
请创建一个只执行一次的定时任务，在下一分钟检查当前目录并总结 Python 文件；列出任务后告诉我它使用的本地时区。
```

```text
请注册一个每 5 分钟运行的持久任务，然后取消它，并确认 durable 列表中已经不存在。
```

**完成标准**

列出上述目标的逐项勾选项，并要求运行全部五个现有 BaseAgent 测试文件。

- [ ] **Step 3: 编写 s16 的八段提示**

必须包含以下实际要求：

**目标**

- shutdown 与 plan approval 使用结构化 request/response。
- response 通过 `request_id` 与原请求关联。
- teammate 完成一次工作后进入可唤醒 IDLE，而不是立即消失。
- permission request/response 与新协议共享一个 mailbox router。

**连接点**

- 保留 `MessageBus`、`validate_agent_name`、`mailbox_lock`、`team_lock`。
- 合并 `consume_lead_inbox` 和 `collect_lead_inbox` 为单一消费入口。
- 保留 `process_permission_request()`，把它作为 router 的一种消息分支。
- teammate 的 guarded tools 仍等待 permission response。

**必须实现**

- `ProtocolState(request_id, type, sender, target, status, payload, created_at)`。
- `new_request_id()` 使用 `uuid.uuid4().hex` 或带碰撞检测的生成方式。
- `match_response()` 返回可测试结果，而不是只打印。
- `_teammate_submit_plan`、`run_request_shutdown`、`run_request_plan`、`run_review_plan`。
- Lead schemas/handlers 和 teammate 的 `submit_plan` schema/handler。
- 明确的消息类型集合或 request→expected response 映射。

**实现提示**

- 状态只允许 pending → approved/rejected。
- unknown ID、type mismatch、duplicate response 都不得改状态。
- Lead router 顺序：permission request → protocol response → ordinary message。
- teammate router 顺序：permission response → shutdown request → plan approval response → ordinary message。
- 被某个 waiter 暂存的非目标消息必须进入 deferred inbox，不能丢失。

**不要照搬**

- 课程代码的随机六位 request ID 不足以避免碰撞。
- 课程计划审批只演示协议，不等于代码门控。
- 不用第二个 `BUS.read_inbox("lead")` 绕过统一 router。
- 不用新的简化 teammate LLM loop 替换现有 recovery 和 guarded tools。

**TDD 顺序**

1. MessageBus 接受并持久化 metadata 和协议类型。
2. request ID 唯一且字段命名一致。
3. 正确 response 更新状态。
4. wrong type/unknown/duplicate 不更新。
5. permission 与 protocol 同批消息都被正确路由。
6. shutdown 在 WORK 与 IDLE 都能响应。
7. plan approve/reject 注入 teammate history。
8. schema 与 handler 一一对应。

**手动 prompt**

```text
启动 alice 作为后端队友，请她先提交实施计划。收到计划后先拒绝并给出反馈，让她重新提交；第二次批准，完成后请求她优雅退出。
```

**完成标准**

必须包括“Lead mailbox 只有一个消费者”和“permission handoff 回归测试仍通过”。

- [ ] **Step 4: 验证 s14/s16 模板和关键术语**

Run:

```bash
rg -n 'DOM/DOW|agent_lock|request_id|permission_request|单一.*(consumer|消费)' homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: 每个关键词至少有一个要求和一个测试/完成标准上下文。

- [ ] **Step 5: 提交 s14/s16 提示**

```bash
git add homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
git commit -m "docs: add cron and team protocol coding prompts"
```

### Task 3: 编写 s17 Autonomous Agents 与 s18 Worktree Isolation 提示

**Files:**
- Modify: `homework/REQUIREMENTS_s14_s19_INCREMENTAL.md`
- Reference: `s17_autonomous_agents/code.py`
- Reference: `s18_worktree_isolation/code.py`
- Reference: `tests/test_homework_baseagent_task_system.py`
- Reference: `tests/test_homework_baseagent_agent_teams.py`

**Interfaces:**
- Consumes: s12 Task、s15 Team、s16 protocol/IDLE。
- Produces: 可自动认领任务的 teammate，以及按 teammate 隔离的 cwd；s19 只扩展 Lead 工具池，不应破坏这些子工具边界。

- [ ] **Step 1: 写结构失败检查**

Run:

```bash
rg -c '^### (目标|与现有 BaseAgent 的连接点|必须实现|实现提示|不要照搬的简化|TDD 顺序|手动验证 prompt|完成标准)$' homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: count 小于 `32`，因为 s17/s18 的八段模板尚未全部完成。

- [ ] **Step 2: 编写 s17 的八段提示**

必须覆盖：

- `scan_unclaimed_tasks()` 只返回 pending、owner 为空、`can_start()` 为真的任务。
- `idle_poll()` 先 inbox 后 task board，返回 `work|shutdown|timeout`。
- teammate 外层 WORK→IDLE 循环和每个 WORK 阶段的有限 LLM 轮数。
- teammate 的 list/claim/complete schemas 和按 teammate name 认领的 handlers。
- `claim_task()` 在 task lock 内完成 load/check owner/check deps/save。
- claim 失败后继续扫描或等待，不把字符串包含判断当成唯一成功信号；推荐结构化结果或重新读取确认。
- identity 保持通过 teammate system prompt；若压缩会删除身份，再显式重注入。

TDD 顺序必须包含：

1. 过滤 blocked/owned/completed task。
2. inbox 优先于 task board。
3. IDLE shutdown 立即响应。
4. 自动 claim 后回到 WORK。
5. 两线程同时 claim 只有一个成功。
6. complete 后下游 task 可被扫描。
7. timeout 使用 fake clock，不真实等待 60 秒。

手动 prompt：

```text
创建三个任务：A 无依赖，B 依赖 A，C 无依赖。启动 alice 和 bob，让他们自行认领；确认 B 只在 A 完成后出现，并在两位队友空闲后请求关闭。
```

- [ ] **Step 3: 编写 s18 的八段提示**

必须覆盖：

- `Task.worktree: str | None = None` 对旧 JSON 向后兼容。
- `WORKTREES_DIR`、严格名称校验和 `run_git(args)`。
- create/bind/keep/remove 和 append-only event log。
- 创建失败不得绑定 task 或记事件。
- 绑定只写 worktree，不修改 task 状态/owner。
- teammate 使用私有 `wt_ctx`；claim 成功后设置，complete 后清空。
- bash/read/write/edit/glob 都接收 cwd；`safe_path` 以该 cwd 为边界。
- teammate cwd 工具仍走原有 permission、diff preview、PostToolUse。
- remove 默认检查 uncommitted changes 和相对基线分支的本地提交；检查失败时 fail closed。
- `discard_changes=true` 仍需经过 destructive permission。

TDD 顺序必须包含：

1. name 为空、`.`、`..`、斜杠、超长时拒绝。
2. create 的 Git 参数、成功绑定和失败回滚。
3. 旧 Task JSON 无 worktree 时可加载。
4. bind 保持 pending。
5. teammate claim 设置 cwd，各队友 cwd 相互独立。
6. 所有文件工具不能逃出 worktree。
7. dirty/committed worktree 默认拒绝删除。
8. 显式 discard 且获批才允许强制删除。
9. 只有成功操作写 event。

手动 prompt：

```text
创建 backend 和 frontend 两个任务，为它们分别建立并绑定 worktree，然后启动 alice 和 bob 自行认领。让两人各自创建同名 status.txt，最后比较两个 worktree 的内容和分支。
```

```text
尝试删除仍有改动的 backend worktree，但不要丢弃修改；确认系统拒绝删除并建议 keep_worktree。
```

- [ ] **Step 4: 验证 s17/s18 的并发与安全边界**

Run:

```bash
rg -n '原子|task lock|fake clock|wt_ctx|fail closed|discard_changes|PostToolUse' homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: 能定位 claim 临界区、可控 idle 测试、teammate cwd、默认拒绝删除和 hook 保留要求。

- [ ] **Step 5: 提交 s17/s18 提示**

```bash
git add homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
git commit -m "docs: add autonomous agent and worktree prompts"
```

### Task 4: 编写 s19 MCP 提示和跨阶段集成场景

**Files:**
- Modify: `homework/REQUIREMENTS_s14_s19_INCREMENTAL.md`
- Reference: `s19_mcp_plugin/code.py`
- Reference: `s20_comprehensive/code.py`

**Interfaces:**
- Consumes: 固定 `TOOLS`/`TOOL_HANDLERS`、动态 system prompt、Pre/PostToolUse hooks。
- Produces: `assemble_tool_pool() -> tuple[list[dict], dict[str, callable]]`，供主 Agent 每次 LLM 请求和工具执行共同使用。

- [ ] **Step 1: 写动态工具池失败检查**

Run:

```bash
rg -n 'assemble_tool_pool|mcp__server__tool|名称冲突|late binding' homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: exit code `1` 或缺少其中至少一项，证明 s19 关键内容尚未完成。

- [ ] **Step 2: 编写 s19 的八段提示**

必须覆盖：

- `MCPClient` 保存原始 server 名、tool definitions 和 handlers。
- `register/discover_tools/call_tool` 的教学接口。
- `mcp_clients` registry、mock factories 和 `connect_mcp`。
- `normalize_mcp_name` 将非 `[A-Za-z0-9_-]` 字符替换为 `_`。
- schema 的 `inputSchema` 转成 Anthropic `input_schema`。
- `assemble_tool_pool()` 从不可变 builtin 副本开始，逐个加入 prefixed MCP 工具。
- lambda/default argument 或 `functools.partial` 固定 client 和原始 tool name。
- 规范化后重复名称必须返回明确错误，不能覆盖 builtin 或其他 MCP handler。
- 每轮 LLM 前重建 pool，或者让 cache key 包含稳定的 MCP server/tool fingerprint。
- `create_message_streaming()` 接收本轮动态 tools，不能继续读全局静态 `TOOLS`。
- MCP handler 与 builtin handler 走同一 execute/PreToolUse/PostToolUse/background 分发。
- destructive annotation 映射到现有确认机制；annotation 缺失时不把工具自动视为安全。
- MCP 工具默认只给 Lead，除非用户明确选择并测试 teammate 继承策略。

TDD 顺序必须包含：

1. 名称规范化。
2. mock server 连接与重复连接。
3. 两个 server 的同名工具不冲突。
4. 规范化碰撞被拒绝。
5. 动态 handler 调到正确 client/tool，覆盖 late binding。
6. connect 后下一轮 schema 和 prompt 可见。
7. streaming request 使用动态 pool。
8. read-only 工具通过，destructive 工具触发 permission。
9. MCP 异常成为对应 `tool_result`，不破坏配对。

手动 prompt：

```text
连接 docs MCP server，列出新发现的完整工具名，然后调用搜索工具查询 context compaction。
```

```text
连接 deploy MCP server 并尝试触发部署；在没有明确确认前不要执行破坏性工具。
```

- [ ] **Step 3: 编写跨阶段集成验证**

完整场景必须按以下顺序：

1. 创建 A、B、C 三个 task，B blockedBy A。
2. 为 A 和 C 创建两个 worktree 并绑定。
3. 启动 alice/bob，使其自动认领。
4. 至少一个 teammate 通过 submit_plan 请求审批。
5. Lead reject 一次、approve 一次。
6. teammate 在自己的 cwd 工作并 complete task。
7. teammate 进入 IDLE 后由 shutdown request 结束。
8. 注册 one-shot cron，在 Agent 空闲时产生 `[Scheduled:<id>]`。
9. 连接 docs MCP，确认下轮 tool pool 出现 prefixed tool。
10. 调用一个 read-only MCP tool，并验证其仍经过日志 hook。

文档要注明：这是人工 smoke flow；自动化测试应分层 stub，不将整条线程链路做成脆弱的实时测试。

- [ ] **Step 4: 验证动态工具池同时接入 schema、handler、prompt 和 hook**

Run:

```bash
rg -n 'input_schema|handler|system prompt|PreToolUse|PostToolUse|create_message_streaming' homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: s19 章节中六项均出现，并说明同一个本轮 tool pool 是唯一来源。

- [ ] **Step 5: 提交 s19 和集成场景**

```bash
git add homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
git commit -m "docs: add MCP and integration coding prompts"
```

### Task 5: 编写与 s20 的冗余审计

**Files:**
- Modify: `homework/REQUIREMENTS_s14_s19_INCREMENTAL.md`
- Reference: `homework/BaseAgent.py`
- Reference: `s20_comprehensive/code.py`
- Reference: `s20_comprehensive/README.md`

**Interfaces:**
- Consumes: 假设 s14/s16-s19 均已按前文整合后的目标 BaseAgent。
- Produces: 四类处置建议：删除、合并、可选保留、必须保留。

- [ ] **Step 1: 写审计分类失败检查**

Run:

```bash
rg -n '^### (建议删除|建议合并|可选保留|必须保留)' homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: exit code `1` 或少于四个结果。

- [ ] **Step 2: 写入“建议删除”的真实死代码**

逐项说明证据和删除条件：

- 重复的第一个 `agent_loop` 声明：只有 `global rounds_since_todo`，随后立即被同名函数覆盖。
- `build_memory_system()`：当前无调用方，实际 system prompt 由 `assemble_system_prompt()` 构建。
- `print_response_text()`：当前 main/streaming 路径无调用方。
- `MAX_REACTIVE_RETRIES`：当前无读取方，真实限制使用 `MAX_REACTIVE_COMPACTS`。
- 完成 s16 统一 router 后残留的第二个 Lead inbox consumer。
- 完成 s19 动态 pool 后残留且仍被 streaming path 读取的静态工具源。

文档必须注明：删除前再次用 `rg` 验证引用，因为用户整合过程中可能已经给这些符号新增调用方。

- [ ] **Step 3: 写入“建议合并”的重复职责**

必须分析：

- `consume_lead_inbox()` 与 `collect_lead_inbox()` 合并成单一 router。
- memory index 已在 system prompt 中暴露，同时 relevant memory 正文又注入最新 user message；保留“目录 + 相关正文”是合理的，但禁止把同一完整正文两次注入。
- `TOOLS`/`TOOL_HANDLERS` 与 `BUILTIN_TOOLS`/`BUILTIN_HANDLERS` 只保留一套 canonical builtin registry。
- cron autorun、用户输入和 teammate/background 通知统一到一个 locked turn/event delivery 入口。
- teammate WORK 和 IDLE 中重复的协议 dispatch 合并为共享 `handle_inbox_message()`。

- [ ] **Step 4: 写入“可选保留”的超出 s20 教学基线能力**

用“收益 / 成本 / 建议场景”说明：

- streaming + partial stream continuation。
- LLM 选择、抽取和 consolidation memory。
- `.todo.json` 会话恢复。
- 细分 429/529/prompt-too-long 和更高 continuation 上限。
- transcript、大结果落盘和详细观测日志。
- system prompt 稳定键缓存。

明确这些不是“功能错误”，只是相对 s20 教学目标的复杂度增量。

- [ ] **Step 5: 写入“必须保留”的非冗余安全与正确性**

列出：

- workspace/mailbox/worktree/task ID 的路径与名称校验。
- destructive bash/MCP permission 和 write/edit diff preview。
- teammate guarded tool → Lead permission handoff。
- tool_use/tool_result 配对修复。
- task claim/mailbox/cron/history/MCP registry 的锁。
- durable 状态原子写、损坏恢复。
- thread daemon/stop event/timeout。
- worktree dirty 检查与默认拒绝 discard。

同时解释：s20 为教学可读性省略某些强化措施，不能据此认定它们冗余。

- [ ] **Step 6: 加入决策摘要表**

表格列必须是：

```markdown
| 项目 | 与 s20 的差异 | 判断 | 建议 |
| --- | --- | --- | --- |
```

至少覆盖上述四类中的每个条目，并让每行判断使用：

```text
真冗余 / 重复职责 / 可选增强 / 必要措施
```

- [ ] **Step 7: 提交冗余审计**

```bash
git add homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
git commit -m "docs: audit BaseAgent redundancy against s20"
```

### Task 6: 全文静态验证与最终交付

**Files:**
- Modify if validation finds issues: `homework/REQUIREMENTS_s14_s19_INCREMENTAL.md`
- Verify: `homework/REQUIREMENTS_s14_s19_INCREMENTAL.md`
- Verify unchanged: `homework/BaseAgent.py`

**Interfaces:**
- Consumes: Tasks 1-5 的完整文档。
- Produces: 无占位符、五章结构完整、约束一致且未触碰实现文件的最终交付。

- [ ] **Step 1: 验证五章均有八段模板**

Run:

```bash
rg -c '^### (目标|与现有 BaseAgent 的连接点|必须实现|实现提示|不要照搬的简化|TDD 顺序|手动验证 prompt|完成标准)$' homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: `40`。

- [ ] **Step 2: 扫描占位符和模糊指令**

Run:

```bash
rg -n 'TBD|TODO|待定|稍后实现|类似上文|适当处理|酌情处理' homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: exit code `1`，没有匹配。

- [ ] **Step 3: 验证各阶段核心不变量**

Run:

```bash
rg -n 'scheduler.*不能.*LLM|单一.*(consumer|消费)|读.*校验.*修改.*保存|discard_changes=true|mcp__.*__|动态.*tool|tool_use.*tool_result' homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: 至少分别定位 s14、s16、s17、s18、s19 和全局约束中的对应要求。

- [ ] **Step 4: 验证冗余审计四类结论**

Run:

```bash
rg -n '^### (建议删除|建议合并|可选保留|必须保留)' homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
```

Expected: 恰好四行。

- [ ] **Step 5: 验证没有意外修改实现文件**

Run:

```bash
git diff -- homework/BaseAgent.py
```

Expected: 只显示用户原本已有的未提交修改；本计划执行期间没有新增 BaseAgent diff。用执行前记录的 diff hash 或 `git diff --numstat` 对比确认，而不是假设空输出。

- [ ] **Step 6: 验证 Markdown 与工作区差异**

Run:

```bash
git diff --check -- homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
git status --short
```

Expected: `git diff --check` exit code `0`；status 中本次范围只涉及增量指南，其他脏文件保持原状。

- [ ] **Step 7: 提交验证修正（仅在 Step 1-6 产生修正时）**

```bash
git add homework/REQUIREMENTS_s14_s19_INCREMENTAL.md
git commit -m "docs: validate BaseAgent incremental coding guide"
```

- [ ] **Step 8: 最终交付**

向用户提供：

- 增量指南的可点击绝对路径。
- 五个阶段各自包含编码、TDD 和手动 prompt 的说明。
- s20 冗余分析的四类摘要。
- 明确声明 `homework/BaseAgent.py` 未被本次交付修改。
