# Automatic memory extraction and agent-private memory productization

## Goal

在已经完成的长期记忆后端基础上，把 `10` 的后半段真正做成产品能力：

* 自动提取长期记忆
* agent 私有记忆
* agent 记忆快照与刷新

让系统不仅“能把长期记忆存进后端”，而且能开始：

* 自动沉淀长期记忆
* 为不同 agent 维护各自的长期上下文
* 以任务状态、快照和审计方式稳定运行

## Why Now

当前已经有：

* 项目级规则文件层
* 长期记忆四类型
* 当前会话记忆
* 恢复上下文
* PostgreSQL 长期记忆主存储
* Redis 队列
* MinIO 归档
* extraction job / snapshot job 基础

但现在这些能力还偏“后端基础设施已经有了”，离产品化还差一层：

* 自动提取结果还不够可控/可审计/可理解
* agent scope 已有基础，但还不是一个真正可用的产品能力
* snapshot 已有 archive 通道，但还没有清晰的可用行为和可见面

## What I already know

* 长期记忆 durable backend 已完成并打通 PostgreSQL / Redis / MinIO
* `save_memory / list_memory / delete_memory` 已存在
* `MemoryService` 已能 enqueue extraction 和 snapshot refresh
* 默认 extractor 目前还是保守 heuristic，不是最终产品行为
* 当前 agent scope 只是基础元数据，不是完整产品面
* 当前 session JSONL ledger 继续保留，不迁移数据库

## Requirements

* 本轮必须把自动提取长期记忆做成真正可用的产品能力，而不是仅停在 job plumbing。
* 本轮必须把 agent 私有记忆做成真正可查询、可隔离、可刷新的能力，而不是只保留 scope 字段。
* PostgreSQL 继续作为长期记忆事实来源。
* Redis 继续负责任务调度。
* MinIO 继续负责快照/归档对象。
* 不迁移 transcript / session ledger。

## Acceptance Targets

* [x] 系统能自动从会话中提出长期记忆候选，并通过后台任务处理，而不阻塞主流程。
* [x] 自动提取结果不会无约束地直接污染长期记忆，至少具备可审计来源和任务状态。
* [x] agent 私有记忆与全局长期记忆能明确区分。
* [x] 针对某个 agent 查询长期记忆时，能够得到：
  * 该 agent 私有记忆
  * 以及仍然适用的全局长期记忆
* [x] agent snapshot/refresh 形成清晰产品行为：
  * 什么时候刷新
  * 刷新后保存什么
  * archive 对象在哪里
* [x] 当前实现足以支撑后续更强的自动化，而不需要再次重做存储边界。

## Planned Features

### 1. Automatic Memory Extraction Product Layer

* 为自动提取任务增加清晰行为：
  * 候选生成
  * 任务写入
  * 后台处理
  * 结果写回长期记忆
* 给自动提取结果补最小审计信息：
  * source
  * job id
  * created_at
  * status
* 让自动提取和现有质量规则协同，而不是绕过它们

### 2. Agent-Private Memory Read/Write Path

* 让 agent scope 真正参与：
  * save
  * list
  * recall
  * delete
* 主 agent 继续默认写全局长期记忆
* child / subagent 可以拥有私有长期记忆 scope

### 3. Snapshot Product Behavior

* 为 agent snapshot 明确最小产品行为：
  * 刷新 job 什么时候触发
  * snapshot 保存哪些长期记忆
  * snapshot archive object key 如何生成
* 将 snapshot 结果与 job 状态联通，形成可追踪结果

### 4. Focused CLI / Inspection Surface

* 在现有 `memory jobs` 基础上补足足够查看状态的输出
* 必要时增加最小 inspection 命令，帮助确认：
  * 某 agent 当前有哪些私有记忆
  * 最近一次 snapshot/refresh 是否完成

## Planned Extensions

* 自动提取结果审核流
* 更复杂的提取策略（LLM-based extraction）
* path-scoped agent memory
* 跨项目共享 agent memory
* 更强的 snapshot restore/import/export 体验
* stale-memory trust scoring
* semantic retrieval / ranking

## Definition of Done

* 自动提取长期记忆对用户/系统是“可见且可解释”的
* agent 私有记忆已形成真实能力，而不是只存在 schema 中
* snapshot/refresh 行为被清楚定义并可测试
* Focused pytest / ruff / mypy 通过
* Trellis docs/PRD 记录清楚当前已做和未来扩展边界

## Technical Approach

* 继续复用当前 durable backend：
  * PostgreSQL
  * Redis
  * MinIO
* 在 `memory.service` 之上补产品行为，不重写底层存储
* extractor 继续保留可替换接口，但把当前默认实现做成更像产品能力的最小版本
* agent scope 通过 repository/service 正式进入读取和刷新链

## Out Of Scope

* transcript / session ledger 迁库
* vector retrieval
* path-scoped rules
* user-scoped rules files
* 多租户体系

## Technical Notes

* `.trellis/tasks/04-18-unified-context-memory-closeout/prd.md`
* `.trellis/tasks/04-18-memory-module-gap-review/prd.md`
* `.trellis/spec/guides/planning-targets-guide.md`
* `.trellis/spec/backend/database-guidelines.md`
* `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`
* `coding-deepgent/src/coding_deepgent/memory/backend.py`
* `coding-deepgent/src/coding_deepgent/memory/service.py`
* `coding-deepgent/src/coding_deepgent/memory/extractor.py`
* `coding-deepgent/src/coding_deepgent/memory/runtime_support.py`

## Checkpoint

State:
- terminal

Verdict:
- APPROVE

Implemented:
- Added automatic extraction jobs on top of the durable memory backend.
- Added product-facing inspection for memory jobs, memory records, and agent scopes.
- Added agent-private memory scope behavior so child/fork agents can enqueue and read private long-term memory while the main agent remains global by default.
- Added snapshot/archive job handling through the same service layer.
- Kept session JSONL ledger untouched as intended.

Verification:
- `pytest -q coding-deepgent/tests/test_memory_backend.py coding-deepgent/tests/test_memory_cli.py coding-deepgent/tests/test_subagents.py`
- broader focused memory/runtime verification still passed after backend integration
- `ruff check ...`
- `mypy ...`
- live smoke with configured services:
  - PostgreSQL: ok
  - Redis queue: ok
  - MinIO/S3-compatible archive: ok
