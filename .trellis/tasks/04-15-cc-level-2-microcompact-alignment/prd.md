# brainstorm: cc level 2 microcompact alignment

## Goal

评审用户提供的 `Level 2: MicroCompact` 描述是否符合 cc-haha 源码功能，并判断 `coding-deepgent` 是否需要补充功能说明或后续实现任务。

## Communication Requirement

When explaining MicroCompact or other context compression levels, lead with
concrete scenarios and visible effects, then map to implementation names. Avoid
mechanism-only explanations.

## What I already know

* 当前 `coding-deepgent` 已有 `microcompact_messages(...)`，按 eligible tool results 数量保留最近 N 个，旧结果替换为 `[Old tool result content cleared]`。
* 当前实现是 live model-call rewrite，不持久化 transcript，不包含时间触发、cache editing、prompt cache 过期判断。
* 用户提供的 Level 2 描述强调：时间触发、服务端 prompt cache 过期、主线程判断、保留最近 N 个可压缩工具结果、cache editing 高级路径。

## Source Notes

cc-haha source reviewed:

* `/root/claude-code-haha/src/services/compact/microCompact.ts`
* `/root/claude-code-haha/src/services/compact/apiMicrocompact.ts`
* `/root/claude-code-haha/src/services/compact/timeBasedMCConfig.ts`
* `/root/claude-code-haha/src/query.ts`

Key source-backed facts:

* `TIME_BASED_MC_CLEARED_MESSAGE` is `[Old tool result content cleared]`.
* `COMPACTABLE_TOOLS` includes file read, shell tools, grep, glob, web search, web fetch, edit, and write.
* `microcompactMessages(...)` first runs `maybeTimeBasedMicrocompact(...)`; if it fires, it short-circuits and skips cached microcompact.
* Time-based trigger checks:
  * config enabled,
  * explicit `querySource`,
  * main-thread source,
  * last assistant message exists,
  * time since last assistant exceeds `config.gapThresholdMinutes`.
* Time-based microcompact collects compactable tool-use IDs, keeps `Math.max(1, config.keepRecent)` most recent IDs, and clears older matching `tool_result` blocks.
* It logs `gapMinutes`, threshold, tools cleared/kept, keepRecent, and tokensSaved.
* It calls `resetMicrocompactState()` because content mutation invalidates cached microcompact state.
* It notifies prompt-cache break detection through `notifyCacheDeletion(querySource)` when enabled.
* Cached microcompact path is separate and feature-gated. It does not mutate local message content; it registers tool results, computes tools to delete, creates pending `cache_edits`, logs analytics, and defers boundary emission until after API response.
* `apiMicrocompact.ts` defines API-side context management strategies such as `clear_tool_uses_20250919` and `clear_thinking_20251015`.

## Evaluation

用户提供的描述整体符合 cc-haha source-visible behavior。

Important clarifications:

* Time-based microcompact does not mean “regardless of content importance” in a semantic sense; it only clears compactable tool results and still keeps recent configured tool results.
* It requires explicit main-thread query source; analysis-only callers without source should not trigger it.
* Cached microcompact is not just “无损优化”; it is API-layer cache editing that avoids mutating local messages and depends on model/support/feature gates.
* Time-based path and cached path are mutually exclusive for that request: time-based fires first and short-circuits.
* Notebook edit appears in API microcompact clearable uses, while `microCompact.ts` compactable tools include edit/write/read/shell/search/web tools visible in this checkout.

## Requirements (Future)

* Decide whether to add cc-style time-based trigger to `coding-deepgent`.
* Decide whether to model prompt-cache state locally or keep this documented as deferred provider-specific behavior.
* User currently wants to explore `cached microcompact` specifically.
* If implemented, ensure main-thread/session-only boundary and avoid running in subagents/analyzers.
* Preserve current MicroCompact marker/path behavior.
* Add bounded runtime events for time-triggered microcompact with gap and tokens saved.

## Acceptance Criteria (Future)

* [ ] Time-based trigger only fires when enabled and source/session is eligible.
* [ ] Trigger keeps at least one recent compactable tool result.
* [ ] Older eligible tool results are cleared with `[Old tool result content cleared]`.
* [ ] Cached/API microcompact remains deferred unless provider support is explicit.
* [ ] Tests cover disabled, wrong source, no assistant, under threshold, clearable results, and keepRecent floor.

## Out of Scope (Current)

* No implementation in this turn.
* No provider-specific cache editing implementation now.
* No exact prompt-cache TTL integration now.

## Status

Research captured / planning-only. User is considering cached microcompact as a future implementation direction.

## Cached MicroCompact Difficulty Notes

Cached microcompact is harder than time-based microcompact because it tries to
remove old tool results without rewriting local message content and without
breaking the provider-side prompt cache prefix.

Concrete difficulties:

* Provider support: cc's implementation is Anthropic/cache-editing specific
  (`cache_edits`, `cache_reference`, `cache_deleted_input_tokens`). Our current
  `coding-deepgent` stack is OpenAI-compatible LangChain first, so we need to
  verify whether the active provider exposes an equivalent API-level context edit
  primitive.
* LangChain abstraction: `RuntimePressureMiddleware.wrap_model_call()` can
  replace `request.messages`, but API-level cache edits may require model
  request kwargs, provider-specific payload fields, or a custom model adapter.
  That risks breaking the "LangChain-native, no custom query loop" boundary.
* Stable tool-result identity: cached microcompact tracks tool results by
  `tool_use_id` and original user-message position. Our LangChain `ToolMessage`
  has `tool_call_id`, but request-level placement and replay across turns must
  be stable enough to pin edits.
* State lifecycle: cc keeps module-level cached MC state with registered tool
  results, deleted refs, pinned edits, and reset behavior. We need a session-
  scoped state owner, not global mutable state, so subagents and resumed sessions
  do not leak tool IDs into each other.
* Main-thread isolation: cc explicitly avoids forked agents / session_memory /
  analyzers. We need an equivalent boundary using `RuntimeContext.agent_name`,
  `entrypoint`, or explicit settings.
* Warm-cache assumptions: cached microcompact only helps when provider cache is
  warm. If the cache is cold or time-based path already mutated content, cache
  edits can be useless or wrong. We would need cache-read/drop signals before
  deciding when to use it.
* Boundary/event timing: cc defers boundary emission until after API response so
  it can use actual `cache_deleted_input_tokens`. Our current event/evidence path
  emits before/around model call and has no provider token-delete metric.
* Interaction with current MicroCompact: existing live rewrite changes content
  to `[Old tool result content cleared]`. Cached microcompact must not also
  content-rewrite the same results, or it destroys the cache-prefix benefit.
* Interaction with tool-result persistence: if a deleted tool result had a
  persisted output path, the model still needs a way to recover it. Cache edit
  deletion must preserve or re-inject path hints somewhere bounded.
* Failure and reset semantics: if provider call fails, if cache edit is rejected,
  or if a later turn no longer contains the pinned position, the cached edit
  state must fail open and reset safely.
* Testing difficulty: unit tests need fake provider/model surfaces that can
  assert cache edit payloads and simulated `cache_deleted_input_tokens`, not just
  final message content.

## Non-API MicroCompact Highlights Worth Considering

User does not currently plan to implement provider API cache editing. Excluding
that path, cc still has several useful MicroCompact details:

### 1. Time-Based Trigger

* Detects a natural pause by measuring minutes since the last assistant message.
* Only fires when feature/config is enabled, source is explicit, and source is
  main-thread.
* Rationale: if the provider prompt cache is probably cold, content rewriting no
  longer sacrifices useful cache hits and can reduce the next request payload.

Potential local value:

* Add `microcompact_gap_threshold_minutes` and only run aggressive tool-output
  clearing after idle gaps.
* This is provider-independent if treated as a local heuristic, even without
  real cache editing.

### 2. Main-Thread / Source Gating

* cc avoids triggering time-based MicroCompact for analysis-only calls,
  compact/session-memory paths, or forked agents.
* It requires explicit `querySource`; `undefined` does not trigger the time-based
  path even though cached-MC treats undefined as main-thread for backward
  compatibility.

Potential local value:

* Gate aggressive MicroCompact to main `RuntimeContext` only.
* Prevent verifier/subagent/summarizer paths from clearing tool outputs that
  belong to another conversation.

### 3. KeepRecent Floor

* cc applies `Math.max(1, config.keepRecent)` because clearing all tool results
  leaves the model with no working tool context.

Potential local value:

* Our `keep_recent_tool_results` currently allows `0`. For aggressive/time-based
  mode, use a separate keep-recent floor of at least 1.

### 4. Compactable Tool Allowlist

* cc restricts clearing to a known set: file read, shell, grep, glob, web search,
  web fetch, edit, write.

Potential local value:

* Keep using capability metadata (`microcompact_eligible`) but audit default
  registry against cc's allowlist.
* Avoid clearing semantic/state tools such as memory, task, plan, skills, or
  verifier outputs.

### 5. Token Saved Accounting

* cc estimates tokens for cleared tool results and logs `tokensSaved`.
* It records `gapMinutes`, threshold, tools cleared, tools kept, keepRecent, and
  tokens saved.

Potential local value:

* Runtime pressure evidence should include bounded `tokens_saved_estimate`,
  `tools_cleared`, and trigger reason for observability and future UI.

### 6. Cache Break / Warning Coordination

* After time-based content clearing, cc resets cached microcompact state and
  notifies prompt-cache break detection to avoid false alarms.

Potential local value:

* If we later add cache/cost observability, local MicroCompact should emit a
  clear event so cache-drop diagnostics know the drop was intentional.

### 7. Path Split Between Time-Based And Cached Paths

* Time-based path fires first and short-circuits.
* Cached path runs only when time-based did not fire and cache is expected warm.

Potential local value:

* Keep local MicroCompact modes mutually exclusive:
  * idle/time-based content clear,
  * count/budget live rewrite,
  * future cached API path.

### 8. External Build Fallback

* cc comments indicate legacy microcompact path was removed; where cached MC is
  unavailable and time-based does not fire, autocompact handles pressure.

Potential local value:

* Avoid over-expanding local MicroCompact into a second full compaction system.
  Let Collapse/AutoCompact handle semantic pressure.
