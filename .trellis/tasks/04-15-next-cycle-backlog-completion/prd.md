# brainstorm: next-cycle backlog completion

## Goal

在 `Approach A MVP` 已由 `Stage 29` 收口之后，补齐一个 canonical 的 `next-cycle` backlog 规划 PRD，明确当前主线应如何看待 `release validation / PR cleanup`、`Stage 30-36 reserve`、以及已经归档但仍与 canonical 口径冲突的 `30A/30B` 历史工作，避免未来继续在“reserve work 已实现”与“reserve 尚未需要”之间来回漂移。

## What I already know

* `project-handoff.md` 明确写明当前推荐方向是 `release validation / PR cleanup for Approach A MVP`，不是立即开启新的主线 stage。
* `project-handoff.md` 与 canonical roadmap 都明确写明 `Stage 30-36` 是 reserve only，只有在后续验证发现 concrete MVP gap 时才需要。
* `Stage 29` 的 PRD 已明确：
  - `H13/H14/H21/H22` deferred
  - `H01-H22` 有显式状态
  - `Stage 30-36 reserve` 当前不是必需
* archived `04-15-next-cycle-phase-1-backlog-decisions/prd.md` 已做过一次 next-cycle phase-1 决策：
  - 选择 `context pressure v2 / session-memory compaction`
  - 首 slice 选择 `Deterministic Assist`
* archived `30A/30B` 任务真实存在，并且 PRD 含有完成型 checkpoint：
  - `30A`: module upgrade contribution seams
  - `30B`: session-memory threshold local updates
* 但 `30A/30B` 与 handoff/roadmap 的 canonical 口径存在冲突：
  - 文档仍说 `Stage 30-36 reserve not currently required`
  - 任务层则显示 `30A/30B` 已实现并归档
* `cross-session memory` 仍是持续性产品要求，因此任何 next-cycle 选择都应说明是否直接/间接推进它。
* 当前 active task `04-15-next-cycle-backlog-completion/` 之前缺失 `prd.md`，现在需要先补齐需求基线。

## Assumptions (temporary)

* 这次任务是规划/清单收口任务，不是新功能实现任务。
* 需要一个 canonical next-cycle statement，说明“下一轮真正该做什么”与“哪些只是历史 reserve experiments”。
* `H13/H14/H21/H22` 不应被此任务静默重开，除非出现新的 source-backed PRD。
* `release validation / PR cleanup` 与 `next-cycle backlog planning` 需要明确先后关系，而不是混成同一类待办。

## Open Questions

* None after user choice:
  - treat `30A/30B` as historical reserve experiments
  - do not use them as the canonical starting point for current next-cycle mainline planning

## Requirements (evolving)

* 收集并对齐当前 next-cycle backlog 的 canonical 输入来源：
  - `project-handoff.md`
  - canonical roadmap
  - `Stage 29` PRD
  - archived `next-cycle phase 1 backlog decisions`
  - archived `30A/30B`
* 明确 `release validation / PR cleanup` 与 next-cycle implementation planning 的关系。
* 明确 `30A/30B` 的 canonical status：
  - accepted starting point
  - historical reserve experiment
  - superseded / non-canonical
* 给出 next-cycle backlog 的分层结果：
  - ready next
  - reserve / conditional
  - explicitly deferred until new product goal
* 任何被保留或推荐的 next-cycle band 都必须写明：
  - concrete function
  - concrete benefit
  - why now
  - whether it advances cross-session memory directly, indirectly, or not at all
* 将 `30A/30B` 归类为 historical reserve experiments：
  - 保留 archive 证据
  - 不作为当前 canonical next-cycle 起点
  - 不以它们的已实现状态推翻 handoff/roadmap 对 `Stage 30-36 reserve` 的 current wording

## Acceptance Criteria (evolving)

* [x] 当前 next-cycle backlog 的 canonical 输入来源已列清。
* [x] `30A/30B` 的 canonical status 已被明确记录。
* [x] `release validation / PR cleanup` 与 next-cycle implementation planning 的关系已被明确记录。
* [x] 存在一个清晰的 next-cycle backlog 分层结果。
* [x] deferred / reserve / ready-next 的边界清晰，不会与 MVP closeout 口径冲突。

## Research Notes

### Canonical input set

* `project-handoff.md`:
  - current next recommended task is `release validation / PR cleanup for Approach A MVP`
  - `Stage 30-36 reserve` is not currently required
  - `H13/H14/H21/H22` remain in the next-cycle backlog unless reopened by a new source-backed PRD
* `coding-deepgent-cc-core-highlights-roadmap.md`:
  - `H13/H14/H21/H22` are deferred
  - `Stage 29` is the MVP deferred-boundary closeout
  - `Stage 30-36` are reserve-only for concrete MVP gaps
* `Stage 29` PRD:
  - MVP closeout is complete
  - next-cycle backlog exists, but reserve work should not be treated as required
* archived `next-cycle phase 1 backlog decisions` PRD:
  - if implementation planning later resumes, the recommended first band is `context pressure v2 / session-memory compaction`
  - the recommended first slice is `Deterministic Assist`
* archived `30A/30B` PRDs:
  - represent real reserve-band implementation experiments
  - do not by themselves overrule current canonical handoff/roadmap wording

### Current canonical tension

* `Stage 29` PRD and `project-handoff.md` both say `Stage 30-36 reserve` is not currently required.
* archived `30A/30B` show real implementation work happened in that reserve band.
* User decision for this task: keep `30A/30B` as historical reserve experiments rather than promoting them into the current canonical next-cycle entrypoint.

### Consequence of the chosen boundary

* Current canonical next step remains:
  - `release validation / PR cleanup for Approach A MVP`
* Current canonical next-cycle planning should not assume:
  - `30A/30B` are the accepted baseline
  - `Stage 30+` already became the real active mainline
* `30A/30B` remain useful as:
  - evidence
  - reusable design input
  - historical experiments that may inform a future reopened PRD
* `30A/30B` should not be treated as:
  - binding product direction
  - proof that Stage 30-36 are now canonically required

### Canonical backlog layering

**Ready next**

* `release validation / PR cleanup for Approach A MVP`
  - concrete function:
    - run a broader validation pass when cost is acceptable
    - review/stage accumulated Stage 18-29 work
    - update PR `#220` or prepare the next PR boundary
  - concrete benefit:
    - verifies that the completed MVP closeout still holds under a broader check pass
    - reduces ambiguity before any new implementation stage is reopened
  - why now:
    - this is the explicit next recommendation in `project-handoff.md`
    - it preserves the Stage 29 closeout discipline
  - cross-session memory impact:
    - indirect only

**Conditional next-cycle implementation candidate**

* `context pressure v2 / session-memory compaction`
  - concrete function:
    - extend the current `compact + sessions + memory` seam with a bounded session-memory-assisted continuity path
  - concrete benefit:
    - improves context-efficiency and cross-session continuity without reopening coordinator/mailbox/platform breadth
  - why later, not now:
    - archived phase-1 backlog planning already recommends this direction
    - but current handoff still places release validation/PR cleanup ahead of any new implementation restart
  - cross-session memory impact:
    - direct
  - current canonical interpretation:
    - best candidate if implementation planning resumes after closeout validation

**Reserve / conditional**

* `Stage 30-36 reserve` generally
  - concrete function:
    - optional follow-on hardening or experiments if validation finds a concrete MVP gap
  - concrete benefit:
    - preserves space for deeper follow-on work without forcing it into the current mainline
  - why not now:
    - canonical docs still say reserve is not currently required
  - cross-session memory impact:
    - depends on the reopened PRD
* archived `30A/30B`
  - concrete function:
    - historical experiments around contribution seams and session-memory threshold updates
  - concrete benefit:
    - reusable evidence and design input if a future PRD reopens this band
  - why not now:
    - user chose not to promote them into the canonical entrypoint
    - they conflict with current reserve wording if treated as active baseline
  - cross-session memory impact:
    - direct, but non-canonical for the current next step

**Explicitly deferred until new product goal**

* `H13 Mailbox / SendMessage`
* `H14 Coordinator keeps synthesis`
* `H21 Bridge / remote / IDE control plane`
* `H22 Daemon / cron / proactive automation`
  - concrete function:
    - broader multi-agent, remote, or proactive runtime expansion
  - concrete benefit:
    - meaningful only when the product explicitly reopens those bands
  - why not now:
    - Stage 29 and the roadmap keep them deferred out of the current MVP path
  - cross-session memory impact:
    - not the current priority driver

## Decision (ADR-lite)

**Context**: Archived `30A/30B` contain completed implementation checkpoints, but current handoff/roadmap language still says `Stage 30-36` are reserve-only and not currently required. The task needs one explicit rule for future planning so the repo stops oscillating between these two signals.

**Decision**: Treat `30A/30B` as historical reserve experiments. Preserve them in archive and use them as optional evidence only, not as the canonical starting point for current next-cycle mainline planning.

**Consequences**:

* `project-handoff.md` and the canonical roadmap remain the current source of truth for what is active next.
* `release validation / PR cleanup` stays ahead of any new implementation-stage restart.
* A future next-cycle implementation may still reuse ideas from `30A/30B`, but only through a fresh source-backed PRD that explicitly reopens the direction.
* This avoids silently promoting reserve experiments into canonical product direction.

## Technical Approach

* Keep this task as a planning/documentation ledger, not an implementation task.
* Use `project-handoff.md` as the primary current-state router:
  - active next work = validation / PR cleanup
  - later implementation candidate = bounded next-cycle planning
* Treat archived `next-cycle phase 1 backlog decisions` as advisory input for a later implementation restart, not as a current-state override.
* Treat archived `30A/30B` as optional evidence only.

## Implementation Plan (planning-only)

* Step 1: keep canonical next action fixed on `release validation / PR cleanup`.
* Step 2: if validation later confirms the MVP closeout remains solid, reopen implementation planning through a fresh source-backed PRD.
* Step 3: when implementation planning is reopened, start from:
  - `context pressure v2 / session-memory compaction`
  - first slice: `Deterministic Assist`
  - optionally reuse `30A/30B` as evidence, but not as a binding baseline

## Definition of Done (team quality bar)

* Decision captured with evidence
* Scope and non-goals are explicit
* Follow-on implementation can start from this PRD without re-deriving the backlog boundary

## Out of Scope (explicit)

* 直接实现任何 next-cycle 产品代码
* 自动重开 `Stage 30+` 的实现工作
* 修改 `Approach A MVP` 边界
* 为 tutorial/reference layer 补做无关规划

## Technical Notes

* Task dir: `.trellis/tasks/04-15-next-cycle-backlog-completion`
* Canonical docs to inspect:
  - `.trellis/project-handoff.md`
  - `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
  - `.trellis/tasks/archive/2026-04/04-15-stage-29-deferred-boundary-adr-mvp-release-checklist/prd.md`
  - `.trellis/tasks/archive/2026-04/04-15-next-cycle-phase-1-backlog-decisions/prd.md`
* Historical reserve docs to inspect:
  - `.trellis/tasks/archive/2026-04/04-15-stage-30a-module-upgrade-contribution-seams/prd.md`
  - `.trellis/tasks/archive/2026-04/04-15-stage-30b-session-memory-threshold-local-updates/prd.md`
* Recent reconciliation already added reserve-policy notes to archived `30A/30B` task metadata so this task can build on that evidence rather than rediscover the conflict.
