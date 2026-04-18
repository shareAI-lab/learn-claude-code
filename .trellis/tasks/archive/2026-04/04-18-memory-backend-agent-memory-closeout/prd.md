# Long-term memory backend and agent memory closeout

## Goal

完整实现长期记忆后端升级与 agent 私有记忆能力，使 `coding-deepgent`
在不重做会话 ledger 的前提下，完成：

* `9` 长期记忆 durable persistence
* `10` 自动提取长期记忆 + agent 私有记忆 / snapshot 基础

并显式使用：

* PostgreSQL
* Redis
* MinIO

来体现真正的后端系统能力。

## Why Now

当前长期记忆已经具备：

* 四类型模型
* save / list / delete
* bounded recall
* feedback enforcement

但它仍然不是 durable backend，也没有自动提取、任务状态、agent 私有记忆、
snapshot、归档等真正的后端能力。

如果继续停留在当前形态：

* 重启后长期记忆不可靠
* 自动积累长期记忆无法成立
* agent 私有记忆无法落地
* “记忆后端”无法体现出真正的数据库 / 队列 / 对象存储设计能力

## What I already know

* 当前统一模型已明确：
  1. 项目级规则文件
  2. 长期记忆
  3. 当前会话记忆
  4. 恢复上下文
* Layer 1 继续使用文件，不进入数据库
* Layer 2 是本轮后端升级核心
* Layer 3 / Layer 4 继续留在现有 session/transcript/compact/resume 体系
* 当前长期记忆后端仍是运行时 store，不是 durable persistence
* 当前还没有：
  * PostgreSQL 主存储
  * Redis queue/worker
  * MinIO snapshot/archive
  * extraction jobs
  * agent-private memory

## Requirements

* 本轮完整实现 `9` 和 `10`，但不迁移现有 session JSONL ledger。
* PostgreSQL 成为长期记忆主存储。
* Redis 负责异步任务队列、去重、防抖、锁。
* MinIO 负责快照和归档对象，不负责长期记忆主记录。
* 长期记忆继续保持四类型：`user / feedback / project / reference`
* 项目级规则文件继续保留为文件入口，不数据库化。
* 当前会话记忆和恢复上下文不得错误迁入长期记忆主库。

## Acceptance Targets

* [ ] 长期记忆在进程重启后仍可读取、列出、删除和使用。
* [ ] 长期记忆的主事实来源变为 PostgreSQL，而不是仅运行时内存。
* [ ] 现有 `save_memory / list_memory / delete_memory` 保持产品语义，但底层切到 PostgreSQL。
* [ ] 自动提取长期记忆不阻塞主流程，而是走 Redis 队列 + worker。
* [ ] 自动提取任务至少有可见状态：
  * `queued`
  * `running`
  * `completed`
  * `failed`
* [ ] 长期记忆具备最小版本/审计能力，至少能追踪：
  * 来源
  * 创建时间
  * 最后更新时间
  * 当前状态
* [ ] agent 私有记忆的基础作用域成立，不再只有全局长期记忆。
* [ ] snapshot / archive 的大对象不进入 PostgreSQL，而进入 MinIO。
* [ ] 当前会话记忆和恢复上下文继续保持独立，不被错误数据库化。

## Planned Features

### 1. PostgreSQL Long-Term Memory Storage

* 新增长期记忆主表
* 新增长期记忆版本表
* 新增提取任务状态表
* 新增 agent 记忆作用域表
* 增加 migration

建议最小表族：

* `memory_records`
* `memory_versions`
* `memory_extraction_jobs`
* `agent_memory_scopes`

### 2. Repository / Service Layer

* 新增 `MemoryRepository`
* 新增 `MemoryService`
* 负责：
  * save
  * list
  * delete/archive
  * version append
  * scope filtering
  * idempotent write

### 3. Keep Existing Product Surface

* 保持现有工具入口：
  * `save_memory`
  * `list_memory`
  * `delete_memory`
* 底层从 runtime store 切到 PostgreSQL

### 4. Redis Queue + Worker

* 自动提取长期记忆走异步任务
* worker 处理：
  * extract long-term memory
  * refresh agent memory snapshot
  * archive snapshot object
* 增加：
  * dedupe key
  * debounce
  * distributed lock
  * retry limit

### 5. MinIO Snapshot / Archive

* 存储：
  * snapshot export bundle
  * extraction raw artifacts
  * agent snapshot archive
* 不把普通长期记忆主记录写入 MinIO

### 6. Agent-Private Memory Foundation

* 为 agent 私有记忆增加 scope
* 主 agent 与 child/agent scope 开始分层
* 让后续 snapshot / sync 有真实基础

## Planned Extensions

* 路径级规则文件
* 用户级规则文件
* 更高级的 stale-memory trust check
* 更强的记忆检索排序/语义检索
* transcript/session ledger 数据库化
* 更完整的 agent memory 产品面
* 统一规则/记忆浏览 UI 或 CLI
* 多租户/跨项目隔离增强

## Definition of Done

* PostgreSQL / Redis / MinIO 三层分工清晰
* 长期记忆 durable persistence 成立
* 自动提取任务链成立
* agent 私有记忆基础成立
* 不破坏当前 session ledger 恢复链
* Focused pytest / ruff / mypy 通过
* Trellis contracts/docs 同步完成

## Technical Approach

* Layer 1:
  * `.coding-deepgent/RULES.md`
  * 继续保留文件型入口
* Layer 2:
  * PostgreSQL 主存储
  * 四类型长期记忆
  * 版本/审计/任务状态
* Layer 3:
  * 当前会话记忆继续走 session state / compact chain
* Layer 4:
  * transcript / compact / resume 继续走 JSONL ledger
* Redis:
  * 队列 / 防抖 / 锁 / worker 分发
* MinIO:
  * snapshot / archive / 大对象归档

## Out Of Scope

* transcript JSONL ledger 迁移到 PostgreSQL
* vector / embedding retrieval
* RabbitMQ / Kafka / NATS
* 全量多租户体系
* 路径级规则 / 用户级规则

## Technical Notes

* `.trellis/tasks/04-18-unified-context-memory-closeout/prd.md`
* `.trellis/spec/guides/planning-targets-guide.md`
* `.trellis/spec/guides/architecture-posture-guide.md`
* `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`
* `.trellis/spec/backend/session-compact-contracts.md`
* `coding-deepgent/src/coding_deepgent/memory/*`
* `coding-deepgent/src/coding_deepgent/sessions/*`
* `coding-deepgent/src/coding_deepgent/rules/*`

## Checkpoint

State:
- implementing

Implemented so far:
- Added SQLAlchemy-backed durable memory repository and schema creation.
- Added Redis-backed queue abstraction with in-memory fallback for tests.
- Added S3-compatible archive abstraction using boto3 for MinIO-compatible object storage.
- Added durable memory service with:
  - save/list/delete
  - extraction jobs
  - snapshot refresh jobs
  - agent scope foundation
- Added CLI surfaces:
  - `memory migrate`
  - `memory jobs`
  - `memory worker-run-once`
- Added focused backend tests for repository, queue/job flow, and CLI.

Verification so far:
- `pytest -q coding-deepgent/tests/test_memory_backend.py coding-deepgent/tests/test_memory_cli.py`
- `pytest -q coding-deepgent/tests/test_memory.py coding-deepgent/tests/test_memory_integration.py coding-deepgent/tests/test_memory_backend.py coding-deepgent/tests/test_memory_cli.py coding-deepgent/tests/test_tool_system_middleware.py coding-deepgent/tests/test_agent_runtime_service.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_runtime_foundation_contract.py`
- `ruff check ...`
- `mypy ...`
- live smoke against configured services:
  - `postgres=ok`
  - `queue=ok`
  - `archive=ok`

Boundary finding:
- Live service wiring required normalizing the PostgreSQL URL to the `psycopg` SQLAlchemy driver, correcting the configured database password, creating the target database, lowering Docker disk pressure for MinIO, and replacing the invalid uppercase bucket name with a valid S3-compatible bucket name.
