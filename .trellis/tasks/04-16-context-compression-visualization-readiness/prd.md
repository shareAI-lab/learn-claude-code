# context compression visualization readiness

## Goal

为未来前端/可视化显示准备上下文系统的数据边界：用户应能看到完整 raw transcript，同时也能看到模型实际使用的 model-facing projection，以及 compact/snip/microcompact/collapse 等压缩事件的时间线和影响范围。

当前只创建 Trellis 占位任务，不在本轮实现。

## What I already know

* `coding-deepgent` 当前主线暂无真正前端产品层；`web/` 默认 reference-only。
* 后端已有部分前端友好基础：
  * `LoadedSession.history` 保留 raw history。
  * `LoadedSession.compacted_history` 表示 compact-aware continuation view。
  * `LoadedSession.compacts` 独立记录 compact records。
  * `LoadedSession.evidence` 可包含 runtime pressure events。
* 当前不足：
  * message records 没有稳定 `message_id`。
  * 当前 `snip` 不是 cc-style selective removal，也没有 removed refs replay。
  * runtime pressure events 未完整记录 affected message/tool ids。
  * 没有 compression timeline query/API。
  * 没有 raw transcript vs model-facing projection diff/view。

## Requirements (Future)

* Add stable message IDs for persisted session message records.
* Add a compression timeline data model that can represent:
  * compact records,
  * runtime pressure events,
  * future snip boundaries,
  * future microcompact affected tool IDs,
  * future collapse/auto-compact summaries.
* Preserve raw transcript append-only.
* Provide a model-facing projection view separately from raw transcript.
* Record enough metadata for UI to explain why a message/tool result is hidden,
  summarized, pruned, or still visible.
* Keep frontend/web implementation out of scope until product UI is explicitly targeted.

## Acceptance Criteria (Future)

* [ ] Raw transcript can be loaded without applying compression filters.
* [ ] Model-facing projection can be loaded or derived with source metadata.
* [ ] Compression timeline can show event type, trigger, affected IDs, and summary.
* [ ] UI can distinguish raw-hidden vs model-visible content.
* [ ] Existing resume/compact tests continue to pass.

## Out of Scope (Current)

* No implementation in this turn.
* No UI component work now.
* No API/server surface unless a future product UI task requires it.
* No physical deletion of transcript records.

## Technical Notes

Candidate backend surfaces:

* `coding-deepgent/src/coding_deepgent/sessions/records.py`
* `coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py`
* `coding-deepgent/src/coding_deepgent/sessions/resume.py`
* `coding-deepgent/src/coding_deepgent/sessions/evidence_events.py`
* `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`
* `.trellis/spec/backend/session-compact-contracts.md`
* `.trellis/spec/backend/runtime-pressure-contracts.md`

## Status

Planning-only placeholder.
