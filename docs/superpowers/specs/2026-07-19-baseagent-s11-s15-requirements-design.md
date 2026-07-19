# BaseAgent s11–s15 需求文档设计

## 目标

新增 `homework/REQUIREMENTS_s11_s15.md`，指导学习者在当前 `homework/BaseAgent.py` 的 s01–s10 能力之上，累计集成 s11 Error Recovery、s12 Task System、s13 Background Tasks、s14 Cron Scheduler 和 s15 Agent Teams。

文档面向教学实现，保持函数明确、依赖少、机制显式；提供足够的做法提示、伪代码和测试建议，但不直接给出完整 `BaseAgent.py` 答案。

## 已确认口径

采用累计集成方案：

- 保留当前 BaseAgent 的工具、hook、权限、TodoWrite、子 Agent、技能、压缩、记忆、动态 system prompt 和 streaming 调用。
- 新增机制必须说明如何进入现有控制流，不能简单拼接五个 lesson 的独立简化循环。
- 目标文件约 700–900 行，细致程度与 `homework/REQUIREMENTS_s06_s10.md` 相当。
- 只新增需求文档，不修改 `homework/BaseAgent.py`。

## 章节结构

文档包含：

1. 背景与当前 BaseAgent 基线。
2. 总体要求和推荐实现顺序。
3. s11–s15 五章需求。
4. 累计版 Agent Loop、工具执行和外部事件整合顺序。
5. 推荐给实现 Agent 的完整 prompt。
6. 自动化测试建议。
7. 手动测试场景。
8. 最终完成标准与能力矩阵。

每章统一包含：

- 目标与当前缺口。
- 必须实现的常量、状态、函数、工具或存储。
- 与当前 BaseAgent 的整合位置。
- 做法提示和伪代码。
- 常见错误。
- 验收标准。
- 可选挑战。

## 五章范围

### s11 Error Recovery

- 在现有 streaming 调用上支持动态 `model` 和 `max_tokens`。
- 处理输出截断、上下文超限和 429/529 瞬态错误。
- 引入 `RecoveryState`、指数退避、随机抖动、续写限制和可选备用模型。
- 复用现有 s08 `reactive_compact()`，避免重复实现压缩系统。

### s12 Task System

- 新增 `.tasks/{id}.json` 持久化任务、`Task` 数据结构和任务 CRUD。
- 实现 `blockedBy`、认领、完成和下游解锁。
- 明确 Task System 与现有 `CURRENT_TODOS` / `todo_write` 的职责边界。
- 增加五个任务工具并更新动态工具目录。

### s13 Background Tasks

- 为 bash 增加 `run_in_background` 控制参数和慢操作兜底判断。
- 在线程中执行慢工具，立即返回与原始 `tool_use_id` 配对的占位结果。
- 完成后使用独立 `<task_notification>` 注入，不复用原始工具调用 ID。
- 保证 PreToolUse/PostToolUse、权限和共享状态锁的调用时机明确。

### s14 Cron Scheduler

- 实现五段式 Cron 匹配、校验、durable/session-only 存储和同一分钟防重。
- 用 Scheduler、Queue、Queue Processor、Consumer 四层解耦时间判断与 Agent 执行。
- 使用 `cron_lock` 保护调度状态，使用 `agent_lock` 防止并行 LLM turn。
- 将当前 main 的局部 history/context 重构为可被用户输入和队列处理器安全调用的共享会话状态。
- 后台线程只在 `main()` 中启动，保证模块可导入测试。

### s15 Agent Teams

- 区分现有 s06 `task` 子 Agent 与 s15 长期队友。
- 新增文件 MessageBus、队友线程、`spawn_teammate`、`send_message` 和 `check_inbox`。
- 队友复用安全工具和 hook，但不得递归启动子 Agent 或队友。
- 说明 Lead 外层自动注入与主动 `check_inbox` 两条交付路径。
- 明确教学版文件邮箱、daemon 生命周期、消费式读取和权限冒泡的局限。

## 累计整合重点

需求文档必须明确以下顺序和边界：

- 压缩前快照、上下文压缩、动态 prompt、临时记忆注入、可恢复 LLM 调用。
- `max_tokens` 截断输出何时写入 history。
- 工具 permission/hook、后台分流和 tool-result 配对。
- 后台完成通知、Cron 事件和队友 inbox 如何进入后续消息。
- Stop hook、记忆提取和会话状态更新的顺序。
- 多线程只能通过受锁状态或文件邮箱通信，不能直接并发修改 Lead history。

## 测试设计

自动测试不调用真实 API，使用 fake response/block/client、临时目录和 monkeypatch：

- s11：退避边界、错误分类、一次 reactive compact、截断升级与续写上限。
- s12：持久化、缺失依赖、状态机和解锁。
- s13：占位结果、完成通知、hook 次数和锁保护。
- s14：Cron 语法、DOM/DOW OR、防重、durable 恢复和 agent lock。
- s15：邮箱消费、同名队友、防递归、summary 提取和两种 inbox 交付。

手动测试为每章提供可直接输入的 prompt、应观察的文件和日志。

## 验收

- 目标文件为 `homework/REQUIREMENTS_s11_s15.md`。
- 总行数在 700–900 行之间。
- s11–s15 每章都有统一的七类内容。
- 明确当前 BaseAgent 的真实整合点，尤其是 streaming、hook、TodoWrite、压缩和记忆。
- 包含自动测试、手动测试、Agent 实现 prompt、累计 Agent Loop 和最终能力矩阵。
- 不含未完成占位标记，不修改 BaseAgent 或现有需求文档。
