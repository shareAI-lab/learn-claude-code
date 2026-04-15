# brainstorm: reconcile stage PRD status

## Goal

使用 Trellis workflow 处理当前遗留的 `stage-*` PRD：基于 canonical handoff、roadmap、contracts、task metadata、代码与测试证据，逐条判定这些 stage PRD 在当前主线中的真实状态，并执行相应的整理动作，使 `.trellis/tasks/` 中的 stage 任务状态与 `coding-deepgent` 的实际主线状态重新一致。

## What I already know

* 当前产品主线是 `coding-deepgent/`，canonical coordination layer 是 `.trellis/`。
* `project-handoff.md` 明确写明当前主线已完成的 stage family 包括 `Stage 12` 到 `Stage 29`。
* `project-handoff.md` 的当前推荐方向不是继续做这些历史 stage，而是 `release validation / PR cleanup for Approach A MVP`。
* `.trellis/tasks/` 中当前仍有多个 `Stage 12A-17D` 任务处于未归档状态，其中大量 `task.py list` 状态仍显示为 `planning`。
* `Stage 18A-19, 21-29, 30A-30B` 的 PRD 已经位于 `.trellis/tasks/archive/2026-04/` 下。
* `Stage 20` 没有搜到独立的 `stage-20-*/prd.md` 文件。
* handoff 的恢复策略建议优先阅读：
  - `04-15-stage-17c-explicit-plan-artifact-boundary/prd.md`
  - `04-15-stage-17d-verifier-subagent-execution-boundary/prd.md`
  - archived `18A/18B/19`
  - `04-15-coding-deepgent-highlight-completion-map/prd.md`
  - archived `29`
* 当前工作区干净，当前没有激活中的 task。
* `mainline-scope-guide.md` 明确要求当前工作默认服务于 `coding-deepgent/` 与 `.trellis/`，不追 tutorial/reference parity。
* `staged-execution-guide.md` 要求默认使用 `lean` 模式，只在需要时扩大验证范围。
* `trellis-doc-map-guide.md` 明确 task PRD 负责在任务进行中记录 requirements、decision、checkpoint、verification evidence；仅当任务完成后才归档。
* 当前未归档的 `Stage 12A-17D` 中，绝大多数 `task.json` 状态仍是 `planning`；`16B latest-valid-compact-view-selection` 已在 active tasks 中标记为 `completed` 但尚未归档。
* archived `18A-19, 21-29` 的 `task.json` 状态是 `completed`，与归档位置一致。
* archived `30A/30B` 的 `task.json` 状态目前也是 `completed`，但这与 roadmap/handoff 中“`Stage 30-36` reserve only / not currently required”存在潜在口径冲突，需要审计。

## Assumptions (temporary)

* 这次任务的目标不是重做 `Stage 12-29` 的实现，而是对 Trellis 任务层做状态校准与归档清理。
* 如果某个 stage 的目标已经被后续 stage、canonical roadmap、handoff、contracts 与代码测试共同吸收，则应判为 `completed` 或 `superseded`，而不是继续保留为 active `planning`。
* 如果某个 stage 明确属于 next-cycle / reserve / deferred scope，则应保留为 `deferred`，而不是归档为 `completed`。
* “处理 PRD” 可能包括：
  - 更新 task metadata / status
  - 归档 active task
  - 补充 PRD 中的结论说明
  - 必要时更新 handoff / roadmap / Trellis notes

## Open Questions

* None after scope confirmation:
  - reconcile active `12A-17D`
  - review only archived `30A/30B` for reserve-policy conflict

## Requirements (evolving)

* 建立一个 stage PRD 审核清单，覆盖当前未归档与已归档的 `stage-*` PRD。
* 为每个相关 stage PRD 给出一个明确状态结论：
  - `completed`
  - `superseded`
  - `deferred`
  - `needs_followup`（仅当现有证据不足）
* 每个结论都必须绑定具体依据，至少来自以下来源中的两类：
  - `project-handoff.md`
  - canonical roadmap / completion map
  - PRD 自身的 implementation / verification notes
  - current code / tests / contracts
  - task metadata / archive location
* 对当前 active 但已完成或已被覆盖的 stage PRD，执行 Trellis 侧整理动作。
* 对应归档/保留动作必须最小化且可解释，避免无依据地删除历史记录。
* 若发现 handoff / roadmap / task state 三者冲突，需要记录冲突并决定 canonical source。

## Code-Spec Depth Check

* This task does not introduce a new product API, schema, or runtime contract in `coding-deepgent`.
* The main executable boundary is Trellis task/archive semantics:
  - how stage task state is classified
  - when an active stage task should be archived
  - which document is canonical when task metadata conflicts with handoff/roadmap
* Concrete contract for this task:
  - `project-handoff.md` and the canonical roadmap own current mainline stage status
  - active task metadata must not contradict canonical completed stage families
  - archived reserve tasks must not be mistaken for MVP-required completed stages
* Validation/error matrix:
  - Good: active historical stage has checkpoint evidence + canonical doc says family completed -> classify completed and archive
  - Base: archived reserve stage exists with implemented notes but canonical doc says reserve/not required -> record as deferred/superseded conflict, do not reopen active work
  - Bad: task metadata alone says `planning`/`completed` but canonical docs or PRD evidence disagree -> do not trust metadata alone

## Research Notes

### Relevant Specs

* `.trellis/spec/guides/mainline-scope-guide.md`: keeps the task focused on `coding-deepgent` and `.trellis/`, not tutorial/reference cleanup.
* `.trellis/spec/guides/staged-execution-guide.md`: establishes `lean` staged execution and checkpoint-driven progression for this audit/cleanup task.
* `.trellis/spec/guides/trellis-doc-map-guide.md`: defines ownership between active task PRDs, canonical docs, and archive behavior.
* `.trellis/spec/backend/runtime-context-compaction-contracts.md`: relevant when confirming Stage 12-16 status claims against current canonical compact/session contract coverage.
* `.trellis/spec/backend/task-workflow-contracts.md`: relevant when confirming Stage 17C/17D status claims and verifier/task workflow boundaries.

### Code Patterns Found

* Stage PRDs record terminal evidence in `## Checkpoint` sections with `Implemented` and `Verification` blocks.
  - Examples:
    - `.trellis/tasks/04-14-stage-12a-context-payload-foundation/prd.md`
    - `.trellis/tasks/04-14-stage-13a-manual-compact-boundary-and-summary-artifact/prd.md`
    - `.trellis/tasks/04-15-stage-17c-explicit-plan-artifact-boundary/prd.md`
* Archived completed stage tasks keep `task.json.status = "completed"` and live under `.trellis/tasks/archive/<year-month>/...`.
  - Examples:
    - `.trellis/tasks/archive/2026-04/04-15-stage-18a-verifier-execution-integration/task.json`
    - `.trellis/tasks/archive/2026-04/04-15-stage-29-deferred-boundary-adr-mvp-release-checklist/task.json`
* `task.py archive` updates parent/child links and then moves the task directory; it does not infer or rewrite task conclusions on its own.
  - Source:
    - `.trellis/scripts/task.py`
    - `.trellis/scripts/common/task_utils.py`

### Files To Modify

* `.trellis/tasks/04-15-stage-prd-status-reconciliation/prd.md`: record decisions, evidence table, and checkpoint.
* Active stage task dirs under `.trellis/tasks/04-14-stage-*` and `.trellis/tasks/04-15-stage-17*`: update task metadata and/or archive them when classified as completed/superseded.
* `.trellis/tasks/archive/2026-04/04-15-stage-30a-module-upgrade-contribution-seams/`
* `.trellis/tasks/archive/2026-04/04-15-stage-30b-session-memory-threshold-local-updates/`
  - record or normalize their deferred/reserve conflict if needed.

### Initial Findings

* All in-scope active stage PRDs from `12A` through `17D` contain completion-style checkpoint evidence, including implemented behavior and verification commands.
* `Stage 16B latest-valid-compact-view-selection` is already marked `completed` in active tasks but still unarchived, which confirms task-state drift exists.
* `project-handoff.md` and the archived completion map both state that Stage 12-19 stage families were completed as part of the current mainline.
* `project-handoff.md` and the canonical roadmap explicitly state `Stage 30-36` are reserve-only and not currently required, which conflicts with archived `30A/30B` being labeled `completed`.

## Technical Approach

* Treat `project-handoff.md` plus the canonical roadmap/completion-map docs as the source of truth for current mainline stage-family status.
* Use each stage PRD checkpoint as the task-level implementation/verification evidence.
* Normalize stale active `task.json` metadata before archiving so archive state reflects the documented completion decision.
* Archive historical active stage tasks with `task.py archive --no-commit` so Trellis link cleanup runs without violating the no-auto-commit rule for AI work.
* For archived `30A/30B`, keep the task archived but add explicit notes that current canonical planning still treats Stage 30-36 as reserve-only.

## Decision (ADR-lite)

**Context**: Active stage tasks from `12A-17D` were still visible as `planning` or otherwise unarchived even though their PRDs contained terminal checkpoints and canonical docs treated those stage families as already complete. Archived `30A/30B` also carried `completed` metadata despite current canonical docs still describing Stage 30-36 as reserve-only.

**Decision**:

* Canonical current-state authority is `project-handoff.md` plus the canonical roadmap/completion-map docs, not stale task metadata.
* Active `12A-17D` tasks with checkpoint evidence are historical completed work and should be archived.
* `04-14-stage-16-compact-transcript-pruning-semantics` is a planning/scope PRD superseded by implemented `16A/16B/16C` follow-on stages and should be archived as historical planning work.
* `04-14-stage-16b-virtual-pruning-compact-selection-hardening` is an orphan active task with no PRD and is superseded by the implemented `16B latest-valid-compact-view-selection` task.
* Archived `30A/30B` remain archived historical work, but for current planning they should be treated as reserve/non-priority work until canonical docs are intentionally reopened.

**Consequences**:

* Active task lists now reflect the actual current mainline instead of historical stage residue.
* Canonical resume docs remain unchanged and still govern the next recommended work.
* Stage 30 reserve ambiguity is documented but does not reopen new implementation work during this cleanup pass.

## Status Audit

* `04-14-stage-12a-context-payload-foundation`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff and completion-map mark Stage 12 complete. Action: normalized metadata and archived.
* `04-14-stage-12b-message-projection-and-tool-result-invariants`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff and completion-map mark Stage 12 complete. Action: normalized metadata and archived.
* `04-14-stage-12c-recovery-brief-and-session-resume-audit`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff and completion-map mark Stage 12 complete. Action: normalized metadata and archived.
* `04-14-stage-12d-memory-quality-policy`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff and completion-map mark Stage 12 complete. Action: normalized metadata and archived.
* `04-14-stage-13a-manual-compact-boundary-and-summary-artifact`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks Stage 13 complete. Action: normalized metadata and archived.
* `04-14-stage-13b-manual-compact-entry-point`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks Stage 13 complete. Action: normalized metadata and archived.
* `04-14-stage-13c-compact-summary-generation-seam`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks Stage 13 complete. Action: normalized metadata and archived.
* `04-14-stage-14a-explicit-generated-summary-cli-wiring`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks Stage 14A complete. Action: normalized metadata and archived.
* `04-14-stage-15a-non-destructive-compact-transcript-records`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks Stage 15 complete. Action: normalized metadata and archived.
* `04-14-stage-15b-compact-record-recovery-display`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks Stage 15 complete. Action: normalized metadata and archived.
* `04-14-stage-15c-compacted-continuation-selection`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks Stage 15 complete. Action: normalized metadata and archived.
* `04-14-stage-16-compact-transcript-pruning-semantics`: `superseded`. Basis: this PRD is a planning/decision artifact with no terminal implementation checkpoint; implemented `16A/16B/16C` follow-on tasks plus handoff/completion-map cover the realized Stage 16 outcome. Action: marked completed for historical archive cleanup and archived with a supersession note.
* `04-14-stage-16a-load-time-compacted-history-view`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks Stage 16 complete. Action: normalized metadata and archived.
* `04-14-stage-16b-latest-valid-compact-view-selection`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks Stage 16 complete. Action: archived.
* `04-14-stage-16b-virtual-pruning-compact-selection-hardening`: `superseded`. Basis: active task had no PRD; the implemented `16B latest-valid-compact-view-selection` task exists and handoff treats Stage 16 as complete. Action: marked completed for historical archive cleanup and archived with an anomaly note.
* `04-14-stage-16c-virtual-pruning-view-metadata`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks Stage 16 complete. Action: normalized metadata and archived.
* `04-14-stage-17a-task-graph-readiness-and-transition-invariants`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks `17A` complete. Action: normalized metadata and archived.
* `04-14-stage-17b-plan-verify-workflow-boundary`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks `17B` complete. Action: normalized metadata and archived.
* `04-15-stage-17c-explicit-plan-artifact-boundary`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks `17C` complete. Action: normalized metadata and archived.
* `04-15-stage-17d-verifier-subagent-execution-boundary`: `completed`. Basis: PRD checkpoint documents implementation + verification; handoff marks `17D` complete. Action: normalized metadata and archived.
* `04-15-stage-30a-module-upgrade-contribution-seams`: `needs_followup`. Basis: archived PRD contains terminal checkpoints showing implementation, but handoff/roadmap still state Stage 30-36 are reserve-only and not currently required. Action: kept archived, added reserve-work note, do not reopen current mainline work from this cleanup task.
* `04-15-stage-30b-session-memory-threshold-local-updates`: `needs_followup`. Basis: archived PRD contains terminal checkpoints showing implementation, but handoff/roadmap still state Stage 30-36 are reserve-only and not currently required. Action: kept archived, added reserve-work note, do not reopen current mainline work from this cleanup task.

## Acceptance Criteria (evolving)

* [x] 已列出本次处理范围内的 stage PRD 清单。
* [x] 每个 stage PRD 都有状态结论和书面依据。
* [x] 当前 active 但实际上已完成/已被覆盖的 stage PRD 得到 Trellis 侧处理。
* [x] 明确保留 next-cycle / reserve PRD，不误归档为 completed。
* [x] 若存在状态冲突，已记录 canonical decision。
* [x] 所有相关 Trellis 变更经过一致性检查。

## Definition of Done (team quality bar)

* Tests added/updated where implementation behavior changes
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 重新实现 `Stage 12-29` 的产品代码
* 打开新的功能 stage，除非审计证明存在真实 MVP 缺口
* 无证据地删除历史 PRD 或重写历史结论
* 对 tutorial/reference layer 做无关整理

## Technical Notes

* New task: `.trellis/tasks/04-15-stage-prd-status-reconciliation`
* Canonical documents:
  - `.trellis/project-handoff.md`
  - `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
  - `.trellis/tasks/04-14-redefine-coding-deepgent-final-goal/prd.md`
  - `.trellis/spec/backend/runtime-context-compaction-contracts.md`
  - `.trellis/spec/backend/task-workflow-contracts.md`
* Candidate bridge docs:
  - `.trellis/tasks/archive/2026-04/04-15-coding-deepgent-highlight-completion-map/prd.md`
* Historical active stage PRDs processed in this task:
  - `12A-17D`
* Already archived stage PRDs:
  - `18A-19`
  - `21-29`
  - `30A-30B`
* Current Trellis guidance for this task:
  - use `.trellis/` as the canonical coordination layer
  - treat task PRDs as the in-progress decision ledger
  - prefer `lean` staged execution unless broader validation becomes necessary

## Checkpoint: Stage PRD Status Reconciliation

State:
- terminal

Verdict:
- APPROVE

Implemented:
- Created a dedicated Trellis task and PRD for stage-status reconciliation.
- Researched canonical authority across handoff, roadmap, completion-map, and task/archive ownership docs.
- Normalized active historical stage task metadata for `12A-17D`.
- Archived all previously active historical stage tasks under `.trellis/tasks/archive/2026-04/`.
- Added reserve-policy reconciliation notes to archived `30A/30B`.

Verification:
- `python3 ./.trellis/scripts/task.py list`
- Verified parent brainstorm tasks now have empty `children` arrays after archive cleanup.
- Parsed representative archived `task.json` files to confirm status/notes updates for:
  - `12A`
  - `16 planning`
  - `16B orphan`
  - `17D`
  - `30A`
  - `30B`

Alignment:
- source files inspected:
  - `.trellis/project-handoff.md`
  - `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
  - `.trellis/tasks/archive/2026-04/04-15-coding-deepgent-highlight-completion-map/prd.md`
  - `.trellis/spec/guides/trellis-doc-map-guide.md`
- aligned:
  - current mainline status comes from canonical Trellis handoff/roadmap docs, not stale task metadata
  - historical stage tasks should not remain active after the stage family is already canonicalized as complete
- deferred:
  - broader reconciliation of non-stage brainstorm/backlog tasks
  - canonical decision on whether `30A/30B` should later be absorbed into current handoff/roadmap
- do-not-copy:
  - no broad rewrite of historical PRDs
  - no reopening of reserve work as part of this cleanup pass

Architecture:
- primitive used:
  - Trellis task PRD as the active decision ledger
  - `task.py archive --no-commit` for safe archive moves and parent/child cleanup
- why no heavier abstraction:
  - this was a task-ledger reconciliation problem, not a product-runtime change

Boundary findings:
- `Stage 16` had both a planning PRD and a later implemented `16A/16B/16C` family; the planning doc should be treated as superseded planning, not pending implementation.
- `04-14-stage-16b-virtual-pruning-compact-selection-hardening` was an orphan task with no PRD and required anomaly handling.
- `30A/30B` are implemented historical work but still non-canonical for the current MVP closeout path.

Decision:
- stop

Reason:
- The approved scope is complete: active `12A-17D` tasks were reconciled and archived, and `30A/30B` conflict notes were recorded without reopening reserve work.
