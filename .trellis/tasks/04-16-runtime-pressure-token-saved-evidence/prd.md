# runtime pressure token saved evidence

## Goal

为现有 runtime pressure / MicroCompact 事件补齐可恢复的节省量观测字段，让后续 time-based MicroCompact、opencode-style tool-output pruning、以及未来 compression timeline 可以复用同一套 bounded evidence metadata。

## Expected Effect

当 live MicroCompact 清理旧工具输出时，runtime event 和 session evidence 应能说明这次清理大概节省了多少上下文，以及清理/保留了多少工具结果。这个变化提升 observability 和后续可视化准备，但不改变模型实际看到的清理语义。

## Requirements

- 对 MicroCompact 事件增加 bounded metadata：
  - `tools_cleared`
  - `tools_kept`
  - `tokens_saved_estimate`
  - `keep_recent`
- 字段必须来自确定性的本地估算，不代表 provider billing/tokenizer 数字。
- 继续保留现有 `cleared_tool_results` 字段兼容当前 runtime pressure contract。
- metadata 不得包含 raw tool output、raw prompt、raw summary。
- 不持久化修改 raw transcript。
- 不实现 time-based MicroCompact trigger。
- 不实现 token-budget pruning。

## Acceptance Criteria

- [ ] MicroCompact helper 可返回或暴露清理统计信息。
- [ ] `RuntimePressureMiddleware.wrap_model_call()` 发出的 `microcompact` event 包含新增 bounded metadata。
- [ ] active `session_context` 下追加的 session evidence 保留新增 bounded metadata。
- [ ] 未发生 MicroCompact 时不发出噪音事件。
- [ ] 现有 MicroCompact 清理语义保持兼容。
- [ ] `.trellis/spec/backend/runtime-pressure-contracts.md` 更新新增字段契约。
- [ ] `coding-deepgent/tests/test_runtime_pressure.py` 覆盖新增 metadata。
- [ ] 相关 focused tests、ruff、targeted mypy 通过。

## Technical Notes

Likely files:

- `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`
- `coding-deepgent/src/coding_deepgent/sessions/evidence_events.py`
- `coding-deepgent/tests/test_runtime_pressure.py`
- `.trellis/spec/backend/runtime-pressure-contracts.md`

## Out of Scope

- No provider-specific exact tokenizer.
- No provider cache-edit payloads.
- No session record schema migration.
- No frontend UI/API.
- No physical deletion of transcript records.

## Checkpoint

State: checkpoint

Verdict: APPROVE

Implemented:

- Added `MicrocompactStats` / `MicrocompactResult` and `microcompact_messages_with_stats(...)`.
- Added bounded `tools_cleared`, `tools_kept`, `tokens_saved_estimate`, and `keep_recent` metadata for `microcompact` runtime events.
- Preserved `cleared_tool_results` for backward compatibility.
- Extended runtime event evidence metadata filtering to preserve the new bounded fields.
- Updated runtime pressure contracts with the executable stats/event contract.

Verification:

- `pytest -q tests/test_runtime_pressure.py` -> 20 passed.
- `pytest -q tests/test_app.py` -> 9 passed.
- `ruff check src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/compact/__init__.py src/coding_deepgent/sessions/evidence_events.py tests/test_runtime_pressure.py` -> passed.
- `mypy src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/sessions/evidence_events.py` -> passed.

Alignment:

- source files inspected: current local runtime pressure implementation and runtime pressure Trellis contracts.
- aligned: local bounded observability for MicroCompact token savings.
- deferred: time-based trigger, token-budget pruning, provider cache-edit APIs.
- do-not-copy: provider-specific exact tokenizer/billing semantics.

Architecture:

- primitive used: existing LangChain middleware-level runtime event/evidence seams.
- why no heavier abstraction: this sub-stage only needs deterministic stats on the existing live projection helper.

Boundary findings:

- No session schema migration needed.
- No raw transcript mutation introduced.
- New fields are bounded integers only.

Decision: continue

Reason:

- The sub-stage is complete, verified, and unblocks `time-based-local-microcompact`.
