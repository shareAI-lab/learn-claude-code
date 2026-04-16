# cc-style time-based local microcompact

## Goal

实现 cc Level 2 MicroCompact 的非 API 本地亮点：在主会话自然暂停后，基于时间阈值主动清理旧的基础工具输出，保留最近工具结果和可恢复路径，并记录触发原因与节省 token。明确不做 provider `cache_edits` / `cache_reference` / cache editing API。

## Background

当前 `coding-deepgent` 已有基础 `MicroCompact`：

* `RuntimePressureMiddleware.wrap_model_call()` 调用 `microcompact_messages(...)`。
* 旧 eligible successful `ToolMessage` 会替换为 `[Old tool result content cleared]`。
* 保留最近 `keep_recent_tool_results` 个可压缩工具结果。
* 如果 tool result artifact 有 persisted output path，会保留路径提示。
* 该 rewrite 是 live model-call projection，不物理修改 transcript。

cc-haha `microCompact.ts` 的非 API 亮点：

* time-based trigger：距最后 assistant message 超过阈值时触发。
* main-thread/source gating：只在主线程明确 source 下触发。
* keepRecent floor：至少保留 1 个最近可压缩工具结果。
* compactable tool allowlist：只清基础执行工具。
* token saved accounting：记录清理收益。
* event/cache coordination：记录这是有意的 pressure action，未来可避免误判 cache drop。

## Requirements

### 1. Time-Based Trigger

* Add settings-backed time gap threshold, e.g. `microcompact_time_gap_minutes: int | None`.
* Time-based path only runs when enabled.
* Trigger computes gap from the latest assistant message timestamp/metadata available in the current model-call messages or runtime/session context.
* If no reliable assistant timestamp exists, fail open and skip time-based path.

### 2. Main-Thread Gating

* Time-based aggressive MicroCompact must only run for the main agent/session path.
* It must not run for verifier, subagent, compact summarizer, session-memory updater, or analysis-only contexts.
* Use `RuntimeContext` fields such as `agent_name`, `entrypoint`, `session_id`, or an explicit setting/flag rather than copying cc's `querySource` string model blindly.

### 3. Token Saved Accounting

* Estimate tokens saved for cleared tool results using deterministic local estimation.
* Runtime event/evidence metadata should include bounded fields:
  * `trigger == "time_gap"`
  * `gap_minutes`
  * `tools_cleared`
  * `tools_kept`
  * `tokens_saved_estimate`
  * `keep_recent`

### 4. Minimum Savings Threshold

* Add settings-backed threshold, e.g. `microcompact_min_saved_tokens`.
* If estimated savings are below threshold, skip clearing.
* This prevents noisy low-value microcompact events.

### 5. KeepRecent Floor

* Existing normal `keep_recent_tool_results` may continue to allow `0` for tests/manual behavior.
* Time-based/aggressive mode must use `max(1, configured_keep_recent)` to avoid clearing all working tool context.

### 6. Protected Tools / Allowlist Audit

* Keep using `ToolCapability.microcompact_eligible`.
* Audit default registry against cc's base execution-tool intent:
  * eligible: read/search/shell/web-fetch-like raw material tools
  * not eligible: memory, task, plan, skill, verifier/subagent semantic tools
* Document this distinction in runtime pressure contract.

## Acceptance Criteria

* [ ] Time-based MicroCompact does nothing when disabled.
* [ ] Time-based MicroCompact does nothing for non-main agent contexts.
* [ ] Time-based MicroCompact does nothing without a reliable assistant timestamp.
* [ ] Under threshold gap does not clear tool results.
* [ ] Over threshold gap clears older eligible tool results.
* [ ] Aggressive keepRecent floors to at least 1.
* [ ] Minimum savings threshold prevents low-value clears.
* [ ] Runtime event/evidence includes trigger, gap, cleared/kept counts, token savings estimate.
* [ ] Persisted output paths remain model-visible after clearing.
* [ ] Existing full `coding-deepgent/tests` pass.
* [ ] `ruff check` and targeted `mypy` pass.
* [ ] `.trellis/spec/backend/runtime-pressure-contracts.md` updated with executable contract.

## Out of Scope

* No `cache_edits`.
* No `cache_reference`.
* No `cache_deleted_input_tokens`.
* No provider-specific cache editing payloads.
* No physical deletion of transcript records.
* No cc-style semantic SnipTool.

## Technical Approach

Likely implementation shape:

* Add a time-based helper near `microcompact_messages(...)`:
  * `maybe_time_based_microcompact_messages(...)`
  * returns messages plus stats or `None`.
* Keep the current count-based `microcompact_messages(...)` as fallback/default behavior.
* In `RuntimePressureMiddleware.wrap_model_call()`:
  1. Snip
  2. Time-based MicroCompact if eligible
  3. Otherwise existing MicroCompact
  4. Collapse
  5. AutoCompact
* Use runtime context to gate main-agent eligibility.
* Extend runtime pressure event/evidence metadata with bounded token-saved fields.

## Technical Notes

Candidate files:

* `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`
* `coding-deepgent/src/coding_deepgent/settings.py`
* `coding-deepgent/src/coding_deepgent/containers/app.py`
* `coding-deepgent/src/coding_deepgent/sessions/evidence_events.py`
* `coding-deepgent/tests/test_runtime_pressure.py`
* `coding-deepgent/tests/test_app.py`
* `.trellis/spec/backend/runtime-pressure-contracts.md`

Source references:

* `/root/claude-code-haha/src/services/compact/microCompact.ts`
* `/root/claude-code-haha/src/services/compact/timeBasedMCConfig.ts`
* `/root/claude-code-haha/src/query.ts`

## Status

Checkpoint complete.

State: checkpoint

Verdict: APPROVE

Implemented:

* Added settings-backed `microcompact_time_gap_minutes` and
  `microcompact_min_saved_tokens`.
* Added main-context gating through configured `main_entrypoint` /
  `main_agent_name` wired from existing settings.
* Added timestamp-based trigger evaluation from `AIMessage` metadata.
* Added aggressive keepRecent floor for time-gap clears.
* Added minimum-savings skip behavior that prevents fallback count-based
  clearing in the same call once the time-gap trigger has fired.
* Added bounded `trigger == "time_gap"` and `gap_minutes` metadata.
* Preserved raw transcript and existing persisted-output path behavior.

Verification:

* `pytest -q tests/test_runtime_pressure.py` -> 26 passed.
* `pytest -q tests/test_app.py` -> 9 passed.
* `ruff check src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/compact/__init__.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py tests/test_runtime_pressure.py tests/test_app.py` -> passed.
* `mypy src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py` -> passed.

Alignment:

* source files inspected:
  * `/root/claude-code-haha/src/services/compact/microCompact.ts`
  * `/root/claude-code-haha/src/services/compact/timeBasedMCConfig.ts`
  * `/root/claude-code-haha/src/query.ts`
* aligned:
  * time-gap trigger based on latest assistant timestamp
  * explicit main-thread gating
  * keepRecent floor
  * local token-saved accounting
* deferred:
  * provider `cache_edits`
  * `cache_reference`
  * cache-deletion API coordination
* do-not-copy:
  * GrowthBook config plumbing
  * provider-specific cache APIs

Architecture:

* primitive used: existing LangChain middleware-level model-call projection.
* why no heavier abstraction: the behavior is a deterministic pre-model-call
  projection over the existing MicroCompact helper.

Boundary findings:

* No session schema migration needed.
* No raw transcript mutation introduced.
* Normal count-based MicroCompact remains available when time-gap trigger does
  not fire.

Decision: continue

Reason:

* This sub-stage is complete and verified.
* The next parent-plan task still holds because normal MicroCompact remains
  count-based rather than token-budget protected.
