# brainstorm: cc level 4 autocompact alignment

## Goal

评估用户提供的 `Level 4: AutoCompact` 描述是否符合 cc-haha 源码功能，判断当前 `coding-deepgent` 是否对齐，并记录后续可补充的 AutoCompact 亮点。

## Communication Requirement

When discussing context compression levels with the user, explain behavior through
concrete scenarios first. Avoid listing only mechanism names such as
`CompactionResult`, hooks, fork, telemetry, or boundary without explaining what
the user/agent sees and what problem it solves.

Preferred explanation style:

* Start with a realistic long-session coding scenario.
* Show what happens before compaction.
* Show what AutoCompact changes in model-facing context.
* Then map that behavior to implementation terms only after the scenario is
  clear.

## What I already know

* 当前 `coding-deepgent` 已有 live `AutoCompact`：
  * `maybe_auto_compact_messages(...)`
  * `compact_live_messages_with_summary(...)`
  * `reactive_compact_messages(...)`
* 当前实现超过阈值后调用 summarizer，生成 boundary + summary + optional restoration paths + preserved recent tail。
* 当前实现没有 PreCompact/PostCompact hooks、forked compact agent、prompt-cache sharing、partial compact、post-compact attachment restoration、failure circuit breaker 等完整 cc 功能。

## Source Notes

cc-haha source reviewed:

* `/root/claude-code-haha/src/services/compact/autoCompact.ts`
* `/root/claude-code-haha/src/services/compact/compact.ts`
* `/root/claude-code-haha/src/commands/compact/compact.ts`

Key source-backed facts:

* `autoCompactIfNeeded(...)` calls `shouldAutoCompact(...)`, then tries `trySessionMemoryCompaction(...)` before legacy `compactConversation(...)`.
* AutoCompact has recursion guards for `session_memory` and `compact` query sources.
* AutoCompact is disabled/suppressed when context-collapse mode owns context pressure.
* AutoCompact has a consecutive failure circuit breaker (`MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`).
* Effective context window reserves output tokens for summary.
* `compactConversation(...)` executes PreCompact hooks, merges hook-provided instructions with user instructions, then streams compact summary.
* If the compact request itself hits prompt-too-long, it truncates oldest API-round groups and retries up to `MAX_PTL_RETRIES = 3`.
* `CompactionResult` includes `boundaryMarker`, `summaryMessages`, `attachments`, `hookResults`, optional `messagesToKeep`, user display message, pre/post token counts, true post-compact token count, and compaction usage.
* `buildPostCompactMessages(...)` establishes output order: boundary marker, summary messages, messagesToKeep, attachments, hookResults.
* `streamCompactSummary(...)` may use a forked compact agent with `maxTurns: 1`, `canUseTool` denying tool use, `querySource: 'compact'`, `forkLabel: 'compact'`, and `skipCacheWrite: true`, falling back to regular streaming on failure.
* Post-compact context restoration includes file attachments, async agent attachments, plan attachment, plan mode attachment, skill attachment, deferred tools delta, agent listing delta, MCP instructions delta, and SessionStart hook messages.
* PostCompact hooks run after compaction and can provide user display messages.
* Telemetry records pre/post token counts, true post-compact token count, will-retrigger-next-turn, compaction usage, cache read/create tokens, query chain, recompaction information, and context breakdown.
* Prompt-cache break detection is notified after compaction.

## Evaluation Of User Description

The user description is largely source-aligned:

* AutoCompact is a costly fallback that calls an LLM to summarize.
* `compactConversation(...)` is the core full compaction path.
* PreCompact and PostCompact hooks exist.
* Compact prompt selection/custom instruction merging exists.
* Summary generation can use forked agent and denies tool use.
* Prompt-too-long retry truncates oldest API-round groups and retries up to 3 times.
* `CompactionResult` includes boundary, summary, attachments, hook results, messagesToKeep, token counts.
* `buildPostCompactMessages(...)` ensures consistent output order.

Useful corrections/clarifications:

* AutoCompact first tries session-memory compaction before legacy full compaction.
* Context-collapse mode can suppress proactive AutoCompact so Collapse owns the headroom problem, while reactive compact remains available as a fallback.
* Forked compact agent is an optimization for prompt-cache sharing and has a streaming fallback path.
* Post-compact attachments are broader than generic “attachments”: they include file restore, async agents, plan, plan mode, skills, tool/agent/MCP deltas, and SessionStart hook messages.
* Compact summary is not allowed to call tools because `createCompactCanUseTool()` denies all tool use.
* There is a failure circuit breaker to avoid repeated doomed autocompact attempts.

## Current `coding-deepgent` Alignment

Aligned:

* AutoCompact exists after Snip/MicroCompact/Collapse.
* It calls a summarizer and produces summary + recent tail.
* It preserves tool-call/tool-result pairing in preserved tail.
* It can include restoration paths for compacted-away persisted tool outputs.
* It fail-opens on proactive summarizer failure.
* Reactive compact retries once after prompt-too-long.
* Session memory can assist summary and can be refreshed from generated summary.
* Manual/generated resume compact records exist separately from raw history.

Not aligned / missing:

* No session-memory-first compact path that replaces full compact when memory is good enough.
* No PreCompact/PostCompact hook lifecycle.
* No forked compact agent with one-turn, no-tools execution.
* No prompt-cache sharing optimization.
* No compact request prompt-too-long retry that truncates oldest API-round groups up to 3 times.
* No `CompactionResult` object with full boundary/attachments/hookResults/messagesToKeep/token accounting.
* No broad post-compact restoration for file attachments, async agents, plan mode, skills, tool/agent/MCP deltas.
* No failure circuit breaker for repeated AutoCompact failures.
* No will-retrigger-next-turn / true post-compact token count telemetry.
* No compact progress/status events.
* No partial compact path.

## Extra cc AutoCompact Highlights Worth Considering

### 1. Session-Memory-First Compact

Try a session-memory-based compact before full summarization when memory is
current and enough to continue.

### 2. Failure Circuit Breaker

Track consecutive AutoCompact failures and stop retrying after a small limit.

### 3. Compact Request PTL Retry

If the compact summarizer call itself is too large, drop oldest API-round groups
and retry up to a bounded count.

### 4. Compact Agent Isolation

Run summary generation through a restricted compact subagent that cannot call
tools and runs only one turn.

### 5. Post-Compact Context Restoration

Restore file paths, plan/plan-mode state, loaded skills, async agent status, tool
schema deltas, agent listings, MCP instructions, and session-start hook context
after summary.

### 6. Structured CompactionResult

Return/record a structured result with boundary, summary messages, kept messages,
attachments, hook results, token counts, and usage.

### 7. Telemetry / UI Progress

Emit progress and final compaction telemetry for future frontend/timeline and
debugging.

### 8. AutoCompact Suppression By Collapse

When richer Collapse is enabled, let Collapse own proactive headroom management;
keep reactive compact as fallback.

## Requirements (Future)

If implementing richer AutoCompact, decide which stage to pursue first:

* minimal failure circuit breaker,
* compact request PTL retry,
* structured CompactionResult,
* post-compact restoration,
* compact subagent isolation,
* PreCompact/PostCompact hook lifecycle.

## Acceptance Criteria (Future)

* [ ] AutoCompact repeated failures stop after a bounded count.
* [ ] Compact summarizer prompt-too-long retries by dropping oldest groups.
* [ ] Compaction result has stable structured fields.
* [ ] Post-compact model-facing context preserves required runtime state.
* [ ] Compact summary generation cannot call tools.
* [ ] Hooks can add bounded instructions/context around compact.
* [ ] Runtime pressure/session compact contracts updated.

## Out of Scope (Current)

* No implementation in this turn.
* No provider-specific prompt-cache sharing unless separately planned.
* No frontend progress UI now.

## Status

Research captured / planning-only.
