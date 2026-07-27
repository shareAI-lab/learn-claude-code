# BaseAgent s14/s16-s19 增量编码指南

## 这份文档怎么用

本指南不提供完整答案代码。请严格按 s14 → s16 → s17 → s18 → s19
的顺序工作：先写一个会因目标能力缺失而失败的测试，确认失败原因正确，
再写最小实现使其通过，最后运行全部 BaseAgent 回归测试。

每个阶段都执行同一个循环：

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

课程后续章节为了突出当前主题，会删掉前面章节的完整实现。参考
`s14_cron_scheduler/code.py`、`s16_team_protocols/code.py` 到
`s19_mcp_plugin/code.py` 时，只提取本章新增机制，不要用其中的简化
`agent_loop()`、teammate loop 或 prompt 覆盖 `homework/BaseAgent.py`
已有能力。

## 适用基线

开始前，BaseAgent 应已经具备 s01-s13 和 s15 的主要能力：

- 基础 Agent Loop、流式输出和 `tool_use` / `tool_result` 配对。
- 文件、shell、glob、todo、task、skill 和同步 subagent 工具。
- 路径边界、危险命令确认、写入 diff 和 hooks。
- 上下文压缩、长期记忆、动态 system prompt。
- 429/529、`max_tokens`、prompt-too-long 和 partial stream 恢复。
- 持久化 task graph、后台工具调用和 teammate MessageBus。
- teammate 对 `bash`、`write_file` 的 Lead permission handoff。

若你的基线与此不同，先补齐 `homework/REQUIREMENTS_s06_s10.md` 和
`homework/REQUIREMENTS_s11_s15.md`，再执行本指南。

## 不可破坏的全局不变量

1. 主 Agent、同步 subagent、background worker、teammate 和 cron 产生的工作，
   都继续遵守各自已有的权限和路径边界。
2. 每个 Anthropic `tool_use` 都必须得到对应 `tool_result`。拒绝、未知工具、
   后台占位和 token 截断也不能破坏配对。
3. 不得删除 streaming、error recovery、compaction、memory、skills、todo、
   task graph、hooks 或动态 prompt 来换取后续章节“看起来能运行”。
4. 主 history 只有一个写入者。用户 turn 与自动 turn 必须通过同一个
   `agent_lock` 和统一入口串行执行。
5. mailbox、task、cron、protocol、MCP registry 等共享状态必须有明确锁边界；
   文件型状态的读、校验、修改和保存应处于同一临界区。
6. 模块 import 不得启动不可控线程。runtime 线程由 `main()` 调用显式启动函数，
   且必须是 daemon 或接受测试可控制的 `stop_event`。
7. 每个新增工具必须同时进入：

   - Anthropic tool schema；
   - 对应 handler；
   - 动态工具目录或 system prompt；
   - PreToolUse / PostToolUse / permission 分发。

8. 自动化测试不得调用真实 LLM、远程 MCP、真实等待一分钟，也不得修改开发者
   已有 Git worktree。使用 `tmp_path`、stub client、fake clock、
   fake subprocess 和可控 event。

## 编码前基线检查

当前工作副本中的 s16 草稿存在若干尚未闭合的接口。先用小测试或静态断言暴露
这些问题，不要等到 s17/s18 才一起调试：

1. `ProtocolState.requested_id` 应统一为课程与消息 metadata 使用的
   `request_id`。
2. `match_resposne` 拼写错误，应统一为 `match_response`，避免形成两套入口。
3. `MessageBus.send()` 的消息白名单当前不包含 shutdown 和 plan approval
   的 request/response 类型，新协议消息会在发送时被拒绝。
4. teammate inbox 草稿判断了错误的 plan 消息方向：teammate 应消费
   `plan_approval_response`，而不是把 `plan_approval_request` 当作审批结果。
5. `consume_lead_inbox()` 与 `collect_lead_inbox()` 都会读取并清空 Lead
   mailbox，会造成 permission 或 protocol 消息被另一个入口提前吞掉。
6. `request_shutdown`、`request_plan`、`review_plan` 和 teammate
   `submit_plan` 尚未全部进入 schemas 与 handlers。
7. 文件中存在重复的 `agent_loop` 声明；第一个同名声明没有独立功能。

先记录基线：

```bash
.venv/bin/python -m py_compile homework/BaseAgent.py
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/test_homework_baseagent_agent_teams.py -q
```

若失败，记录真实错误并先判断它是否属于上述草稿问题。一次只修复一个可观察
行为；不要把无关格式化或记忆系统重构混入协议提交。

## 建议的测试文件

为了让每一章的回归边界清楚，建议新增：

```text
tests/test_homework_baseagent_cron.py
tests/test_homework_baseagent_team_protocols.py
tests/test_homework_baseagent_autonomous_agents.py
tests/test_homework_baseagent_worktrees.py
tests/test_homework_baseagent_mcp.py
tests/test_homework_baseagent_s20_redundancy.py  # 只做静态/结构检查
```

测试加载 BaseAgent 时继续沿用仓库现有 stub `anthropic`、环境变量和临时目录
模式，不从测试进程导入后就自动启动 runtime 线程。

## s14：Cron Scheduler

本章按 `homework/REQUIREMENTS_s11_s15.md` 的 s14 章节实现调度生产、
队列交付和 durable job。既有文档是 cron 语义的权威来源；这里重点告诉你
以什么顺序写、接到 BaseAgent 的哪里，以及怎样证明没有破坏旧机制。

### 目标

实现一个独立的教学版 Cron Scheduler：

- 接受标准五字段 cron：`minute hour day-of-month month day-of-week`。
- 每秒检查到期 job，但同一 job 在同一分钟最多入队一次。
- scheduler thread 只向线程安全队列生产事件，绝不调用 LLM。
- one-shot job 入队后删除；recurring job 保留。
- durable job 写入 `.scheduled_tasks.json` 并能在重启模拟中恢复。
- session-only job 只在当前进程存在。
- 用户没有输入时，queue processor 也能通过统一 turn 入口交付
  `[Scheduled:<job_id>] <prompt>`。

### 与现有 BaseAgent 的连接点

不要新写第二个简化 Agent Loop。需要连接的已有位置是：

- 在 imports 中增加 `datetime`，但把“当前时间”包装成可在测试中替换的调用点。
- 在 background task 与 Task System 附近新增独立 Cron 区域。
- 在 `TOOLS` 和 `TOOL_HANDLERS` 增加 `schedule_cron`、`list_crons`、
  `cancel_cron`。
- 在 `agent_loop()` 每轮最前面的 pending event 注入阶段消费 cron queue。
- 把 `run_agent_turn()` 扩展或替换成统一的 locked turn 入口，使 CLI 输入和
  cron 自动唤醒共用同一份 history/context。
- 在 `update_context()` 中加入当前本地时区、待调度 job 数量等轻量状态；
  不要把所有 prompt 正文塞进 system prompt。
- 后续 s19 会动态组装工具池，因此 s14 工具应被视为 builtin tools。

推荐明确区分三类锁：

```text
cron_lock   保护 scheduled_jobs、cron_queue、_last_fired
agent_lock  保证同一时刻只有一个主 Agent turn
其他既有锁  继续保护 task、mailbox 和 background registry
```

不要持有 `cron_lock` 调 LLM，也不要持有它等待 `agent_lock`。

### 必须实现

数据与生命周期：

- `DURABLE_PATH = WORKDIR / ".scheduled_tasks.json"`。
- `CronJob(id, cron, prompt, recurring, durable)` dataclass。
- `scheduled_jobs`、`cron_queue`、`cron_lock`、`agent_lock`、
  `_last_fired`。
- `start_runtime_threads(stop_event=None)`，只启动一次 scheduler 和 queue
  processor；仅由 `main()` 调用。

纯逻辑与持久化函数：

- `_cron_field_matches(field, value)`。
- `cron_matches(cron_expr, dt)`。
- `_validate_cron_field(field, lo, hi)`。
- `validate_cron(cron_expr)`。
- `save_durable_jobs()`、`load_durable_jobs()`。
- `schedule_job(cron, prompt, recurring=True, durable=True)`。
- `cancel_job(job_id)`。
- `cron_scheduler_loop(stop_event=None)`。
- `consume_cron_queue()`、`has_cron_queue()`。
- `queue_processor_loop(stop_event=None)`。

工具层：

- `run_schedule_cron` 返回 job ID、表达式、recurring/durable 和本地时区。
- `run_list_crons` 在锁内复制 snapshot，在锁外格式化。
- `run_cancel_cron` 对不存在的 ID 返回清晰错误。
- 三个 tool schema 的 required、默认值与 handler 参数一致。

### 实现提示

按以下顺序实现，出错面最小：

1. 先做不接触全局状态的字段校验和匹配。
2. 再做 `schedule_job` / `cancel_job` 和 durable JSON。
3. 再做 scheduler producer 与“同分钟去重”。
4. 最后做主 Agent 自动交付。

五字段至少支持：

```text
*      任意值
5      单个数字
*/5    正整数步长
1,3,5  列表
1-5    闭区间
```

校验时先拆列表，再识别 wildcard/step/range/number。拒绝字段数量不为五、
非法字符、零或负步长、超界数字、倒序范围。不要依靠匹配函数运行时抛异常来
完成注册校验。

DOM/DOW 使用标准 OR 语义：

```text
两者都是 *       → 日期条件通过
只有一个受限     → 受限字段必须匹配
两者都受限       → 任一字段匹配即可
```

Python weekday 需要转换为 Sunday=0：

```text
(dt.weekday() + 1) % 7
```

同分钟 marker 必须包含日期：`%Y-%m-%d %H:%M`。如果只保存 `HH:MM`，
recurring job 第二天同一分钟会被错误去重。

durable 写入建议采用同目录临时文件加 `replace()`。保存前只 snapshot
`durable=True` 的 job；加载时逐条校验并跳过坏记录。整个 JSON 损坏时记录
warning、返回空集合，不能阻止 BaseAgent 启动。

queue processor 的锁顺序：

1. 等待或轮询 `has_cron_queue()`。
2. non-blocking/短时获取 `agent_lock`。
3. 获得后再次检查队列，防止状态已变化。
4. 通过统一 turn 入口交付。
5. `finally` 释放锁。

### 不要照搬的简化

- 不要复制 s14 中只支持当前章节工具的 `TOOLS` 和简化 `agent_loop()`。
- 不要在模块 import 时执行 `load_durable_jobs()` 后直接启动线程。
- 不要从 scheduler thread 调 `client.messages.create/stream`。
- 不要在 cron thread、CLI thread 中分别维护 history/context。
- 不要只在用户下一次输入时顺便消费 queue；那不算自动交付。
- 不要用真实 `time.sleep(60)` 写测试。

### TDD 顺序

建议在 `tests/test_homework_baseagent_cron.py` 依次添加：

1. `test_cron_field_supports_wildcard_number_step_list_and_range`：
   每种语法各选一个匹配值和不匹配值。
2. `test_validate_cron_rejects_invalid_shape_and_bounds`：
   覆盖四/六字段、越界、倒序范围、零步长和非法字符。
3. `test_cron_matches_uses_dom_dow_or_semantics`：
   固定 fake datetime，分别验证都为 wildcard、单边受限和双边受限。
4. `test_scheduler_enqueues_at_most_once_per_calendar_minute`：
   fake clock 在同一分钟 tick 多次，queue 只有一项。
5. `test_recurring_job_can_fire_on_next_date`：
   日期变化后相同 HH:MM 再次入队。
6. `test_one_shot_is_removed_after_enqueue` 与
   `test_recurring_job_remains_registered`。
7. `test_only_durable_jobs_are_saved_and_valid_jobs_reload`。
8. `test_corrupt_file_and_invalid_job_do_not_abort_loading`。
9. `test_scheduler_only_enqueues_and_never_calls_llm`：
   给 client stub 一个调用即失败的实现。
10. `test_import_does_not_start_runtime_threads`。
11. `test_user_and_cron_turns_share_agent_lock`：
    用 event/barrier 证明两个入口不会同时进入 Agent Loop。

RED 阶段应看到“函数/状态不存在”或期望行为不符，而不是环境变量、真实线程
或真实 API 错误。每通过一组纯函数测试后再进入线程测试。

阶段回归命令：

```bash
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/test_homework_baseagent_cron.py -q
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/test_homework_baseagent_*.py -q
```

### 手动验证 prompt

在 BaseAgent CLI 中依次尝试：

```text
请创建一个只执行一次的定时任务，在下一分钟检查当前目录并总结 Python 文件；列出任务后告诉我它使用的本地时区。
```

```text
请注册一个每 5 分钟运行的持久任务，列出它，然后取消它，并确认 durable 列表中已经不存在。
```

观察：

- 注册结果是否包含 job ID。
- `list_crons` 是否说明 recurring、durable 和本地时区。
- 到期时是否在没有新键盘输入的情况下出现 `[Scheduled:<id>]`。
- 用户 turn 正在执行时，scheduled work 是否只排队而不并发写 history。

### 完成标准

- [ ] wildcard、number、step、list、range 均有正反测试。
- [ ] DOM/DOW 使用 OR 语义。
- [ ] minute marker 包含完整日期。
- [ ] one-shot、recurring 行为不同且正确。
- [ ] durable/session-only 边界正确，损坏记录可恢复。
- [ ] scheduler 只入队，不调用 LLM。
- [ ] runtime 线程显式、可停止且不会重复启动。
- [ ] 用户与 cron 共用一个 locked turn 入口。
- [ ] 三个工具的 schema、handler、prompt/catalog、hook 均已连接。
- [ ] 本阶段和全部既有 BaseAgent 测试通过。

## s16：Team Protocols

本章在现有 MessageBus 和 teammate permission handoff 上增加结构化
request-response 协议。核心不是多加几个字符串类型，而是让请求能被追踪、
响应能被关联、不同协议不会互相误认，并且 mailbox 只有一个可靠的消费入口。

### 目标

实现两套共用机制的协议：

| 协议 | 方向 | 目的 |
| --- | --- | --- |
| shutdown request/response | Lead → teammate → Lead | 优雅结束 teammate |
| plan approval request/response | teammate → Lead → teammate | 提交、批准或拒绝计划 |

要求：

- 每个请求有不可混淆的 `request_id`。
- pending 状态只向 approved/rejected 迁移一次。
- unknown ID、错误响应类型和重复响应不得改变原状态。
- teammate 在 WORK 和 IDLE 都能处理 shutdown。
- Lead 能同时处理 permission、protocol 和 ordinary messages。
- teammate 完成一个工作阶段后进入可唤醒 IDLE，而不是立即退出。

### 与现有 BaseAgent 的连接点

复用并增强：

- `MessageBus.send/read_inbox`、`validate_agent_name`、`mailbox_path`。
- `mailbox_lock` 和 `team_lock`。
- `process_permission_request()`。
- `wait_for_permission_response()` 的 deferred inbox 模式。
- `spawn_teammate_thread()` 中已有的 recovery、guarded tools 和 summary。
- `agent_loop()` 开始处 team message 注入，以及 Stop 后等待 teammate activity。

最关键的结构变化是合并 Lead inbox：

```text
BUS.read_inbox("lead") 只在一个公共 consumer 中发生
  ├─ permission_request  → process_permission_request
  ├─ *_response          → match_response
  ├─ plan request        → 作为需要 Lead 决策的普通可见事件
  └─ message/result      → 注入主 history
```

`run_check_inbox()` 和主循环必须调用这个公共 consumer，不能各自直接读取文件。

### 必须实现

协议状态：

- `ProtocolState(request_id, type, sender, target, status, payload, created_at)`。
- `pending_requests: dict[str, ProtocolState]`。
- 保护 registry 的 `protocol_lock`，或明确复用适合的现有锁。
- `new_request_id()`。
- request type 到合法 response type 的显式映射。
- `match_response(response_type, request_id, approve)`。

Lead 工具：

- `run_request_shutdown(teammate)`。
- `run_request_plan(teammate, task)`。
- `run_review_plan(request_id, approve, feedback="")`。
- 对应的 `request_shutdown`、`request_plan`、`review_plan` schemas/handlers。

teammate 工具与分发：

- `_teammate_submit_plan(from_name, plan)`。
- teammate `submit_plan` schema/handler。
- 共享或职责清楚的 `handle_inbox_message()`。
- `consume_lead_inbox()` 作为单一 Lead mailbox consumer；它必须保留并路由
  permission 消息。

MessageBus 允许的类型至少覆盖：

```text
message
result
permission_request
permission_response
shutdown_request
shutdown_response
plan_approval_request
plan_approval_response
```

### 实现提示

`new_request_id()` 优先使用 `uuid.uuid4().hex`。若保留短随机 ID，必须在
`protocol_lock` 内检测 registry 冲突并重试，测试需要固定 random 制造碰撞。

让 `match_response()` 返回结构化或至少可断言的结果，例如 matched、unknown、
type_mismatch、duplicate，而不是只有 `print()`。状态检查顺序应是：

1. request 是否存在。
2. response type 是否与 request type 匹配。
3. 当前状态是否仍为 pending。
4. 原子更新为 approved/rejected。

Lead router 推荐顺序：

```text
permission_request
  → protocol response
  → plan_approval_request
  → ordinary message/result
```

teammate router 推荐顺序：

```text
permission_response
  → shutdown_request
  → plan_approval_response
  → ordinary message
```

permission waiter 读取 teammate inbox 时，只拿走匹配 `request_id` 的
`permission_response`；其他消息放进 `deferred_inbox`。随后 WORK/IDLE router
必须继续处理这些 deferred messages，不能静默丢弃 shutdown。

plan approval 的教学基线是“协议流程”，不是强制门控。也就是说 teammate 模型
应收到“等待批准”的结果和审批消息，但代码并未天然阻止它继续调用工具。若你
要实现真正门控，把它作为单独增强：

- 为 teammate 保存 approved plan/request 状态。
- 未批准时 guarded mutation 返回 error tool_result。
- approve 后放行，reject 后要求重新提交。

不要只靠 system prompt 宣称已经门控。

### 不要照搬的简化

- 不要照搬课程随机六位 request ID 而忽略碰撞。
- 不要把当前 typo `requested_id` / `match_resposne` 延续为兼容别名；统一接口。
- 不要让 `MessageBus.send()` 白名单继续拒绝新协议类型。
- 不要在 `run_check_inbox()` 与 main loop 中各调用一次 `BUS.read_inbox("lead")`。
- 不要把 `plan_approval_request` 当成 teammate 要消费的审批结果。
- 不要用 s16 的简化 teammate LLM loop 覆盖现有 `with_retry`、
  permission handoff、hooks 和 tool-result 配对。
- 不要把“提交计划后模型通常会等待”当成安全门控。

### TDD 顺序

建议在 `tests/test_homework_baseagent_team_protocols.py` 依次添加：

1. `test_message_bus_accepts_protocol_types_and_preserves_metadata`。
2. `test_protocol_state_uses_request_id_and_ids_are_unique`。
3. `test_matching_response_transitions_pending_request_once`。
4. `test_unknown_wrong_type_and_duplicate_responses_do_not_mutate_state`。
5. `test_lead_consumer_routes_permission_and_protocol_from_same_batch`：
   一次 mailbox snapshot 同时放两类消息。
6. `test_check_inbox_and_agent_loop_share_one_consumer`：
   spy `read_inbox("lead")`，证明没有竞争入口。
7. `test_teammate_handles_shutdown_during_work`。
8. `test_teammate_handles_shutdown_during_idle`，使用 fake clock/event。
9. `test_plan_approve_and_reject_are_injected_into_teammate_history`。
10. `test_permission_waiter_defers_shutdown_and_ordinary_messages`。
11. `test_protocol_tool_schemas_and_handlers_have_same_names`。

若实现计划强制门控，再单独增加：

```text
test_mutating_tool_is_rejected_before_plan_approval
test_mutating_tool_is_allowed_after_plan_approval
test_rejected_plan_requires_resubmission
```

先让 protocol state 的纯测试变红/变绿，再接线程生命周期。线程测试用 event
驱动，不依赖真实 sleep。

阶段回归命令：

```bash
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/test_homework_baseagent_team_protocols.py -q
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/test_homework_baseagent_agent_teams.py -q
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/test_homework_baseagent_*.py -q
```

### 手动验证 prompt

```text
启动 alice 作为后端队友，请她先提交实施计划。收到计划后先拒绝并给出具体反馈，让她重新提交；第二次批准，完成后请求她优雅退出。
```

观察顺序：

```text
plan_approval_request
  → Lead review/reject
  → plan_approval_response
  → teammate 修订并重新 submit
  → Lead approve
  → teammate 工作
  → shutdown_request
  → shutdown_response
```

同时观察 permission request 是否仍能到达 Lead；不能因为检查 plan inbox 而超时。

### 完成标准

- [ ] 所有协议字段统一使用 `request_id`。
- [ ] MessageBus 明确接受每一种协议消息。
- [ ] request/response 类型映射、重复响应和 unknown ID 有测试。
- [ ] Lead mailbox 只有一个 consumer。
- [ ] permission 和 protocol 同批到达时都能正确处理。
- [ ] teammate 在 WORK/IDLE 都能响应 shutdown。
- [ ] plan approve/reject 能回到正确 teammate。
- [ ] 所有新增 schema 与 handler 对齐并进入动态 prompt/catalog。
- [ ] 未实现强制门控时，文档和代码不声称已经具备该安全属性。
- [ ] 原有 agent teams、permission、recovery 测试继续通过。

## s17：Autonomous Agents

本章让 teammate 在 IDLE 阶段自动发现并原子认领可执行任务。Lead 仍负责创建
任务和依赖关系，但不必逐个把 task ID 发给队友。

### 目标

把 teammate 生命周期从“一次工作后退出”升级为：

```text
WORK
  → 没有 tool_use
  → IDLE
      ├─ 收到 inbox       → WORK
      ├─ 找到可认领 task  → 原子 claim → WORK
      ├─ shutdown_request → SHUTDOWN
      └─ timeout          → SHUTDOWN
```

自动认领必须满足三个条件：

- task 是 `pending`；
- task 没有 owner；
- `blockedBy` 中的每个 task 都存在且已 `completed`。

多个 teammate 同时看到同一 task 时，最终只能有一个 owner。

### 与现有 BaseAgent 的连接点

复用：

- s12 的 `Task`、`list_tasks()`、`can_start()`、`claim_task()`、
  `complete_task()`。
- s15 的 `spawn_teammate_thread()`、MessageBus 和 active teammate registry。
- s16 的 WORK/IDLE inbox router 与 shutdown protocol。
- teammate 已有的 recovery、permission handoff 和 summary。

需要调整：

- 为 task 文件的读改写增加 `task_lock`；不要只给 `save_task()` 单独上锁。
- 增加 `scan_unclaimed_tasks()` 和 `idle_poll()`。
- teammate tools 增加 `list_tasks`、`claim_task`、`complete_task`。
- teammate `claim_task` handler 必须把 owner 固定为当前 teammate name，
  不能接受模型自行提供 owner。
- `spawn_teammate_thread()` 采用有限 WORK inner loop 和 WORK/IDLE outer loop。
- active registry 应能区分 running、idle、stopped，至少保证 stop 后原子移除。

主 Agent 的 `run_claim_task()` 仍可使用 owner=`"agent"`；teammate handler 和
Lead handler 不要共用一个会把 owner 写错的无参 wrapper。

### 必须实现

- `task_lock = threading.RLock()` 或等价锁。
- `scan_unclaimed_tasks() -> list[dict]`。
- `IDLE_POLL_INTERVAL` 与 `IDLE_TIMEOUT`，允许测试 monkeypatch。
- `idle_poll(agent_name, messages, name, role, stop_event=None)`，返回明确的
  `work`、`shutdown` 或 `timeout`。
- teammate task schemas：

  - `list_tasks` 无参数；
  - `claim_task(task_id)`；
  - `complete_task(task_id)`。

- teammate handlers：

  - list 输出 status、owner、blockedBy；
  - claim 在闭包内绑定当前 teammate；
  - complete 只能完成 in_progress task，并保留既有状态机约束。

- claim 的原子临界区：

```text
acquire task_lock
  → load task
  → 检查 status
  → 检查 owner
  → 检查 dependencies
  → 修改 owner/status
  → 原子保存
release task_lock
```

如果 task 文件写入已经使用临时文件 replace，保留它；锁解决同进程竞争，
原子 replace 解决半写文件，两者职责不同。

### 实现提示

`scan_unclaimed_tasks()` 只负责生成候选 snapshot，不负责宣告认领成功。扫描与
claim 之间状态可能变化，因此 `idle_poll()` 必须检查 claim 的真实返回。

不要只写：

```text
if "Claimed" in result:
```

更稳妥的教学接口是让 `claim_task()` 返回带 `ok/status/task_id/owner` 的结果，
或者失败后重新读取 task 确认 owner。若暂时保留字符串 API，至少让成功前缀
固定，并为容易误判的错误字符串写回归测试。

IDLE 优先级固定为：

1. 检查 stop event。
2. 读取并路由 inbox；shutdown 优先于普通消息。
3. 扫描 task board。
4. 等待下一次 poll。

不要先 claim task 再处理已经到达的 shutdown。

若第一个候选 claim 失败，说明另一个 teammate 可能抢先成功。可以继续尝试
snapshot 中的后续候选，也可以下一轮重新扫描；不能把失败候选注入为已认领。

身份应主要放在 teammate system prompt，因为 compaction 通常不删除 system。
如果你现有 teammate 压缩逻辑会重建 prompt 或只保留 messages，再在每次进入
WORK 时检查并补一条稳定 `<identity>`。不要以 `len(messages) <= 3` 作为唯一
压缩判断，普通短会话也会满足这个条件；优先使用显式 compact 标记。

IDLE 不应忙等。生产代码可以 `stop_event.wait(IDLE_POLL_INTERVAL)`，测试则让
fake event/clock 立即推进。

### 不要照搬的简化

- 不要照搬 s17 在锁外 `load → check owner → save` 的 claim；它仍有竞态。
- 不要把 `scan_unclaimed_tasks()` 返回候选等同于成功认领。
- 不要在 IDLE 先扫任务再读 inbox。
- 不要真实 sleep 60 秒测试 timeout。
- 不要为了加入 outer loop 而删除 teammate 的 error recovery、permission
  waiter、deferred inbox 或 tool-result 配对。
- 不要允许 teammate 调 `claim_task(task_id, owner="任意名字")`。
- 不要因为 `blockedBy` 非空就永远跳过；所有依赖完成后它应成为候选。

### TDD 顺序

建议在 `tests/test_homework_baseagent_autonomous_agents.py` 依次添加：

1. `test_scan_returns_only_pending_unowned_unblocked_tasks`：
   同时准备 owned、completed、missing dependency 和 completed dependency。
2. `test_idle_checks_inbox_before_task_board`：
   inbox 有普通消息且 board 有 task，应先返回 work 而不 claim。
3. `test_idle_shutdown_has_priority_over_ordinary_work`。
4. `test_successful_auto_claim_injects_exact_task_and_returns_work`。
5. `test_failed_claim_is_not_reported_as_work_on_that_task`。
6. `test_two_simultaneous_claims_have_exactly_one_winner`：
   barrier 同时放行两个线程，断言一个成功、文件只有一个 owner。
7. `test_completing_dependency_makes_downstream_task_scannable`。
8. `test_teammate_claim_handler_forces_current_agent_as_owner`。
9. `test_idle_timeout_uses_fake_clock_or_event`。
10. `test_work_idle_work_cycle_preserves_deferred_protocol_messages`。
11. `test_identity_is_preserved_after_explicit_compaction`。

并发测试连续运行至少三次，避免偶然通过：

```bash
for i in 1 2 3; do
  .venv/bin/python -m pytest -p no:cacheprovider \
    tests/test_homework_baseagent_autonomous_agents.py::\
test_two_simultaneous_claims_have_exactly_one_winner -q
done
```

然后执行：

```bash
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/test_homework_baseagent_task_system.py \
  tests/test_homework_baseagent_agent_teams.py \
  tests/test_homework_baseagent_autonomous_agents.py -q
```

### 手动验证 prompt

```text
创建三个任务：A 无依赖，B 依赖 A，C 无依赖。启动 alice 和 bob，让他们自行认领；确认 B 只在 A 完成后出现，并在两位队友空闲后请求关闭。
```

观察：

- alice/bob 是否认领不同任务。
- `.tasks/*.json` 是否始终只有一个 owner。
- A 完成前 B 是否不可见，完成后是否可认领。
- teammate 完成当前任务后是否进入 IDLE 并继续发现工作。
- shutdown 是否能打断 IDLE。

### 完成标准

- [ ] 扫描条件严格覆盖 status、owner 和全部依赖。
- [ ] inbox 优先于 task board。
- [ ] claim 的读、校验、修改、保存处于同一 task lock。
- [ ] 并发认领测试只有一个 winner，且可重复通过。
- [ ] teammate 获得 list/claim/complete 工具但不能伪造 owner。
- [ ] WORK/IDLE 循环有轮数和 timeout 边界。
- [ ] WORK/IDLE 都继续路由 permission 和 protocol 消息。
- [ ] 身份在 compaction 后仍可靠存在。
- [ ] task system 和 agent teams 回归测试通过。

## s18：Worktree Isolation

本章把 task、teammate cwd 与 Git worktree 生命周期连接起来，让并行队友不会
在同一个目录中覆盖彼此的文件。worktree 隔离的是工作目录，不替代任务认领、
权限确认或最终人工 review。

### 目标

实现：

- Task 可选绑定一个 Git worktree。
- Lead 能创建、保留或安全删除 worktree。
- teammate 认领带 worktree 的 task 后，自己的文件工具在该目录执行。
- 不同 teammate 的 cwd 相互独立，不调用全局 `os.chdir()`。
- 有未提交改动或新增提交时，删除默认失败。
- Git 操作成功后写 append-only 生命周期事件。

教学流程：

```text
create task
  → create_worktree(name, task_id)
  → task 仍为 pending
  → teammate 原子 claim
  → teammate 私有 wt_ctx 指向 worktree
  → 在隔离 cwd 工作
  → complete_task
  → keep_worktree 等待 review，或明确 discard 后 remove
```

### 与现有 BaseAgent 的连接点

需要修改但不能破坏的接口：

- `Task` 增加 `worktree: str | None = None`。
- `load_task()` 兼容没有 `worktree` 字段的旧 JSON。
- `safe_path(p, cwd=None)` 以 `cwd or WORKDIR` 为安全根。
- `run_bash/read/write/edit/glob` 接受可选 cwd。
- `run_teammate_guarded_tool()` 执行获批工具时必须把当前 teammate cwd 传给
  raw handler，不能批准后退回主 WORKDIR。
- teammate 工具继续经过 `PreToolUse`，执行后继续触发 `PostToolUse`；
  cwd 隔离不能成为绕过 hooks 的另一条 handler 路径。
- diff preview hook 也必须使用 block 的有效 cwd，否则预览与实际修改不同文件。
- teammate thread 内保存私有 `wt_ctx`；不得用进程全局 cwd。
- s17 自动 claim 成功后读取 task.worktree 并更新 `wt_ctx`。
- s19 动态 MCP 只扩展 Lead 工具池，不应意外把 worktree 管理工具交给 teammate。

Lead 新工具：

- `create_worktree(name, task_id="")`。
- `keep_worktree(name)`。
- `remove_worktree(name, discard_changes=False)`。

### 必须实现

状态与验证：

- `WORKTREES_DIR = WORKDIR / ".worktrees"`。
- 严格 name pattern，例如 `[A-Za-z0-9._-]{1,64}`，并单独拒绝 `.`、`..`。
- worktree 路径 resolve 后必须仍位于 `WORKTREES_DIR`。
- `run_git(args, cwd=WORKDIR) -> (ok, output)`，使用 argv list，不拼 shell。
- `log_event(type, name, task_id="", **metadata)`。

生命周期：

- `create_worktree(name, task_id="")`。
- `bind_task_to_worktree(task_id, name)`。
- `_inspect_worktree_changes(path)`，区分 dirty files、相对创建基线的 commits、
  检查失败。
- `keep_worktree(name)`。
- `remove_worktree(name, discard_changes=False)`。

tool schemas/handlers：

- `create_worktree` required=`name`，`task_id` 可选。
- `keep_worktree` required=`name`。
- `remove_worktree` required=`name`，`discard_changes` 默认 false。

建议在创建 worktree 时记录创建基线 SHA。删除检查使用：

```text
git status --porcelain
git rev-list --count <creation_base_sha>..HEAD
```

不要依赖 `@{push}`：新建教学分支通常没有 upstream，命令失败后若只读空 stdout，
会把已有 commit 误判为零。

### 实现提示

`safe_path` 的边界应随调用者 cwd 变化：

```text
base = resolve(cwd or WORKDIR)
path = resolve(base / user_path)
要求 path 位于 base 内
```

这意味着 teammate 在 worktree 内不能用 `../../` 回到主仓库。Lead 的普通文件
工具仍以 WORKDIR 为根。

为了让 hooks 看见真实 cwd，可选择：

- 给 tool block 增加经过验证的 `cwd`/agent context 属性；或
- 让 teammate guarded dispatcher 把 cwd 作为内部参数传给 permission 和
  diff helper，但不让模型直接控制这个参数。

不能把内部 cwd 暴露成模型可随意填写的 tool input。

创建顺序：

1. 校验 name 和目标路径。
2. 若 task_id 存在，先确认 task 存在且尚未绑定其他 worktree。
3. 执行 `git worktree add <path> -b wt/<name> HEAD`。
4. Git 成功后绑定 task。
5. 绑定或事件写入失败时，返回清晰的部分失败状态；进阶实现可安全回滚新
   worktree，但不能假装全部成功。
6. 成功后写 create event。

绑定只修改 `task.worktree`，保持 status=`pending`、owner=None。真正推进状态
仍由 s17 claim 完成。

teammate：

- claim 成功后读取最新 task；有 worktree 则验证目录后设置私有 `wt_ctx`。
- claim 无 worktree task 时把 `wt_ctx` 设为 None。
- complete 后清空 `wt_ctx`，避免下一个 task 错用旧目录。
- bash/read/write/edit/glob 的 wrapper 每次读取当前 `wt_ctx`。

删除时 fail closed：

- status 或 commit 检查失败 → 默认拒绝。
- dirty files > 0 或 commits > 0 → 默认拒绝并建议 `keep_worktree`。
- 只有 `discard_changes=true` 且通过 destructive permission 才运行强制删除。
- worktree remove 成功后再删除专用 branch；分支删除失败要报告部分成功。
- 只为真实成功步骤记录 remove event。

### 不要照搬的简化

- 不要调用全局 `os.chdir()`；所有线程会一起切目录。
- 不要让模型提供内部 cwd。
- 不要只给 bash 加 cwd，却让 read/write/edit/glob 继续操作主 WORKDIR。
- 不要批准 teammate write 后调用不带 cwd 的 `run_write()`。
- 不要用 `@{push}` 的空输出推断“没有提交”。
- 不要默认 `git worktree remove --force`。
- 不要让 create/bind 自动 claim 或 complete task。
- 不要在 Git 命令失败时仍写成功 event。
- 不要把主 worktree 或 WORKDIR 作为可删除目标。

### TDD 顺序

建议在 `tests/test_homework_baseagent_worktrees.py` 依次添加：

1. `test_validate_worktree_name_rejects_empty_dot_dotdot_slash_and_overlong`。
2. `test_resolved_worktree_path_cannot_escape_root`。
3. `test_old_task_json_loads_with_worktree_none`。
4. `test_create_uses_argv_git_and_binds_only_after_success`。
5. `test_failed_git_create_does_not_bind_or_log_success`。
6. `test_bind_preserves_pending_status_and_owner`。
7. `test_teammate_claim_sets_private_cwd_and_complete_clears_it`。
8. `test_two_teammates_with_same_relative_filename_write_different_roots`。
9. `test_all_teammate_file_tools_reject_escape_from_worktree`。
10. `test_diff_preview_and_actual_write_use_same_cwd`。
11. `test_remove_refuses_dirty_or_committed_worktree_by_default`。
12. `test_inspection_failure_refuses_removal`。
13. `test_explicit_discard_still_requires_permission`。
14. `test_events_are_written_only_after_successful_lifecycle_steps`。
15. `test_main_worktree_cannot_be_removed_by_name_trick`。

Git 测试优先 stub `subprocess.run` 并断言 argv/cwd。只增加一个受控临时 Git
仓库的 smoke test，不操作课程根仓库。

阶段回归命令：

```bash
.venv/bin/python -m pytest -p no:cacheprovider \
  tests/test_homework_baseagent_worktrees.py \
  tests/test_homework_baseagent_task_system.py \
  tests/test_homework_baseagent_agent_teams.py -q
```

### 手动验证 prompt

```text
创建 backend 和 frontend 两个任务，为它们分别建立并绑定 worktree，然后启动 alice 和 bob 自行认领。让两人各自创建同名 status.txt，最后比较两个 worktree 的文件内容和当前分支。
```

然后：

```text
尝试删除仍有改动的 backend worktree，但不要丢弃修改；确认系统拒绝删除并建议 keep_worktree。
```

观察 task JSON 在绑定后仍为 pending；认领后 owner/status 改变；两个
`status.txt` 位于不同根目录；默认删除不会丢工作。

### 完成标准

- [ ] 旧 Task JSON 向后兼容。
- [ ] name、resolve path 和主 worktree 都有保护。
- [ ] create 成功后才 bind/log，bind 不改变 task 状态。
- [ ] 每个 teammate 有独立 wt_ctx，不使用全局 chdir。
- [ ] bash/read/write/edit/glob 和 diff hook 使用同一有效 cwd。
- [ ] permission handoff 获批后仍在正确 worktree 执行。
- [ ] dirty、committed 或无法检查的 worktree 默认拒绝删除。
- [ ] `discard_changes=true` 仍需要 destructive permission。
- [ ] event log 只记录真实成功步骤。
- [ ] task、team、permission 回归测试通过。

## s19：MCP Tools

本章把 mock MCP server 发现的工具增量加入主 Agent 动态工具池。

## 跨阶段集成验证

本章组合验证 cron、protocol、autonomy、worktree 和 MCP 的交互边界。

## 与 s20 的功能冗余对比

本章区分真正冗余、重复职责、可选增强和不可删除的必要措施。
