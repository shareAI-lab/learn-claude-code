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
