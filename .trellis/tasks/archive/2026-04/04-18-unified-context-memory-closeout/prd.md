# Unified context and memory model closeout

## Goal

把 `coding-deepgent` 的“产品内长期规则 + 长期记忆 + 当前会话记忆 + 恢复上下文”收成一个统一、可执行、可验证的产品模型，并以一次集成实现的方式落到当前 mainline，而不是继续让这四层作为零散能力分别演化。

## Why Now

当前本地已经分别具备：

* 长期记忆
* 当前会话记忆
* compact / resume / recovery
* prompt/context 装配

但它们之间的边界仍然主要存在于讨论和局部实现中，尚未形成一个对用户、实现者、后续任务都清晰的统一模型。

如果现在不收口：

* 记忆和上下文恢复会继续混淆
* 新功能会继续以“补一点 memory”或“补一点 context”方式零散演进
* 后续规划会持续缺少清晰验收目标

## What I already know

* 当前长期记忆已经是四类型结构：`user / feedback / project / reference`
* 当前长期记忆已经具备 `save_memory / list_memory / delete_memory`
* 当前长期记忆已经有 bounded recall / render，并且部分 `feedback` 能直接影响行为
* 当前已经有 `Current-session memory`
* 当前 recovery/resume 已经能分开显示长期记忆和当前会话记忆
* 当前还没有正式的产品内长期规则文件层
* 当前长期记忆仍不是 durable persistent backend
* cc 侧是“长期说明 + 长期记忆 + session memory + transcript/compact/resume + dynamic context protocol”的组合系统，而不是单独一个 memory 子模块

## Requirements

* 本轮必须把四层统一模型明确落到当前 mainline：
  1. 项目级规则文件
  2. 长期记忆
  3. 当前会话记忆
  4. 恢复上下文
* Layer 1 采用文件型规则入口
* Layer 1 第一版只做单一项目级规则文件，不做路径级或用户级规则作用域
* Layer 1 存长期行为约束，不存系统自己学到的知识
* Layer 2 存长期可复用知识，不冒充长期规则
* Layer 3 继续作为当前这次长会话的工作记忆
* Layer 4 继续作为历史事实恢复层
* 四层进入模型的顺序固定为：
  1. 项目级规则文件
  2. 长期记忆
  3. 当前会话记忆
  4. 恢复上下文
* Layer 1 / Layer 2 允许用户直接编辑
* Layer 3 / Layer 4 以系统维护为主

## Acceptance Targets

* [x] 项目里存在一个明确的、用户可直接编辑的项目级规则文件入口，且它不再和长期记忆混淆。
* [x] 运行时装配明确遵守四层固定顺序：
  1. 项目级规则文件
  2. 长期记忆
  3. 当前会话记忆
  4. 恢复上下文
* [x] recovery / resume / context 装配里，用户能清楚看见长期记忆与当前会话记忆的区别。
* [x] 项目级规则文件、长期记忆、当前会话记忆、恢复上下文之间的职责边界被显式写进产品合同和测试。
* [x] 当前会话摘要不会被错误提升为长期记忆或长期规则。
* [x] 恢复上下文不会被错误提升为长期记忆或长期规则。
* [x] 后续 feature-family planning 可以围绕这四层拆任务，而不需要重新解释系统边界。

## Planned Features

* 增加单一项目级规则文件入口。
  * 推荐路径：`.coding-deepgent/RULES.md`
* 在 runtime prompt/context 组装里正式接入项目级规则文件。
* 固化四层装配顺序，并增加 focused tests 验证该顺序不漂移。
* 把 Layer 1 / Layer 2 / Layer 3 / Layer 4 的职责和禁止越层规则写入 Trellis backend contracts。
* 明确错误提升的禁止规则：
  * transcript 历史事实不能直接成为长期规则
  * transcript 历史事实不能直接成为长期记忆
  * 当前会话记忆不能直接成为长期规则
  * 当前会话记忆不能直接成为长期记忆
* 在 recovery / resume 可见面中保留：
  * 项目级规则文件存在性/入口信号
  * 长期记忆
  * 当前会话记忆
* 补 focused tests 覆盖：
  * 规则文件存在/缺失时的装配行为
  * 四层固定顺序
  * recovery / resume 的分层可见面
  * 错误层级提升不发生

## Planned Extensions

* 路径级规则文件
* 用户级规则文件
* 长期记忆 durable persistence backend
* 更聪明的长期记忆筛选与过时判断
* 自动建议或自动提取长期记忆
* agent-private / child-agent memory
* 统一规则/记忆浏览入口

## Definition of Done

* 代码、合同、测试三者一致
* 四层模型对用户、实现者、后续任务都清晰
* Focused pytest / ruff / mypy 通过
* Trellis 文档已同步到足以支撑后续 planning

## Technical Approach

* Layer 1 通过文件入口进入当前 prompt/context 组装链
* Layer 2 继续使用结构化长期记忆层
* Layer 3 继续保持 current-session memory 的独立职责
* Layer 4 继续保持 transcript / compact / resume 的事实恢复职责
* 不增加为兼容旧局部设计而存在的桥接层
* 直接采用更清晰的长期分层边界

## Out Of Scope

* 本轮不做路径级规则
* 本轮不做用户级规则
* 本轮不做长期记忆持久化 backend
* 本轮不做自动提取长期记忆
* 本轮不做 agent 私有记忆

## Technical Notes

* `.trellis/tasks/04-18-memory-module-gap-review/prd.md`
* `.trellis/project-handoff.md`
* `.trellis/spec/guides/planning-targets-guide.md`
* `.trellis/spec/guides/architecture-posture-guide.md`
* `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`
* `.trellis/spec/backend/session-compact-contracts.md`
* `/root/claude-code-haha/src/memdir/*`
* `/root/claude-code-haha/src/services/SessionMemory/*`
* `/root/claude-code-haha/src/utils/queryContext.ts`
* `/root/claude-code-haha/src/utils/attachments.ts`
* `coding-deepgent/src/coding_deepgent/memory/*`
* `coding-deepgent/src/coding_deepgent/sessions/*`
* `coding-deepgent/src/coding_deepgent/prompting/*`

## Checkpoint

State:
- terminal

Verdict:
- APPROVE

Implemented:
- Added a project-level rules file layer at `.coding-deepgent/RULES.md`.
- Integrated project rules into prompt assembly ahead of long-term memory.
- Added a dedicated current-session memory middleware so Layer 3 is model-visible outside of recovery text.
- Split user-facing recovery brief from model-facing resume context so resume no longer duplicates earlier layers.
- Added recovery visibility for project rules while keeping long-term memory and current-session memory visibly separate.
- Updated Trellis docs/contracts so later work can plan against the fixed four-layer model.

Verification:
- `pytest -q coding-deepgent/tests/test_prompting.py coding-deepgent/tests/test_rules.py coding-deepgent/tests/test_session_memory_middleware.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_memory_integration.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py`
- `ruff check coding-deepgent/src/coding_deepgent/rules coding-deepgent/src/coding_deepgent/prompting/builder.py coding-deepgent/src/coding_deepgent/sessions/project_rules.py coding-deepgent/src/coding_deepgent/sessions/session_memory_middleware.py coding-deepgent/src/coding_deepgent/sessions/contribution_registry.py coding-deepgent/src/coding_deepgent/sessions/resume.py coding-deepgent/src/coding_deepgent/containers/app.py coding-deepgent/tests/test_prompting.py coding-deepgent/tests/test_rules.py coding-deepgent/tests/test_session_memory_middleware.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_memory_integration.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py`
- `mypy coding-deepgent/src/coding_deepgent/rules coding-deepgent/src/coding_deepgent/prompting/builder.py coding-deepgent/src/coding_deepgent/sessions/project_rules.py coding-deepgent/src/coding_deepgent/sessions/session_memory_middleware.py coding-deepgent/src/coding_deepgent/sessions/contribution_registry.py coding-deepgent/src/coding_deepgent/sessions/resume.py coding-deepgent/src/coding_deepgent/containers/app.py coding-deepgent/tests/test_prompting.py coding-deepgent/tests/test_rules.py coding-deepgent/tests/test_session_memory_middleware.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_memory_integration.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py`
