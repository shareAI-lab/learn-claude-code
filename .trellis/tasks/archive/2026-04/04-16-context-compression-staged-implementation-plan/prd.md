# context compression staged implementation plan

## Goal

作为 4 个上下文压缩后续计划的父任务，统一拆解、排序、并发策略和交付边界。该父任务不直接实现代码；它负责协调子任务，避免 MicroCompact / Collapse / AutoCompact / tool-output pruning 之间的重复、冲突和顺序错误。

## Child Tasks

* `04-15-opencode-style-auto-tool-output-prune`
* `04-16-cc-style-time-based-local-microcompact`
* `04-16-cc-style-collapse-store-pressure-guard`
* `04-16-cc-style-autocompact-hardening`

Frontend/visualization planning remains separate:

* `04-16-context-compression-visualization-readiness`

## Why A Parent Plan Is Needed

这 4 个计划共享同一套 runtime pressure/session context surfaces：

* `compact.runtime_pressure`
* `sessions` evidence / records
* settings / container wiring
* runtime pressure contracts
* future model-facing projection metadata

如果不排序，容易出现：

* MicroCompact 和 opencode-style prune 重复清同一批 tool result。
* Collapse 和 AutoCompact 都抢着摘要同一段历史。
* AutoCompact restoration 依赖的 structured result 还没建立。
* Spawn guard 依赖 pressure ratio，但 pressure estimation 还没统一。

## Decomposition Principles

* Keep implementation tasks small enough to complete with focused tests.
* Prefer one reusable contract per child implementation task.
* If a task touches session record schema, runtime pressure ordering, and subagent behavior at once, split it.
* Treat source-backed research PRDs as reference, not implementation tasks.
* Keep provider-specific cache editing out of this parent plan.

## Proposed Execution Order

### Stage 1: Tool Output Pruning Foundation

Source tasks:

* `04-15-opencode-style-auto-tool-output-prune`
* `04-16-cc-style-time-based-local-microcompact`

Recommended small tasks:

1. `runtime-pressure-token-saved-evidence`
   * Add bounded `tokens_saved_estimate`, `tools_cleared`, `tools_kept` fields to runtime pressure event/evidence.
   * Reason: both opencode-style prune and time-based MicroCompact need this observability.

2. `time-based-local-microcompact`
   * Add idle-gap trigger, main-agent gating, keepRecent floor, min savings threshold.
   * Reason: cc Level 2 non-API value, independent from Collapse/AutoCompact.

3. `token-budget-tool-output-prune`
   * Upgrade count-based keep policy to token-budget protected recent tool outputs if still needed after Stage 1.2.
   * Reason: opencode-style enhancement may overlap with time-based mode; implement only if the simpler mode is insufficient.

Parallelism:

* `runtime-pressure-token-saved-evidence` can be done first and unblocks both.
* `time-based-local-microcompact` and `token-budget-tool-output-prune` should not be implemented in parallel unless their write sets are separated, because both touch `microcompact_messages` semantics.

### Stage 2: AutoCompact Reliability Backbone

Source task:

* `04-16-cc-style-autocompact-hardening`

Recommended small tasks:

1. `autocompact-failure-circuit-breaker`
   * Stop repeated doomed proactive AutoCompact attempts after bounded failures.
   * Low coupling and useful immediately.

2. `compact-request-ptl-retry`
   * If summarizer prompt is too long, drop oldest groups and retry.
   * Depends on clear grouping/tail-pair invariants.

3. `structured-compaction-result`
   * Introduce local structured result and stable render order.
   * Should happen before restoration/hooks.

4. `post-compact-restoration-contributions`
   * Restore active todos, plan/verifier evidence, skill/file refs, bounded paths.
   * Depends on structured result.

5. `pre-post-compact-hooks`
   * Add PreCompact/PostCompact contribution seams.
   * Depends on structured result and restoration boundaries.

Parallelism:

* `autocompact-failure-circuit-breaker` can run in parallel with Stage 1 after current branch is clean.
* `structured-compaction-result` must precede restoration/hooks.
* `compact-request-ptl-retry` can run before or after structured result if kept local, but should not overlap with AutoCompact render-order changes.

### Stage 3: Collapse Store And Projection

Source task:

* `04-16-cc-style-collapse-store-pressure-guard`

Recommended small tasks:

1. `collapse-records`
   * Add durable collapse records without applying replay yet.

2. `collapse-projection-replay`
   * Derive model-facing collapsed view from raw history + collapse records.
   * Depends on stable message IDs or at least stable message indexes.

3. `pressure-ratio-trigger`
   * Use estimated tokens / model context window when available.
   * Can be shared with spawn guard.

4. `collapse-overflow-drain`
   * On prompt-too-long, drain collapse summaries before reactive compact.
   * Depends on records + replay.

5. `spawn-pressure-guard`
   * Warn/block subagent spawn at high pressure.
   * Depends on pressure ratio and subagent context boundaries.

Parallelism:

* `pressure-ratio-trigger` can be developed in parallel with `collapse-records` if write sets are separated.
* `collapse-projection-replay` must wait for collapse records.
* `collapse-overflow-drain` must wait for projection replay.
* `spawn-pressure-guard` can wait until pressure ratio exists and should be isolated in `subagents`.

## Cross-Stage Dependencies

* `structured-compaction-result` helps AutoCompact restoration and future UI.
* `pressure-ratio-trigger` helps Collapse and spawn guard.
* `runtime-pressure-token-saved-evidence` helps future visualization.
* Stable message IDs are likely required before full `collapse-projection-replay` and cc-style Snip; if missing, create a separate foundational task before Stage 3.2.

## Parallel Work Plan

Safe parallel groups if using separate worktrees/agents:

* Group A: `runtime-pressure-token-saved-evidence`
* Group B: `autocompact-failure-circuit-breaker`
* Group C: `pressure-ratio-trigger`

Do not run in parallel initially:

* `time-based-local-microcompact` and `token-budget-tool-output-prune` because both change tool-output clearing semantics.
* `structured-compaction-result` and `post-compact-restoration-contributions` because restoration depends on result shape.
* `collapse-records` and `collapse-projection-replay` unless record schema is frozen first.

## Recommended Immediate Next Task

Start with:

```text
runtime-pressure-token-saved-evidence
```

Why:

* Small and low-risk.
* Improves current MicroCompact observability.
* Unblocks time-based MicroCompact and frontend compression timeline.
* Does not require session schema changes.

## Out of Scope

* No implementation in this parent task.
* No provider-specific cached microcompact API.
* No frontend UI implementation.
* No cc-style semantic SnipTool in this parent plan.

## Acceptance Criteria

* [x] Parent task exists.
* [x] 4 compression child tasks are linked.
* [x] Dependencies are documented.
* [x] Safe parallel groups are documented.
* [x] Recommended immediate next task is identified.

## Status

Planning-only parent task.

## Checkpoint: Stage 1 Tool Output Pruning Foundation

State: checkpoint

Verdict: APPROVE

Implemented:

* `runtime-pressure-token-saved-evidence`
* `time-based-local-microcompact`
* `token-budget-tool-output-prune`

Verification:

* Focused runtime pressure/app/static checks passed at each sub-stage.
* Final full `coding-deepgent` suite after Stage 2: `pytest -q` -> 281 passed.

Decision: continue

Reason:

* Stage 1 completed without changing raw transcript persistence.

## Checkpoint: Stage 2 AutoCompact Reliability Backbone

State: checkpoint

Verdict: APPROVE

Implemented:

* `autocompact-failure-circuit-breaker`
* `compact-request-ptl-retry`
* `structured-compaction-result`
* `post-compact-restoration-contributions` active-todo slice
* `pre-post-compact-hooks`

Verification:

* `pytest -q tests/test_runtime_pressure.py tests/test_hooks.py` -> 46 passed.
* `pytest -q tests/test_app.py` -> 9 passed.
* `pytest -q` -> 281 passed.
* Targeted `ruff check` and `mypy` passed.

Decision: continue

Reason:

* Stage 2 completed through the planned hook seam.

## Checkpoint: Stage 3 Collapse Store And Projection

State: checkpoint

Verdict: ITERATE

Boundary findings:

* `collapse-records` and `collapse-projection-replay` need deterministic references
  from collapse records back to raw transcript messages.
* Current persisted session messages have `message_index` but no stable
  `message_id`.
* Parent plan already identified stable message IDs as a likely prerequisite
  before full `collapse-projection-replay`.

Decision: split

Reason:

* Created prerequisite task `04-16-stable-message-ids-compression-projection`.
* Continuing directly into durable collapse replay would lock future
  compression timeline/projection work onto unstable implicit indexes.

## Checkpoint: Stage 3 Collapse Store And Projection Closeout

State: verifying

Verdict: APPROVE

Implemented:

* `stable-message-ids-compression-projection`
* `collapse-records`
* `collapse-projection-replay`
* `pressure-ratio-trigger`
* `collapse-overflow-drain`
* `spawn-pressure-guard`

Verification:

* Focused collapse/session/runtime/subagent/app tests passed:
  `pytest -q coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_runtime_pressure.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_subagents.py coding-deepgent/tests/test_app.py`
* Final full-suite verification is required before commit:
  `pytest -q coding-deepgent/tests`
* Targeted `ruff check` and `mypy` are required before commit.

Architecture:

* Raw transcript remains the source of truth as `LoadedSession.history`.
* Compact and collapse are append-only `transcript_event` projections over raw
  messages.
* Collapse replay uses stable `message_id` references only.
* Runtime live collapse persistence uses a non-model-visible transcript
  projection sidecar rather than leaking storage IDs into prompt messages.

Decision: continue

Reason:

* Backend collapse foundation is now coherent enough for final validation and
  scoped commit. Frontend/timeline remains in the separate visualization task.
