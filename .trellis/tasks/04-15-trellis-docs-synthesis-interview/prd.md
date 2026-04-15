# brainstorm: trellis docs synthesis and interview expansion

## Goal

围绕当前 `coding-deepgent` 主线的 `.trellis/` 文档体系，整理总结已有 Trellis 文档、确认这种“文档收束/总结”是否符合 Trellis 官方推荐实践，并设计一套通过采访用户进一步补充 Trellis 文档的工作方式，使后续规范建设更系统、更可持续。

## What I already know

* 用户的下一步任务意图是：
  * 整理总结已有的 Trellis 文档
  * 通过采访的形式进一步补充 Trellis 文档
  * 联网学习 Trellis 用法
* 用户明确给出了官方参考入口：
  * `https://docs.trytrellis.app/zh/guide/ch07-writing-specs`
* 用户明确给出了主要社区参考方向：
  * Linux Do
* 当前仓库的主线已经明确为 `coding-deepgent/` + `.trellis/`。
* 当前 `.trellis/` 已包含：
  * `workflow.md`
  * `project-handoff.md`
  * `plans/`
  * `spec/backend/*`
  * `spec/guides/*`
  * `workspace/`
* 当前 Trellis 文档经过前面几轮收口，已经开始承担：
  * 主线范围定义
  * 后端结构规范
  * 质量规范
  * cc 对齐方法
  * staged execution 方法
* Trellis 官方“规范编写指南”明确推荐：
  * `index.md` 作为入口，列出规范文件及状态
  * 每个 spec 文件只专注一个主题
  * 从**实际代码中提取模式**来填充 spec
  * spec 应该**持续演进**，而不是一次写完
* Linux Do 上的实际使用反馈强调：
  * Trellis 的价值在于把团队约定整理成结构化文档并按需注入
  * 预生成 spec 往往会有空白，必须后续手工补全
  * 训练/推广场景里，团队确实会再写“培训文档”或“介绍文档”，但这通常是补充层，不应替代原子化 spec

## Assumptions (temporary)

* 这个任务首先是“规范设计/工作流设计”问题，而不是立即大规模改写全部 Trellis 文档。
* “采访”更像是一种 requirements/spec discovery 方法，需要被写成 Trellis 内的可复用流程，而不是临时聊天习惯。
* 官方 Trellis 文档很可能强调如何写 spec，而不一定直接给出“采访式补充 spec”的现成模板；如果没有，需要结合官方原则做本地化设计。

## Open Questions

* None. User delegated future low-risk process choices to the recommended option.

## Requirements (evolving)

* 研究 Trellis 官方文档，确认现有 `.trellis/` 文档整理/总结是否符合推荐实践。
* 研究 Linux Do 上与 Trellis 使用、spec 编写、项目落地相关的高价值讨论。
* 盘点当前仓库已有 Trellis 文档的类型、职责、重叠区与空白区。
* 优先产出一份 Trellis 文档地图，说明 `.trellis/` 内各层文档的职责、入口关系、阅读顺序与修改落点。
* 这份文档地图需要同时服务：
  * 项目维护者：理解 `.trellis/` 的职责分层与长期维护方式
  * AI agent：知道先读什么、改哪里、如何把新信息写回正确文档
* 文档地图采用**单独 guide** 形态，而不是仅靠现有 `index.md` 承载。
* 文档地图初版只覆盖当前 `coding-deepgent` 主线高价值 Trellis 文档，不把 `.trellis/` 所有脚本/配置/内部文件都画进去。
* 设计一套“采访式补充 Trellis 文档”的流程，并写入 Trellis。
* 该流程应能指导后续 agent：
  * 先读现有 Trellis
  * 找空白
  * 通过逐步采访补足事实
  * 将结果落到正确 Trellis 文档

## Acceptance Criteria (evolving)

* [x] PRD 记录了官方文档对 spec 编写/维护的关键建议。
* [x] PRD 记录了 Linux Do 上与 Trellis 落地相关的高价值经验。
* [x] 当前 `.trellis/` 文档被分类整理，并识别出高价值空白区。
* [x] 形成一份高可读的 Trellis 文档地图，解释当前 `.trellis/` 文档体系。
* [x] 形成一套采访式补充 Trellis 文档的可执行流程。
* [x] 明确哪些 Trellis 文档应继续汇总整理，哪些应保持原子化。

## Definition of Done (team quality bar)

* Docs/notes updated if behavior changes
* Workflow remains coherent for future sessions
* New guidance is specific enough for repeated use

## Out of Scope (explicit)

* 立即重写全部 `.trellis/` 文档
* 为了“看起来完整”而填充低价值 spec 模板
* 脱离 `coding-deepgent` 主线去服务教程/reference 层

## Technical Notes

* New child task:
  * `.trellis/tasks/04-15-trellis-docs-synthesis-interview`
* Parent task:
  * `.trellis/tasks/04-15-trellis-spec-consolidation`
* Likely target docs:
  * `.trellis/workflow.md`
  * `.trellis/spec/guides/index.md`
  * `.trellis/spec/backend/index.md`
  * new guide for Trellis doc map
  * possibly a new guide for interview-driven doc expansion

## Current Trellis Doc Map

### Workflow / Coordination

* `.trellis/workflow.md`
  * 总工作流、读取顺序、开发过程、阶段执行协议
* `.trellis/project-handoff.md`
  * `coding-deepgent` 主线的最小恢复入口

### Planning / Product Memory

* `.trellis/plans/index.md`
  * 长期计划入口
* `.trellis/plans/*.md`
  * 主线 roadmap / reconstructed master plan / runtime foundation specs

### Specs / Norms

* `.trellis/spec/backend/*`
  * 后端主线规范，已有部分 Active 文档
* `.trellis/spec/guides/*`
  * 思维指南、cc 对齐、staged execution、mainline scope
* `.trellis/spec/frontend/*`
  * 目前大多仍是模板/占位

### Session Memory / Records

* `.trellis/workspace/index.md`
  * 工作记录总索引
* `.trellis/workspace/<developer>/journal-N.md`
  * 会话记录

## Current Gaps

* 缺少一份“如何理解整个 `.trellis/` 文档体系”的高层地图文档。
* 缺少一份“如何通过采访补 spec”的明确流程文档。
* backend 规范已经开始具体化，但 frontend 规范仍然大量空白。
* workflow、handoff、spec、plans、workspace 之间的职责关系，对新协作者仍然不够一眼看懂。

## Research Notes

### Official Trellis docs say

Source:

* `https://docs.trytrellis.app/zh/guide/ch07-writing-specs`

Key points:

* `index.md` should be the entrypoint listing spec files and their status.
* Each spec file should focus on one topic.
* Specs should be filled from actual code and actual conventions, not ideals.
* Good specs are concrete, with code and reasons.
* Specs should evolve continuously after bugs, better patterns, and team decisions.

Inference for this repo:

* “整理总结已有 Trellis 文档” is aligned with official guidance **only if** it means:
  * clarifying entrypoints
  * reducing overlap
  * improving categorization
  * filling blanks from actual practice
* It is **not** aligned if it means replacing topic docs with one giant summary file.

### Linux Do usage signals

Source examples:

* `https://linux.do/t/topic/1850897`
* `https://linux.do/t/topic/1803999`
* `https://linux.do/t/topic/1868950`

High-signal takeaways:

* Teams use Trellis to turn implicit habits into structured project memory/specs.
* People often need extra explanation/training docs because the raw Trellis structure is powerful but not self-explanatory.
* Empty or partially filled specs are a common pain point; users expect later补全.
* Too much process or too many questions can increase token/interaction cost, so补全文档的流程应该是渐进式、按需、逐主题推进。

### Constraints from our repo/project

* Current `.trellis/` already has multiple useful docs, but navigation and role boundaries are still not fully summarized.
* We just moved more project knowledge into Trellis, so this is the right moment to create a cleaner synthesis layer.
* The repo mainline is `coding-deepgent`, so the synthesis/interview flow should serve product/mainline docs first, not tutorial/reference docs.

### Feasible approaches here

**Approach A: Index-first synthesis + gap-driven interview** (Recommended)

* How it works:
  * Keep existing Trellis docs as atomic source-of-truth.
  * Add or improve a small number of synthesis/index docs to explain roles, boundaries, and reading order.
  * Build an interview workflow that finds one missing area at a time, asks targeted questions, then writes the answer into the correct topic doc.
* Pros:
  * Matches official Trellis guidance best.
  * Keeps docs maintainable.
  * Works well for iterative AI/human collaboration.
* Cons:
  * Requires discipline to avoid “summary doc” drift.

**Approach B: Big Trellis handbook first**

* How it works:
  * Create one large Trellis handbook that summarizes everything, then update topic docs later.
* Pros:
  * Easy for humans to skim initially.
* Cons:
  * Conflicts with official topic-first guidance.
  * High drift risk.
  * Easy to become a second source-of-truth.

**Approach C: Interview-first, summarize later**

* How it works:
  * Start interviewing immediately, capture answers into PRDs or notes, then reorganize docs afterward.
* Pros:
  * Fast feedback from the user.
* Cons:
  * Easy to collect facts without a stable Trellis information architecture.
  * Rework risk is higher.

## Decision (ADR-lite)

**Context**: The repo now has enough Trellis content that navigation, overlap control, and gap-filling strategy matter. The user wants both doc synthesis and interview-driven expansion, and official Trellis guidance favors topic-focused, evolving specs over a monolithic handbook.

**Decision**: Default to Approach A unless the user explicitly prefers a different path.

**Consequences**:

* We should first classify and summarize current Trellis docs by role.
* We should design an interview workflow that fills gaps into the correct target docs.
* We should avoid turning the result into one giant “master Trellis doc”.

### Progress update

* User selected the mixed-mode path with priority on **Trellis doc map first**.
* User selected the Trellis doc map audience as **both maintainers and AI agents**.
* User selected the doc-map carrier as **a standalone Trellis guide**.
* User selected the initial doc-map scope as **current mainline high-value Trellis docs only**.

## Final Confirmation Draft

Goal:

* Create a standalone Trellis doc map guide for the current `coding-deepgent` mainline, then use it as the foundation for later interview-driven Trellis spec expansion.

Requirements:

* Use official Trellis spec-writing guidance:
  * index as entrypoint
  * topic-focused docs
  * actual-code/actual-convention extraction
  * continuous evolution
* Use Linux Do feedback as supporting context:
  * Trellis adoption benefits from structured explanation
  * empty specs need follow-up filling
  * avoid over-heavy process and token waste
* Create a standalone guide under `.trellis/spec/guides/`.
* Serve both maintainers and AI agents:
  * maintainers need role boundaries and maintenance rules
  * agents need reading order and update target rules
* Scope the first version to high-value mainline docs:
  * `.trellis/workflow.md`
  * `.trellis/project-handoff.md`
  * `.trellis/plans/index.md`
  * `.trellis/plans/*.md` high-level categories
  * `.trellis/spec/backend/index.md`
  * `.trellis/spec/backend/*.md` high-level categories
  * `.trellis/spec/guides/index.md`
  * `.trellis/spec/guides/*.md` high-level categories
  * `.trellis/workspace/index.md`
* Do not cover every `.trellis/scripts/*`, config, or internal task file in the first version.

Acceptance Criteria:

* [x] A new standalone guide explains current high-value Trellis doc roles.
* [x] The guide includes reading order for maintainers and AI agents.
* [x] The guide includes “where to write new knowledge” rules.
* [x] The guide states how it supports later interview-driven expansion.
* [x] `.trellis/spec/guides/index.md` links to the new guide.

Technical Approach:

* Add `.trellis/spec/guides/trellis-doc-map-guide.md`.
* Update `.trellis/spec/guides/index.md`.
* Keep the guide as a map, not a duplicate source-of-truth for every rule.

Implementation Plan:

* PR1 / Slice 1: Add the doc-map guide and index link. Completed.
* PR2 / Slice 2: Add interview-driven spec expansion guide after the map is accepted. Completed.

## Checkpoint: Trellis Doc Map Guide

State:

* checkpoint

Verdict:

* APPROVE

Implemented:

* Added `.trellis/spec/guides/trellis-doc-map-guide.md`.
* Added guide index entry and trigger in `.trellis/spec/guides/index.md`.
* The guide covers:
  * high-value document layers
  * maintainer reading order
  * AI agent reading order
  * write-target rules for new knowledge
  * summary vs atomic spec boundary
  * interview-driven expansion routing

Verification:

* Checked the new file exists.
* Checked `.trellis/spec/guides/index.md` links to `trellis-doc-map-guide.md`.

Decision:

* continue to PR2 / Slice 2 when user wants to design the interview-driven expansion guide.

## Checkpoint: Interview-Driven Spec Expansion Guide

State:

* checkpoint

Verdict:

* APPROVE

Implemented:

* Added `.trellis/spec/guides/interview-driven-spec-expansion-guide.md`.
* Added guide index entry and trigger in `.trellis/spec/guides/index.md`.
* The guide covers:
  * when to interview
  * when not to interview
  * target-doc selection
  * one-question interview rule
  * immediate write-back into owning Trellis doc
  * PRD interview trail format
  * MVP interview loop and stop conditions

Verification:

* Checked the new file exists.
* Checked `.trellis/spec/guides/index.md` links to `interview-driven-spec-expansion-guide.md`.

Decision:

* terminal for the initial brainstorm implementation slice.

## Interview Note: Frontend Spec Activation Strategy

Question:

* For deferred `frontend/*` specs, choose long-term deferred, reference-only simple note, or future-activatable template.

Answer:

* Future-activatable template.

Target docs:

* `.trellis/spec/frontend/index.md`
* `.trellis/spec/frontend/directory-structure.md`
* `.trellis/spec/frontend/component-guidelines.md`
* `.trellis/spec/frontend/hook-guidelines.md`
* `.trellis/spec/frontend/state-management.md`
* `.trellis/spec/frontend/type-safety.md`
* `.trellis/spec/frontend/quality-guidelines.md`

Change made:

* Marked frontend specs as deferred because `coding-deepgent/` is current mainline.
* Added activation requirements so future frontend/web product work can reactivate these specs without treating current reference UI as mainline.

## Checkpoint: Fast Trellis Gap Fill

State:

* checkpoint

Verdict:

* APPROVE

Implemented:

* Filled `backend/database-guidelines.md` with current no-SQL/store/session persistence guidance.
* Filled `backend/error-handling.md` with current error-boundary conventions.
* Filled `backend/logging-guidelines.md` with current `structlog` and evidence-vs-log guidance.
* Marked frontend specs as future-activatable deferred specs.

Verification:

* Derived backend guidance from current `coding-deepgent/src` and tests.
* Recorded the frontend activation decision from user interview.

Decision:

* continue when the next gap-fill batch is requested.

## Interview Note: Error Handling Strictness

Question:

* Should error handling prefer fail-fast, user-experience-first errors, or a mixed but strict boundary posture?

Answer:

* Mixed but strict.

Target doc:

* `.trellis/spec/backend/error-handling.md`

Change made:

* Added default posture and boundary decision matrix:
  * schema/domain/service fail fast
  * model-visible tools return bounded `"Error: ..."` when appropriate
  * CLI converts expected failures to `ClickException` / `typer.Exit`
  * recoverable middleware fails open only when a contract explicitly allows it

## Interview Note: Evidence Vs Logs Boundary

Question:

* Should session evidence record only high-value recoverable facts, record more runtime events, or stay extremely minimal?

Answer:

* Evidence should record only high-value recoverable facts.

Target doc:

* `.trellis/spec/backend/logging-guidelines.md`

Change made:

* Added default evidence posture.
* Documented current whitelisted runtime evidence kinds:
  * `hook_blocked`
  * `permission_denied`
  * `microcompact`
  * `auto_compact`
  * `reactive_compact`
* Clarified that successful ordinary tool calls, hook start/complete events, config/startup diagnostics, and non-contractual debug details should stay as logs.

## Interview Note: Project Handoff Update Policy

Question:

* Should `.trellis/project-handoff.md` update on milestones, every session, or only release/PR boundaries?

Answer:

* Milestone updates.

Target docs:

* `.trellis/project-handoff.md`
* `.trellis/spec/guides/trellis-doc-map-guide.md`

Change made:

* Added handoff update policy:
  * update when mainline stage family, canonical roadmap/dashboard, latest verified state, next recommended task, canonical cross-session requirement, or minimal resume reading order changes
  * do not update for ordinary daily progress or minor session summaries
  * use workspace journals via `record-session` for ordinary session records
* Updated Trellis doc map write-target rules to distinguish mainline handoff updates from ordinary completed-session records.

## Checkpoint: Interview Workflow In Main Workflow

State:

* checkpoint

Verdict:

* APPROVE

Implemented:

* Added interview-driven spec expansion references to `.trellis/workflow.md`.
* Added a workflow section requiring:
  * derive first
  * choose owning Trellis doc before asking
  * ask one targeted question
  * write answer immediately
  * record interview note in active PRD

Verification:

* Manual read of the updated workflow section.

Decision:

* continue with next interview topic.

## Interview Note: Plans Vs Specs Boundary

Question:

* Should future agents treat plans as direction and specs as executable constraints, minimize plans, or make plans the source of all design before deriving specs?

Answer:

* Plans write direction; specs write executable constraints.

Target docs:

* `.trellis/spec/guides/trellis-doc-map-guide.md`
* `.trellis/spec/guides/interview-driven-spec-expansion-guide.md`

Change made:

* Added plans-vs-specs boundary:
  * `plans/` own product goals, roadmap rows, stage sequencing, strategic tradeoffs, deferred/do-not-copy decisions, milestone boundaries
  * `spec/` owns implementation contracts, schemas/signatures, module boundaries, validation/error matrices, testing requirements, concrete do/don't rules
  * plan decisions that become mandatory for implementation should be extracted into the owning spec

## Interview Note: Task PRD Vs Workspace Journal Boundary

Question:

* Should task PRDs record task-internal decisions while journals record completed sessions, or should more process move into journals?

Answer:

* PRD records task-internal decisions; journal records completed sessions.

Target docs:

* `.trellis/spec/guides/trellis-doc-map-guide.md`
* `.trellis/spec/guides/interview-driven-spec-expansion-guide.md`
* `.trellis/workflow.md`

Change made:

* Added PRD-vs-journal boundary:
  * active task PRD owns requirements, interview notes, scope decisions, checkpoints, verification evidence, unresolved questions
  * workspace journal owns completed session summaries, commits, final testing notes, next-step handoff after completed session
  * active interview decisions should not live only in journals

## Interview Note: Spec Update Trigger

Question:

* Should specs update only when contracts/boundaries change, after every feature, or only after bugs?

Answer:

* Update specs when contracts or boundaries change.

Target docs:

* `.trellis/spec/guides/trellis-doc-map-guide.md`
* `.trellis/workflow.md`

Change made:

* Added spec-update triggers:
  * tool schema / command / API shape
  * runtime state fields or payload formats
  * module ownership or boundary
  * validation / error behavior
  * test requirements or verification matrix
  * cross-layer transformation
  * repeated mistake that should become a rule
* Clarified that ordinary implementation detail should not create spec noise.

## Interview Note: CC Alignment Record Placement

Question:

* Should cc-haha alignment results first live in active PRDs and then be promoted, or should all alignment go directly into plans or specs?

Answer:

* First write to active PRD, then promote stable roadmap outcomes to plans and executable constraints to specs.

Target docs:

* `.trellis/spec/guides/cc-alignment-guide.md`
* `.trellis/spec/guides/trellis-doc-map-guide.md`

Change made:

* Clarified cc alignment record placement:
  * active task PRD owns expected effect, source evidence, matrix, exploratory decisions
  * `plans/` owns stable roadmap/product-direction outcomes
  * `spec/` owns executable implementation constraints
  * exploratory source notes should not become canonical specs by default

## Interview Note: Validation Scope Policy

Question:

* Should validation default to focused first with broader escalation, full validation every time, or minimum checks only?

Answer:

* Focused first; broader validation only when risk triggers it.

Target docs:

* `.trellis/spec/backend/quality-guidelines.md`
* `.trellis/spec/guides/staged-execution-guide.md`

Change made:

* Added validation scope policy:
  * focused tests and touched-file lint/typecheck by default
  * broader validation for cross-layer contracts, runtime/session/compact/task changes, middleware ordering changes, ambiguous focused failures, or explicit user request
  * no full-suite default for every small change

## Interview Note: Delegated Recommended Defaults

Question:

* Should future low-risk process choices continue to require explicit user selection?

Answer:

* No. User delegated future low-risk process choices to the recommended option.

Target docs:

* `.trellis/workflow.md`

Change made:

* Added workflow rule:
  * proceed with recommended/default option for low-risk process choices
  * still stop for irreversible deletion, major product direction changes, or unclear ownership

## Interview Note: Task Archive Policy

Question:

* Should completed Trellis tasks be archived after commit/acceptance, after PR merge, or manually without default?

Answer:

* Use recommended default: archive after the work is actually complete and committed, or docs/planning-only complete.

Target docs:

* `.trellis/workflow.md`
* `.trellis/spec/guides/trellis-doc-map-guide.md`

Change made:

* Added task archive policy:
  * archive when acceptance criteria are met and appropriate verification is complete
  * archive after human commit, or when docs/planning-only work is explicitly complete
  * do not keep tasks open only because stale task metadata says `planning` or `in_progress`

## Checkpoint: Trellis Docs Synthesis And Interview Expansion

State:

* terminal

Verdict:

* APPROVE

Implemented:

* Added Trellis doc map guide.
* Added interview-driven spec expansion guide.
* Filled backend persistence, error handling, and logging guidance.
* Marked frontend specs as deferred but future-activatable.
* Added handoff update policy.
* Added plans-vs-specs boundary.
* Added task PRD vs workspace journal boundary.
* Added spec update trigger rule.
* Added cc alignment record placement rule.
* Added validation scope policy.
* Added delegated recommended-default behavior for low-risk process choices.
* Added task archive policy.

Verification:

* Lightweight file/link checks were run for the two new guides.
* Subsequent edits are documentation-only and follow the established Trellis doc-map routing.

Decision:

* terminal for this Trellis docs synthesis/interview foundation pass.

## Checkpoint: Trellis Optimization Batch

State:

* terminal

Verdict:

* APPROVE

Implemented:

* Updated `.trellis/spec/backend/index.md` statuses for database, error handling, and logging from placeholder to active.
* Split the oversized runtime context/compaction contract into:
  * `.trellis/spec/backend/tool-result-storage-contracts.md`
  * `.trellis/spec/backend/session-compact-contracts.md`
  * `.trellis/spec/backend/runtime-pressure-contracts.md`
  * kept `.trellis/spec/backend/runtime-context-compaction-contracts.md` as an overview index.
* Normalized current backend spec paths to `coding-deepgent/tests/...` and `coding-deepgent/src/...`.
* Replaced migrated `.omx/...` current references with `.trellis/...` paths in Trellis planning docs where appropriate.
* Expanded `.trellis/plans/index.md` with plan roles, read timing, and maintenance rules.
* Updated `.trellis/spec/guides/trellis-doc-map-guide.md` to mark frontend specs as deferred/future-activatable.
* Added review output format requirements to `.trellis/spec/backend/quality-guidelines.md`.
* Added `.trellis/scripts/check_trellis_links.py` for lightweight local Markdown link checks.

Verification:

* `python3 ./.trellis/scripts/check_trellis_links.py` -> passed.
* Scanned current Trellis specs/plans/workflow/handoff for stale `tests/test_*`, `src/coding_deepgent`, `.omx/`, deleted `coding-deepgent/docs`, and removed skill references.
* Confirmed backend specs no longer contain old relative `tests/test_*` or `src/coding_deepgent` paths.

Residual notes:

* `.trellis/plans/index.md` intentionally mentions the removed `.omx` tree as migration context.
* `.trellis/spec/backend/index.md` intentionally mentions `coding-deepgent/docs/` only to say not to revive parallel docs there.

Decision:

* terminal for the requested 8-item Trellis optimization batch.
