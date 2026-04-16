# brainstorm: cc level 3 collapse alignment

## Goal

评估用户提供的 `Level 3: Collapse` 描述是否符合 cc-haha 可见源码，并判断当前 `coding-deepgent` 的 Collapse 是否对齐，以及后续还有哪些 cc 亮点值得规划。

## Communication Requirement

When explaining context compression mechanisms, use concrete scenarios before
terms. The user explicitly prefers examples such as "long coding session,
testing logs, file reads, subagent spawn" over mechanism-only lists.

## What I already know

* 当前 `coding-deepgent` 已实现 summarizer-based live `Collapse`：
  * `maybe_collapse_messages(...)`
  * `collapse_live_messages_with_summary(...)`
  * 在 `RuntimePressureMiddleware.wrap_model_call()` 中运行于 `MicroCompact` 之后、`AutoCompact` 之前。
* 当前实现是 live model-call rewrite，失败时 fail-open，不持久化 collapse store，不记录 staged collapse drain state。
* 用户提供的描述强调 90% commit、95% spawn block、主动重构、抑制 AutoCompact、选择性消息组重构、与 fork/spawn 交互。

## Source Notes

cc-haha source reviewed:

* `/root/claude-code-haha/src/query.ts`
* `rg CONTEXT_COLLAPSE/contextCollapse` in `/root/claude-code-haha/src`

Key source-backed facts:

* `query.ts` feature-gates `contextCollapse` via `feature('CONTEXT_COLLAPSE')`.
* `contextCollapse.applyCollapsesIfNeeded(...)` runs after `microcompact` and before `autocompact`.
* Source comments state collapse runs before autocompact so if collapse gets the input under autocompact threshold, autocompact is a no-op and granular context is preserved.
* Source comments state collapse is a read-time projection over full REPL history.
* Summary messages live in a collapse store, not in the REPL array.
* Collapse persists across turns because `projectView()` replays the commit log on every entry.
* Prompt-too-long recovery first attempts `contextCollapse.recoverFromOverflow(...)` to drain staged collapses before reactive compact.
* Query logic has `collapseOwnsIt` and withheld error handling so context-collapse recovery can own certain prompt-too-long conditions before autocompact/reactive compact surfaces them.
* The actual `services/contextCollapse/index.js/ts` implementation file is not present in this local public checkout, so exact threshold constants such as 90% commit and 95% spawn-block cannot be source-verified here.

## Evaluation Of User Description

The description is directionally aligned with visible cc behavior:

* Collapse is a more granular active context restructuring layer.
* It runs before AutoCompact and can suppress/avoid AutoCompact by reducing pressure first.
* It preserves more granular context than full AutoCompact.
* It has an overflow recovery role before reactive compact.

Parts not source-verified from this checkout:

* Exact 90% commit threshold.
* Exact 95% spawn-block threshold.
* Exact spawn/fork blocking implementation.
* Exact internal grouping/commit algorithm.

Therefore, describe those as likely cc design details from non-visible context,
not as verified facts from the available source tree unless another source is
provided.

## Current `coding-deepgent` Alignment

Aligned:

* Collapse exists in runtime pressure pipeline.
* Collapse runs before AutoCompact.
* Collapse uses a summarizer and preserves recent tail.
* Collapse fail-open behavior preserves model call reliability.
* Collapse is live rewrite and does not physical-delete transcript.
* Collapse emits bounded runtime pressure event/evidence.

Not aligned / missing:

* No utilization-ratio trigger based on model context window percentage.
* No 90% staged commit threshold.
* No 95% spawn/subagent block.
* No persistent collapse store or commit log replay.
* No read-time projection over full raw history.
* No staged collapse drain before reactive compact.
* No explicit AutoCompact suppression beyond natural ordering.
* No grouping algorithm that selectively collapses message groups while retaining granular raw context.
* No fork/subagent interaction policy.

## Extra cc Collapse Highlights Worth Considering

### 1. Read-Time Projection Over Raw History

Collapse should be a projection over raw transcript, not a destructive rewrite.
Future UI/resume can show raw history while model-facing history uses collapse
projection.

### 2. Collapse Store / Commit Log

cc comments indicate summary messages live outside the REPL array and are replayed
by `projectView()`. This suggests a durable collapse record model similar to
compact records but more granular.

### 3. AutoCompact Avoidance

Collapse is valuable because it can reduce pressure enough to avoid full
AutoCompact, preserving more original context.

### 4. Overflow Drain Before Reactive Compact

On prompt-too-long, drain staged collapse first; only if that fails, run full
reactive compact.

### 5. Context-Window Percentage Thresholds

Instead of fixed token thresholds, use utilization ratio against model context
window when reliable model limits are available.

### 6. Spawn/Fork Pressure Policy

At high pressure, block or warn before spawning subagents because forked context
would multiply pressure. This should be planned carefully for our LangChain
subagent model.

### 7. Selective Group Collapse

Collapse should ideally summarize older message groups while preserving recent
groups and critical tool-call/tool-result pairs.

### 8. UI/Observability

Collapse records should be visible in future compression timeline with group IDs,
summary, affected message IDs, and trigger utilization.

## Requirements (Future)

* Decide whether to keep current live Collapse as MVP or plan a richer cc-style
  Collapse store/replay stage.
* If implementing richer Collapse, define:
  * context window utilization source,
  * group selection algorithm,
  * collapse record schema,
  * projection replay,
  * overflow drain behavior,
  * spawn/subagent gating policy.

## Acceptance Criteria (Future)

* [ ] Collapse can avoid AutoCompact when it reduces pressure below auto threshold.
* [ ] Collapse record/projection preserves raw transcript.
* [ ] Prompt-too-long recovery drains staged collapse before reactive compact.
* [ ] Collapse metadata is visible in recovery/timeline surfaces.
* [ ] Subagent spawn policy accounts for high context pressure if enabled.

## Out of Scope (Current)

* No implementation in this turn.
* No claim that 90%/95% thresholds are source-verified from current checkout.
* No frontend UI work now.

## Status

Research captured / planning-only.
