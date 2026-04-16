# opencode-style auto tool output prune

## Goal

占位规划一个未来增强：把当前 `MicroCompact` 的旧工具输出清理能力，升级为更接近 opencode `SessionCompaction.prune()` 的自动工具输出 pruning 策略。当前只记录任务和范围，不在本轮实现。

## Background

当前 `coding-deepgent` 已有 MVP 级 Auto Tool Output Prune：

* `RuntimePressureMiddleware` 每次 model call 前运行 `microcompact_messages(...)`。
* 只处理 eligible successful `ToolMessage`。
* 保留最近 `keep_recent_tool_results` 个 compactable tool results。
* 更旧结果替换为 `[Old tool result content cleared]`。
* 若结果 artifact 有 persisted output path，则保留该 path。
* 这是 live rewrite，不直接持久化 transcript。

opencode 的 `SessionCompaction.prune()` 提供了更强的参考策略：

* 从最新消息往旧消息倒序扫描。
* 至少保护最近两个 user turns。
* 遇到 assistant summary 或已 compacted tool output 时停止。
* 跳过 protected tools，例如 `skill`。
* 统计 completed tool output tokens。
* 保留最近约 `PRUNE_PROTECT = 40_000` tokens 的工具输出。
* 只有预计释放超过 `PRUNE_MINIMUM = 20_000` tokens 时才执行。
* 将旧 tool part 标记为 compacted，渲染给模型时输出 `[Old tool result content cleared]`。

## Requirements (Future)

* Replace or extend count-based `keep_recent_tool_results` with token-budget based protection.
* Add a minimum estimated-token savings threshold before pruning.
* Preserve tool-call/tool-result pairing and current persisted-output path behavior.
* Keep protected tool outputs unpruned through capability metadata or explicit config.
* Decide whether pruning remains live-only or persists a compacted marker/state.
* Keep behavior LangChain-native and inside runtime pressure/session boundaries.

## Acceptance Criteria (Future)

* [ ] Old completed eligible tool outputs beyond protected recent-token budget are pruned.
* [ ] Recent protected-token window remains inline.
* [ ] Protected tools are never pruned.
* [ ] No pruning happens when estimated savings are below threshold.
* [ ] Persisted output paths remain model-visible after pruning.
* [ ] Existing `MicroCompact` tests either remain valid or are replaced by stronger budget-based tests.
* [ ] Runtime pressure contracts are updated with executable signatures, matrix, and tests.

## Out of Scope (Current)

* No implementation in this turn.
* No cc-style semantic SnipTool.
* No physical deletion of session transcript records.
* No provider-specific exact tokenizer integration unless separately approved.

## Technical Notes

* Candidate files:
  * `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`
  * `coding-deepgent/src/coding_deepgent/tool_system/capabilities.py`
  * `coding-deepgent/src/coding_deepgent/settings.py`
  * `coding-deepgent/tests/test_runtime_pressure.py`
  * `.trellis/spec/backend/runtime-pressure-contracts.md`
* Reference:
  * `sst/opencode`: `packages/opencode/src/session/compaction.ts`
  * `sst/opencode`: `packages/opencode/src/session/message-v2.ts`
  * `sst/opencode`: `packages/opencode/src/tool/truncate.ts`

## Status

Planning-only placeholder. Current MVP remains the existing `MicroCompact`.
