# brainstorm: memory runtime discussion

## Goal

讨论 `coding-deepgent` 在当前 H07 基础之上，下一层 memory runtime 应该优先补哪一类能力，并先拍板边界，避免 memory / session / compact / subagent 再次混成一层。

## What I already know

* 当前 H07 已完成的主线已从旧 namespace 模型推进为四类型长期记忆：`user / feedback / project / reference`。
* 当前长期记忆已具备：`save_memory`、`list_memory`、`delete_memory`、store-backed save/list/delete/recall、`MemoryContextMiddleware`、bounded recall、quality policy。
* 当前 `feedback` 已不只是 prompt recall；它已经能通过 `ToolGuardMiddleware` 阻断三类高风险动作：commit 前未 lint、依赖变更未确认、generated 路径直改。
* `project-handoff` 已明确：cross-session memory 是产品要求，但 richer `session-memory extraction` 与 `agent-memory snapshot runtime` 仍 deferred。
* 当前仓库已经存在 `sessions/session_memory.py`，说明系统已经有一层 session-memory artifact 机制，且它会参与 recovery brief、compact assist、compact summary update。
* 当前 `memory/policy.py` 已增强：过短、重复、transient task/session state、可推导项目信息、相对日期 project memory 都会被拒绝。
* 现有设计文档明确要求 memory 不应退化成 knowledge dump，也不应和 todo/task/session state 混放。

## Assumptions (temporary)

* 这轮先讨论架构/产品边界，不直接进入实现。
* 当前最值得讨论的不是“要不要 memory”，而是“下一层 richer memory 应该先增强哪种 runtime effect”。
* 这轮要区分至少三层：long-term durable memory、session-memory artifact、subagent/agent-local snapshot。

## Open Questions

* “整个记忆模块一次性完成” 的包络，到底是：
  * 只收 long-term memory，
  * 还是把 session-memory / resume / recovery visibility 一起收掉，
  * 还是连 durable backend / auto-extraction / subagent memory 也一起做？

## Requirements (evolving)

* 保持 memory / todo / task / session / compact 的边界清晰。
* 讨论必须落到“expected effect + local target + out-of-scope”。
* 新方案必须说明对 cross-session continuity 是直接、间接还是没有帮助。
* 若涉及 richer runtime，必须先说明为什么值得增加复杂度。
* 长期记忆核心类型收敛为闭合集：`user / feedback / project / reference`。
* `local` 不再作为长期记忆核心模型的一部分；若保留，仅作为独立的 machine-local note 概念。

## Acceptance Criteria (evolving)

* [x] 明确下一轮 memory 讨论的主问题，不把三个子问题混在一起。
* [x] 给出 2-3 个可选方向及其边界。
* [x] 形成一个推荐方向，并说明为什么现在先讨论它。
* [x] 长期记忆与当前会话记忆在 product surface 中明确分层。
* [x] 长期记忆支持 save / list / delete / recall / feedback enforcement。
* [x] recovery/resume 可见面能同时显示长期记忆与当前会话记忆。
* [x] C 方案后续计划已写入文档，并以功能语言描述。

## Definition of Done (team quality bar)

* 形成清晰讨论结论并写入任务 PRD。
* 边界、收益、风险、out-of-scope 明确。
* 如果后续进入实现，按 Trellis task workflow 配置相关 spec context。

## Out of Scope (explicit)

* 本轮不直接修改 `coding-deepgent` 代码。
* 本轮不重新打开 embeddings/vector recall。
* 本轮不直接重开 H13/H14 多 agent 协调实现。

## Technical Notes

* `.trellis/project-handoff.md`
* `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
* `.trellis/plans/coding-deepgent-h01-h10-target-design.md`
* `coding-deepgent/src/coding_deepgent/memory/*`
* `coding-deepgent/src/coding_deepgent/sessions/session_memory.py`
* `coding-deepgent/src/coding_deepgent/tool_system/middleware.py`
* `coding-deepgent/tests/test_memory.py`
* `coding-deepgent/tests/test_memory_integration.py`
* `coding-deepgent/tests/test_tool_system_middleware.py`

## Decisions

* 2026-04-18: 采用方案 A。`local` 不进入长期记忆核心类型系统；长期记忆对齐目标收敛为 `user / feedback / project / reference` 四类型。
* 2026-04-18: `feedback` 作为最优先亮点先收敛。最小结构为 `rule / why / how_to_apply / source`，用于保存用户纠正或确认过的行为规则；render/recall 优先级高于普通 `project` memory。
* 2026-04-18: 后续 memory 亮点按收益最大优先排序，不要求与旧方案或旧数据兼容；当长期边界更干净时，优先选择更适合未来演进的结构而不是兼容桥接。
* 2026-04-18: `project` 作为第二优先亮点。最小结构为 `fact_or_decision / why / how_to_apply / effective_date / source`，只保存非代码可推导的项目事实、决策背景和长期约束；涉及时间时必须使用绝对日期。
* 2026-04-18: `reference` 作为第三优先亮点。最小结构为 `label / pointer / purpose / how_to_apply / source`，专门承载 repo 之外但长期有用的外部系统入口；不与 `project` 决策或 repo 内部路径混用。
* 2026-04-18: 采用 Approach B。把“整个记忆模块”定义为两层并一次性收口：
  * long-term memory
  * session-memory artifact
* 2026-04-18: C 方案不进入本轮实现，但必须把后续计划写进文档，而且用功能语言描述用户最终会获得什么，不写成架构术语清单。

## Research Notes

### Current local state

* Long-term memory:
  * four-type contract exists
  * save/list/delete tools exist
  * recall/render exists
  * feedback enforcement exists for three high-value actions
* Session-memory:
  * separate `session_memory` artifact exists
  * already participates in recovery brief, compact assist, compact-summary refresh
* Not done:
  * long-term memory visibility in recovery/resume surface
  * unified “memory module” contract that explains long-term vs session-memory together
  * durable backend for long-term memory
  * auto extraction
  * subagent/agent-memory snapshot

### Feasible approaches here

**Approach A: Long-Term Memory Closeout**

* How it works:
  * finish only long-term memory module
  * include four-type schema, management tools, feedback enforcement, recall/render cleanup
* Pros:
  * smallest delivery
  * low risk
* Cons:
  * “entire memory module” remains incomplete because session-memory is still a separate unfinished seam

**Approach B: Integrated Memory Closeout** (Recommended)

* How it works:
  * treat memory module as two explicit layers:
    * long-term memory
    * session-memory artifact
  * finish both together at the product boundary
  * include visibility in recovery/resume so the user can inspect remembered state
  * keep durable backend, auto extraction, and subagent memory out of scope
* Pros:
  * matches current product reality
  * gives one coherent memory boundary
  * high user-visible payoff without reopening too much infra
* Cons:
  * bigger than long-term-only closeout

**Approach C: Full Future Memory Platform**

* How it works:
  * do integrated memory plus durable backend, auto extraction, and subagent/agent memory
* Pros:
  * most complete long-term vision
* Cons:
  * too broad for one safe pass now
  * high risk of mixing multiple unfinished domains

## Chosen Scope

### In Scope For One-Shot Completion

* Long-term memory:
  * four-type memory model
  * save / list / delete
  * recall / render
  * feedback-driven behavior rules
* Session-memory:
  * explicit boundary vs long-term memory
  * recovery/resume visibility
  * stale/current status visibility
  * compact/resume continuity kept coherent with long-term memory
* Product visibility:
  * user can see what the system remembers
  * user can distinguish long-term memory from current-session memory
* Documentation:
  * current memory module boundary becomes explicit in Trellis docs
  * future C-scope memory work is written down as a function-first roadmap

### Out Of Scope For This Pass

* durable long-term memory backend
* auto extraction from conversation into memory
* subagent/agent-private memory
* vector/embedding retrieval
* background memory maintenance

## Technical Approach

* Long-term memory:
  * four-type structured memory model
  * bounded store-backed save/list/delete/recall
  * feedback rules may directly block a few high-value actions through existing tool guard surfaces
* Current-session memory:
  * remains a separate session artifact
  * stays visible in recovery/resume as “Current-session memory”
* Integration:
  * long-term memory snapshot is written into runtime state and carried into recorded session snapshots
  * recovery brief renders long-term memory and current-session memory as two separate sections
* Documentation:
  * current memory module boundary updated in Trellis specs
  * future C-scope memory path recorded as a function-first roadmap

## Checkpoint

State:
- terminal

Verdict:
- APPROVE

Implemented:
- Four-type long-term memory (`user / feedback / project / reference`) is the active product contract.
- Memory management tools now support save, list, and delete.
- `feedback` memory can directly block selected high-value actions.
- Recovery/resume now shows a separate `Long-term memory:` section and a separate `Current-session memory:` section.
- Session snapshots preserve the long-term memory visibility snapshot alongside current-session memory.
- Future larger memory work was documented in function-first language.

Verification:
- Focused memory/session/CLI/runtime tests passed.
- `ruff check` passed on touched memory/session/runtime files and tests.
- `mypy` passed on touched memory/session/runtime files and tests.
