# cc-style collapse store and pressure guard

## Goal

规划实现更接近 cc Level 3 Collapse 的上下文重构系统：从当前一次性 live collapse，升级为可记录、可重放、可观测、能参与 spawn/subagent 压力控制和 overflow recovery 的 collapse subsystem。

当前只创建 Trellis planning task，不在本轮实现。

## Background

当前 `coding-deepgent` 已有 MVP Collapse：

* `maybe_collapse_messages(...)` 在 `RuntimePressureMiddleware.wrap_model_call()` 中运行。
* Collapse 在 `MicroCompact` 后、`AutoCompact` 前。
* 使用 summarizer 生成 live summary，保留 recent tail。
* 失败时 fail-open。
* 不物理删除 transcript。

cc-haha 可见源码显示更完整的 Collapse 设计：

* Collapse 是 read-time projection over raw history。
* Summary messages live in a collapse store, not the REPL array。
* `projectView()` replays commit log across turns。
* Collapse runs before AutoCompact to preserve granular context and avoid full summary when possible。
* prompt-too-long recovery tries collapse drain before reactive compact。
* 用户提到的 90% commit / 95% spawn block 属于目标行为，但当前 checkout 中具体实现文件不可见，需实现前再次 source-verify 或作为本地产品决策。

## Planned Feature Points

### 1. Collapse Records

Record durable collapse artifacts without deleting raw transcript.

Required future behavior:

* Add a collapse record type or structured evidence/state entry.
* Record affected message IDs/ranges.
* Record summary text.
* Record trigger reason and estimated pressure.
* Record created timestamp and model/context source.

Example shape:

```json
{
  "record_type": "collapse",
  "collapse_id": "collapse-001",
  "covered_message_ids": ["msg-001", "msg-002"],
  "summary": "Research phase summary...",
  "trigger": "pressure_ratio",
  "estimated_token_ratio": 0.91
}
```

### 2. Projection Replay

Derive model-facing context from raw history plus collapse records.

Required future behavior:

* Raw transcript remains complete.
* Model-facing projection replaces covered message ranges with collapse summaries.
* Replay is deterministic across session resume.
* Projection metadata explains which raw messages were hidden by which collapse.

### 3. Pressure Ratio Trigger

Trigger collapse based on estimated utilization of model context window.

Required future behavior:

* Compute `estimated_tokens / model_context_window`.
* Trigger staged collapse around configurable threshold, e.g. `collapse_commit_ratio`.
* Prefer ratio-based pressure when reliable model context window is available.
* Keep fallback token threshold for providers without reliable limits.

### 4. Spawn Guard

Prevent or warn on subagent/fork spawn when context pressure is too high.

Required future behavior:

* Before `run_subagent` or verifier-like child execution, check pressure ratio.
* If above configured threshold, return a bounded warning/error or require collapse first.
* Avoid blocking lightweight verifier paths unless explicitly configured.
* Record guard event in runtime evidence.

### 5. Overflow Drain

When prompt-too-long occurs, drain existing collapse summaries before full reactive compact.

Required future behavior:

* Detect prompt-too-long after proactive collapse.
* If collapse records exist, produce a more compact projection by tightening/draining collapse summaries.
* Retry once with drained collapse projection.
* If still too long, fall through to existing reactive compact.

## Acceptance Criteria (Future)

* [ ] Collapse records persist separately from raw messages.
* [ ] Loading a session can derive raw history and collapse-projected history separately.
* [ ] Collapse replay is deterministic and tested across resume.
* [ ] Pressure ratio trigger can fire before AutoCompact.
* [ ] Collapse can avoid AutoCompact when it reduces pressure below threshold.
* [ ] Spawn guard blocks or warns according to configured pressure threshold.
* [ ] Prompt-too-long path drains collapse projection before reactive compact.
* [ ] Frontend/timeline surfaces can explain collapse events and affected messages.
* [ ] Existing compact/session/runtime pressure tests continue to pass.

## Out of Scope (Current)

* No implementation in this turn.
* No frontend UI work in this task.
* No physical deletion of raw transcript records.
* No claim that exact cc 90%/95% constants are source-verified in this checkout.
* No provider-specific exact tokenizer requirement unless separately planned.

## Technical Notes

Likely backend surfaces:

* `coding-deepgent/src/coding_deepgent/sessions/records.py`
* `coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py`
* `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`
* `coding-deepgent/src/coding_deepgent/subagents/tools.py`
* `coding-deepgent/src/coding_deepgent/settings.py`
* `coding-deepgent/tests/test_sessions.py`
* `coding-deepgent/tests/test_runtime_pressure.py`
* `coding-deepgent/tests/test_subagents.py`
* `.trellis/spec/backend/runtime-pressure-contracts.md`
* `.trellis/spec/backend/session-compact-contracts.md`

Source references:

* `/root/claude-code-haha/src/query.ts`
  * `contextCollapse.applyCollapsesIfNeeded(...)`
  * comments around read-time projection, collapse store, commit log replay
  * prompt-too-long recovery with `recoverFromOverflow(...)`

## Status

Planning-only placeholder. Ready for future staged implementation.
