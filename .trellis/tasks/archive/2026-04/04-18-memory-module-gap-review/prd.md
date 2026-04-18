# brainstorm: memory module gap review

## Goal

基于当前 `coding-deepgent` 的记忆实现和 cc/Claude Code 的记忆相关源码，明确“记忆模块”目前已经覆盖的功能、还缺的具体功能，以及下一轮应该优先补哪一类功能。

## What I already know

* 当前 `coding-deepgent` 已经完成一轮 integrated memory closeout：
  * 四类型长期记忆 `user / feedback / project / reference`
  * `save_memory / list_memory / delete_memory`
  * bounded recall / render
  * `feedback` 对少量高价值动作直接生效
  * recovery/resume 可见面里已经分开显示 `Long-term memory` 和 `Current-session memory`
* 当前 `coding-deepgent` 的长期记忆仍然是 store-backed 的运行时能力，不是持久落盘 backend。
* 当前 `coding-deepgent` 仍没有自动提取长期记忆、子 agent 私有记忆、向量检索、后台维护。
* cc 侧长期记忆主线来自：
  * `src/memdir/*`
  * `src/services/SessionMemory/*`
  * `src/tools/AgentTool/agentMemory.ts`
  * `src/tools/AgentTool/agentMemorySnapshot.ts`
* cc 的长期记忆核心是：
  * 闭合四类型
  * 只保存不可推导信息
  * frontmatter + MEMORY.md 索引
  * 记忆老化/信任提醒
  * user/project/local 以及 agent memory scope
  * session memory 周期性提取与 agent memory snapshot

## Assumptions (temporary)

* 用户现在要的不是立即继续编码，而是先把“当前实现相对 cc 还差哪些功能”讲清楚。
* 本轮主要输出 gap review 和下一步目标选择，不一定直接进入实现。
* 评价标准以“用户能得到什么功能”为主，而不是是否逐字照搬 cc 源码。

## Open Questions

* 这套 planning 标准，是否直接升级成后续所有主线计划的默认准则？

## Requirements (evolving)

* 必须 source-backed，对照当前本地代码和 cc 相关源码/文档。
* 输出要按“具体功能差距”分组，不要只给术语。
* 需要明确：
  * 已对齐功能
  * 部分对齐功能
  * 明确缺失功能
* 必须把“上下文关联系统”和“记忆系统”合并讨论，而不是只看 memory 目录。
* 最后要给出 2–3 个可选的下一轮目标包络，并推荐一个。

## Acceptance Criteria (evolving)

* [ ] 给出当前记忆模块相对 cc 的功能差距清单
* [ ] 功能差距按具体用户收益分组，而不是抽象层次
* [ ] 给出下一轮目标的 2–3 个选项
* [ ] 给出推荐选项和理由

## Definition of Done (team quality bar)

* 结论写入 PRD
* 差距描述可直接转为后续任务范围
* 推荐方向清晰，不依赖口头记忆

## Out of Scope (explicit)

* 本轮不直接进入实现
* 本轮不重新做已经完成的 memory closeout
* 本轮不讨论 tutorial/reference 层 UI

## Technical Notes

* `.trellis/project-handoff.md`
* `.trellis/plans/coding-deepgent-h01-h10-target-design.md`
* `/tmp/claude-code-book/第二部分-核心系统篇/06-记忆系统-Agent的长期记忆.md`
* `/root/claude-code-haha/src/memdir/*`
* `/root/claude-code-haha/src/services/SessionMemory/*`
* `/root/claude-code-haha/src/tools/AgentTool/agentMemory.ts`
* `/root/claude-code-haha/src/tools/AgentTool/agentMemorySnapshot.ts`
* `coding-deepgent/src/coding_deepgent/memory/*`
* `coding-deepgent/src/coding_deepgent/sessions/session_memory.py`
* `coding-deepgent/src/coding_deepgent/sessions/long_term_memory.py`

## Research Notes

### Current local strengths

* Long-term memory types are already aligned to `user / feedback / project / reference`.
* Long-term memory has structured save/list/delete and bounded render.
* Feedback memories can already affect a few concrete actions, not only prompt text.
* Recovery/resume already shows long-term memory separately from current-session memory.

### Combined context + memory view

cc 实际上不是一个“单独的记忆模块”，而是一个组合系统：

* persistent instructions:
  * `CLAUDE.md`
  * `.claude/rules/*`
* long-term memory:
  * `memdir`
  * `MEMORY.md` + topic files
* current-session memory:
  * `SessionMemory`
* recovery / continuation context:
  * transcript
  * compact
  * resume brief
* dynamic context protocol:
  * attachments / queryContext / nested memory / relevant memories

当前本地对应物是：

* persistent instructions:
  * runtime base prompt + custom/append prompt
* long-term memory:
  * `memory/`
* current-session memory:
  * `sessions/session_memory.py`
* recovery / continuation context:
  * `sessions/` + compact/resume chain
* dynamic context protocol:
  * PromptContext + middleware-injected memory/todo/runtime context

Correction:

* Trellis specs / workflow / handoff are agent-side development scaffolding, not
  product-facing persistent instruction layers.
* They should not be treated as the product equivalent of cc `CLAUDE.md` or
  `.claude/rules/*`.

### Current local gaps vs cc

* No durable memory survives restart yet.
* No file-based memory entries or human-readable memory index.
* No explicit stale-memory trust/verification workflow at recall time.
* No smarter relevance selection beyond bounded deterministic recall.
* No automatic suggestion/extraction of durable memories from conversation.
* No per-agent memory scope and no agent snapshot/sync path.
* Current-session memory exists, but not the richer background extraction/update behavior cc has.

### Source-backed fit assessment

#### Already aligned enough

* closed four-type long-term memory model
* explicit “do not save derivable information” direction
* structured save / list / delete operations
* long-term memory vs current-session memory split
* some feedback memories can affect behavior directly

#### Partially aligned

* long-term memory retrieval:
  * local has bounded structured recall
  * cc has file index + topic-file recall + stronger trust/verification guidance
* session memory:
  * local has current/stale session-memory artifact and compact/resume assist
  * cc has richer thresholded/background extraction behavior
* memory visibility:
  * local shows long-term/current-session memory in recovery brief
  * cc has `/memory` browse/edit flow and plain markdown files

#### Clearly missing

* long-term memory survives restart in a durable user-visible store
* markdown memory files and a readable index entrypoint
* stronger stale-memory trust/verification flow before acting on recalled facts
* more selective / relevant memory retrieval when memory grows
* auto-suggested or auto-extracted durable memories from conversation
* per-agent memory scope and agent memory snapshots

### Feasible next goals

**Approach A: Durable And Auditable Memory**

* User-visible result:
  * remembered items survive restart
  * users can inspect/edit memory outside the running process
* Best when:
  * persistence and auditability matter most

**Approach B: Smarter Memory Use** (Recommended)

* User-visible result:
  * recalled memory is less likely to be stale, noisy, or over-applied
  * system gets better at picking the right memory for the current task
* Best when:
  * reliability is the current biggest concern

**Approach C: Automatic And Agent-Specific Memory**

* User-visible result:
  * system suggests or extracts memories by itself
  * child agents keep their own remembered context
* Best when:
  * the product is ready to become more autonomous

## Decision (ADR-lite)

**Context**

当前最大的混乱点不是“长期记忆有没有做”，而是：

* 产品内长期规则
* 长期记忆
* 当前会话记忆
* 恢复上下文

这三层在认知上还没有被收成一个统一模型，导致后续目标很容易混淆成“继续做 memory”而不是“完善整套上下文/记忆工程”。

**Decision**

下一轮继续方向先采用“统一模型”路线：

* 把 `产品内长期规则 + 长期记忆 + 当前会话记忆 + 恢复上下文` 作为一个整体系统来定义
* 不再只从 `memory/` 目录出发讨论
* 先把这四层的边界、顺序、职责、用户可见面收清，再决定下一轮实现目标
* 用户选择把 “正式建 Layer 1” 和 “收紧 Layer 2/3/4” 一起规划，不拆成两轮
* Layer 1 正式方向采用“文件型规则入口”。
* Layer 1 第一版范围采用“单一项目级规则文件”，不同时引入路径级或用户级规则作用域。
* Layer 1 内容边界先定为：
  * 规则文件存“长期行为约束”
  * 长期记忆存“长期可复用知识”
* 四层进入模型的固定顺序采用：
  1. 项目级规则文件
  2. 长期记忆
  3. 当前会话记忆
  4. 恢复上下文
* 层级可编辑性先定为：
  * Layer 1 / Layer 2：允许用户直接编辑
  * Layer 3 / Layer 4：系统维护为主

**Consequences**

* 优点：
  * 可以直接解决“上下文”和“记忆”混淆的问题
  * 后续任务能围绕统一边界拆验收目标
* 代价：
  * 范围比“只补 memory 功能”更大
  * 需要明确哪些内容仍然留到未来，例如 agent 私有记忆

## Unified Model Draft

### Layer 1: Product-Level Long-Term Rules

What it is:

* 用户或项目长期明确写给系统的规则
* 不应该被当作“系统自己总结出来的记忆”

What kind of things belong here:

* 长期工作方式
* 项目级约束
* 明确的人写规则

### Layer 2: Long-Term Memory

What it is:

* 系统跨会话积累的长期可复用知识
* 只保存不可推导的信息

What kind of things belong here:

* `user`
* `feedback`
* `project`
* `reference`

### Layer 3: Current-Session Memory

What it is:

* 当前这一次长会话的工作记忆/摘要
* 服务于 compact / continuation / resume

What kind of things belong here:

* 当前会话摘要
* 当前会话重点
* 当前会话压缩辅助信息

### Layer 4: Recovery Context

What it is:

* 从历史事实恢复“之前发生了什么”的上下文
* 不是长期规则，也不是长期记忆

What kind of things belong here:

* transcript
* compact
* resume brief
* continuation history

### Core Boundary Rule

* Layer 1 tells the system **how it should generally behave**
* Layer 2 tells the system **what durable knowledge it has learned**
* Layer 3 tells the system **what this current long conversation is about**
* Layer 4 tells the system **what has actually happened so far**

## Combined Planning Scope

What the next planning round must define together:

* Layer 1:
  * product-level long-term rules entrypoint
  * who can edit it
  * how it becomes model-visible
* Layer 2:
  * what remains long-term memory instead of becoming a rule
  * how long-term memory is recalled and trusted
* Layer 3:
  * what counts as current-session memory
  * how it refreshes and how it is shown
* Layer 4:
  * what belongs to transcript/compact/resume only
  * what must never be promoted into memory/rules automatically

## Layer 1 Direction

Chosen direction:

* use a file-based rules entrypoint as the formal Layer 1 surface
* first version uses one project-level rules file only

Why:

* easiest for users to understand
* keeps long-term rules visibly distinct from long-term memory
* gives the clearest audit surface before adding more structured execution logic
* avoids reopening nested/path-scoped rule resolution too early

### Content boundary

Put into the rules file:

* project-level long-term behavior constraints
* long-term collaboration/process requirements
* explicit engineering conventions the system should generally obey

Do not put into the rules file:

* user profile
* learned durable facts
* project decision background
* external references
* current-session summaries
* historical transcript facts

Short rule:

* rules file = long-term behavior constraints
* long-term memory = durable reusable knowledge

## Runtime Assembly Order

Fixed order:

1. project-level rules file
2. long-term memory
3. current-session memory
4. recovery context

Why:

* rules define how the system should generally behave
* long-term memory provides durable learned knowledge
* current-session memory provides the summary of this active long conversation
* recovery context restores what has actually happened so far, but should not override the prior three layers by default

## Editability Rule

User-editable layers:

* Layer 1: project-level rules file
* Layer 2: long-term memory

System-maintained layers:

* Layer 3: current-session memory
* Layer 4: recovery context

Reason:

* Layer 1 exists to capture explicit long-term rules from users/projects
* Layer 2 must remain correctable/auditable by users
* Layer 3 should stay a generated summary of the active long conversation
* Layer 4 should stay a factual recovery layer rather than a hand-edited narrative

## Planning Standard Draft

Future planning for this area should not jump directly from discussion to implementation.
Each follow-up task should be written in three explicit buckets before coding:

### 1. Acceptance Targets

What must be true for the task to count as complete.

Examples:

* what the user can now see
* what the system can now do
* what behavior is now prevented
* what boundary is now explicit

### 2. Planned Features

The concrete features that this task will implement now.

Examples:

* one new rule file entrypoint
* one recovery brief section
* one memory trust check

### 3. Planned Extensions

Future features that are intentionally not implemented in this task, but are already identified so planning stays coherent.

Examples:

* user-level rules scope
* durable memory persistence
* agent-private memory

### Rule

No new feature family should go straight into implementation until these three buckets are explicit:

* Acceptance Targets
* Planned Features
* Planned Extensions

This is intended to become a reusable planning rule, not a one-off memory-task note.

## Proposed Next Task

### Goal

把“产品内长期规则 + 长期记忆 + 当前会话记忆 + 恢复上下文”收成一个统一可执行模型，并把这四层正式落到产品边界里，而不是继续作为零散能力演化。

### Acceptance Targets

* 项目里有一个明确的、用户可直接编辑的项目级规则文件入口，且它不再和长期记忆混淆。
* 系统能清楚区分四层：
  * 项目级规则文件
  * 长期记忆
  * 当前会话记忆
  * 恢复上下文
* 进入模型的顺序被固定并经过测试：
  1. 项目级规则文件
  2. 长期记忆
  3. 当前会话记忆
  4. 恢复上下文
* 用户能清楚看见哪些内容属于长期记忆、哪些属于当前会话记忆、哪些属于恢复上下文。
* 当前会话记忆和恢复上下文不会再被误当成长期规则或长期记忆。
* 本轮结果足够清晰，后续功能可以直接围绕这四层继续扩展，而不用重新定义边界。

### Planned Features

* 增加一个单一项目级规则文件入口。
  * 建议路径：`.coding-deepgent/RULES.md`
* 在 prompt/context 组装里正式接入项目级规则文件，并保证它先于长期记忆进入模型。
* 把长期记忆、当前会话记忆、恢复上下文的显示与装配规则写成显式产品合同。
* recovery/resume 继续保持长期记忆与当前会话记忆分开显示，并补清项目级规则文件的可见性/存在性信号。
* 明确禁止自动把以下内容提升到错误层级：
  * transcript 历史事实 -> 长期规则
  * 当前会话摘要 -> 长期记忆
  * 恢复上下文 -> 长期记忆
* 增加 focused tests，覆盖：
  * 规则文件存在/缺失时的装配行为
  * 四层固定顺序
  * recovery/resume 可见面分层
  * 错层 promotion 不发生

### Planned Extensions

* 项目级规则文件之外的路径级规则
* 用户级规则文件
* 长期记忆的持久化落盘 backend
* 更聪明的长期记忆筛选与过时判断
* 自动建议或自动提取长期记忆
* 子 agent / agent 私有记忆
* 更统一的规则/记忆浏览与管理入口

### Out Of Scope

* 本轮不做路径级规则
* 本轮不做用户级规则
* 本轮不做长期记忆持久化 backend
* 本轮不做自动提取长期记忆
* 本轮不做 agent 私有记忆
