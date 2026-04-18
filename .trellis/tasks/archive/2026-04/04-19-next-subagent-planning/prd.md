# brainstorm: next subagent planning

## Goal

在 batch1/batch2 之后，决定 `coding-deepgent` 子 agent 主线下一步应该推进哪一类能力，并把它收束成一条清晰的后续实现方向，而不是同时打开 H12 深化、H13 mailbox、H14 coordinator 三条线。

## What I already know

* 当前 canonical roadmap 里：
  * `H11 Agent as tool and runtime object` = `implemented`
  * `H12 Fork/cache-aware subagent execution` = `implemented-minimal`
  * `H13 Mailbox / SendMessage` = `deferred`
  * `H14 Coordinator keeps synthesis` = `deferred`
* 本地最近两批已完成的方向是：
  * batch1: `max_turns` / model routing / built-in catalog / local custom agents / fork continuity / resume foundation
  * batch2: background subagent runtime / progress + notification / queued follow-up input / plugin-provided agents
* 现有 repo 和 spec 已经明确：
  * background subagent runs 现在是 bounded local slice
  * 还不是 mailbox / coordinator / team runtime
  * 若要继续做 team execution，必须走新的 task/subagent spec，而不是继续往 `run_subagent` 上叠字符串参数
* 现有 H11/H12 source-backed research 里，下一层尚未充分对齐的主要块是：
  * async lifecycle deeper details: abort cascade / cleanup inventory / kill semantics
  * richer fork/cache parity: byte-identical prefix, cache-safe summary/fork reuse
  * H13 mailbox / SendMessage
  * H14 coordinator synthesis

## Assumptions (temporary)

* 用户现在说“去计划”，指的是规划下一阶段，而不是立刻继续编码。
* 当前最有价值的规划不是列一大串 backlog，而是先决定下一条主线。
* 选择会直接影响后续 task topology，因此应该先做方向收敛。

## Open Questions

* （resolved）H12 做完时继续只保留显式 `run_fork`，不额外加入隐式一键分叉入口。

## Requirements (evolving)

* 输出应明确给出 2–3 条下一阶段可选路线。
* 每条路线都要说明：
  * 解决什么问题
  * 为什么现在值得做
  * 对后续 H13/H14 的影响
  * 主要风险
* 推荐顺序应基于当前 repo 已有基础，而不是抽象上“更高级”。
* 最终要收敛成一条下一步主线。
* 用户已选择：下一阶段继续深化 H12，而不是切到 H13/H14。
* 用户已选择：H12 下一条切片采用 `completion pack`，不拆成单独的 background-fork 或 summary-only 路线。
* 用户已选择：不需要兼容旧方案或旧数据，应优先长远干净边界。
* 用户已进一步选择：这条线按最大完成度收口，包含后台分支、自动状态、收尾、停止、恢复稳健性、路径/工作区稳健性。
* 用户已选择：入口层继续只保留显式 `run_fork`，不新增隐式 fork 入口。

## Acceptance Criteria (evolving)

* [ ] 能给出 2–3 条具体路线，而不是泛泛 backlog。
* [ ] 能说明每条路线和当前 H11/H12/H13/H14 边界的关系。
* [ ] 能明确给出推荐路线和理由。
* [ ] 能通过一个单选问题收敛方向。
* [ ] 能在 H12 路线下继续收敛出第一条实现切片。
* [ ] 能在 `H12 completion pack` 下继续收敛出明确 scope boundary。
* [x] 能在“最大完成度收口”前提下收敛出最后一个入口层决定。

## Definition of Done (team quality bar)

* 结论基于当前 roadmap、现有 batch1/batch2、和已有 H11/H12 research。
* 不把 H13/H14 当成“默认下一步”，除非能说明为什么当前基础已经足够。
* 明确列出 out-of-scope，避免一次打开多条高耦合主线。
* 用户已选方向要立即记录进 PRD，而不是停留在会话里。
* 用户已明确“不需要兼容旧方案/旧数据”，所以后续方案应默认允许直接替换旧局部抽象。
* 用户已明确要按更完整交付收口，而不是先做最小可用版。
* 用户已明确继续只保留显式 `run_fork`，因此实现不应分散到多种 fork 入口形态。

## Out of Scope (explicit)

* 本轮不直接改代码。
* 不再并行规划 H13/H14 的完整实施细节。
* 不重新审计全部 H01-H22。

## Technical Notes

* Local docs inspected:
  * `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
  * `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md`
  * `.trellis/tasks/04-17-l5b-deferred-boundary-adr-refresh/prd.md`
  * `.trellis/tasks/04-18-subagent-batch1-parity-implementation-plan/prd.md`
  * `.trellis/tasks/04-19-subagent-batch2-runtime-implementation-plan/prd.md`
  * `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`
  * `.trellis/spec/backend/task-workflow-contracts.md`

## Research Notes

### Constraints from our repo/project

* H11 已经不是“有没有 subagent”，而是已经有真实 runtime、resume、background local runs。
* H12 还是 minimal，不适合直接宣称 full parity。
* foundation contracts 明确禁止把 mailbox/coordinator/team semantics 继续堆进 `run_subagent`。
* 这意味着若切 H13/H14，要有新的 surface，而不是继续 patch `run_subagent`.

### Feasible approaches here

**Approach A: 继续深化 H12 / lifecycle correctness** (Recommended)

* How it works:
  * 继续留在 H11/H12 线，补最接近现有基础的缺口：
    * background fork workers
    * abort / cleanup / kill semantics
    * cache-safe summary / fork reuse
* Pros:
  * 复用当前 batch1/batch2 已铺好的 runtime/seams
  * 风险最低
  * 能把“已有很多功能点”收成更可靠的一条线
* Cons:
  * 仍然没有真正进入多 agent 协作
  * 用户感知的新范式不如 mailbox/coordinator 大

**Approach B: 正式切到 H13 mailbox / SendMessage**

* How it works:
  * 新开 task-linked mailbox store + 显式 message surface
  * 让多个 subagent 之间能发消息，但暂时不做 coordinator
* Pros:
  * 真正跨进 multi-agent readiness
  * 给后续 H14 coordinator 打底
* Cons:
  * 需要新 surface/new spec，不是当前 `run_subagent` 上的小延伸
  * 容易把 scope 拉大

**Approach C: 直接规划 H14 coordinator**

* How it works:
  * 先定义 coordinator/worker 拓扑、汇总职责、任务分工边界
  * mailbox 作为 coordinator 依赖面一起规划
* Pros:
  * 直接面对最终多 agent 架构
  * 长期路线最清楚
* Cons:
  * 以当前基础看最容易变成高层设计先行
  * 没有 mailbox 作为中间层时，落地风险最大

## Decision (ADR-lite)

**Context**: batch1/batch2 已经把 H11 和 H12 minimal slice 做到一个足够可继续深化的阶段，但 foundation contracts 仍明确要求不要把 mailbox/coordinator/team semantics 继续堆进 `run_subagent`。

**Decision**: 下一阶段优先继续深化 H12，不切到 H13 mailbox，也不先做 H14 coordinator 规划。

**Consequences**:

* 近期会优先补 fork/cache-aware execution 和 fork lifecycle correctness。
* H13/H14 继续维持 deferred，不在这一步并行打开。
* 用户已进一步选择 `H12 completion pack`，即 background fork workers 和 cache-safe summary / fork reuse 一起推进。
* 后续实现可以直接替换旧局部设计，不要求为旧方案/旧数据加桥接层。
* 用户已进一步要求按更完整交付收口，因此这包默认还包含 abort / cleanup / kill semantics 与 resume/path hardening。
* 用户已进一步选择继续只保留显式 `run_fork`，因此 H12 收口将聚焦单一 fork surface，而不是双入口并存。

## Technical Approach

下一阶段以 `H12 completion pack` 为单一实现主线，范围包括：

* background fork workers
* cache-safe summary / fork reuse
* abort / cleanup / kill semantics
* resume / path / worktree hardening

并保持两条硬边界：

* 不为旧方案或旧数据增加兼容层
* 不新增隐式 fork 入口，继续只保留显式 `run_fork`

## Expansion Sweep

1. Future evolution
* 如果很快会做多 agent，当前选择应避免把 H12 patch 成伪 coordinator。
* 如果短期仍想先打牢 runtime，应该继续沿 H11/H12 的 lifecycle/correctness 线收敛。

2. Related scenarios
* background fork workers 和 cache-safe summary 是当前 batch2 的自然延伸。
* mailbox / SendMessage 一旦进入，就会牵动 task store、state model、runtime surface。

3. Failure / edge cases
* 如果过早进入 H13/H14，容易把 `run_subagent` 扭成一层临时兼容壳。
* 如果只继续补 H12，也要避免永远停留在“更完整的单机 child runtime”而不进入真正协作。
