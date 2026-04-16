# autocompact failure circuit breaker

## Goal

给 proactive AutoCompact 增加连续失败 circuit breaker：当 summarizer 连续失败时，后续 model calls 不再反复尝试 doomed auto-compact，避免持续浪费 API 时间和噪音事件，同时保持 reactive prompt-too-long fallback 的既有行为。

## Expected Effect

如果 live AutoCompact summarizer 连续失败，runtime pressure middleware 会记录 bounded skip event 并跳过后续 proactive AutoCompact，直到一次成功 compact 重置失败计数。失败时继续 fail-open，不能破坏当前模型调用。

## Requirements

- Add settings-backed `auto_compact_max_failures: int | None`.
- Track consecutive proactive AutoCompact failures on the middleware instance.
- Increment failure count only when threshold crossing attempted proactive AutoCompact and summarizer failed/returned invalid summary.
- Reset failure count after successful proactive AutoCompact.
- When failure count reaches max, skip proactive AutoCompact for later model calls.
- Emit bounded runtime event/evidence metadata for skip:
  - `event_kind == "auto_compact"`
  - `strategy == "auto"`
  - `trigger == "failure_circuit_breaker"`
  - `failure_count`
  - `max_failures`
- Do not change reactive compact retry semantics.

## Acceptance Criteria

- [ ] Repeated proactive AutoCompact failures stop after configured max failures.
- [ ] Successful proactive AutoCompact resets failure count.
- [ ] Skip emits bounded runtime event/evidence metadata.
- [ ] `auto_compact_max_failures is None` preserves current fail-open behavior.
- [ ] Existing reactive compact tests remain valid.
- [ ] Runtime pressure contract updated.
- [ ] Focused tests, ruff, and targeted mypy pass.

## Source Evidence

- `/root/claude-code-haha/src/services/compact/autoCompact.ts`
- `/root/claude-code-haha/src/services/compact/compact.ts`
- Source PRD: `.trellis/tasks/04-16-cc-style-autocompact-hardening/prd.md`

## Out of Scope

- No compact request prompt-too-long retry in this sub-stage.
- No structured compaction result yet.
- No restoration contributions or hooks.
- No provider-specific prompt-cache behavior.

## Status

Checkpoint complete.

State: checkpoint

Verdict: APPROVE

Implemented:

- Added settings-backed `auto_compact_max_failures`.
- Added `AutoCompactResult` and `maybe_auto_compact_messages_with_status(...)`.
- Preserved `maybe_auto_compact_messages(...)` as a compatibility wrapper.
- Added middleware-owned consecutive proactive AutoCompact failure counter.
- Incremented failure count only when proactive threshold was crossed and
  summarization/compaction failed open.
- Reset failure count after successful proactive AutoCompact.
- Added bounded skip event/evidence metadata when circuit breaker trips.

Verification:

- `pytest -q tests/test_runtime_pressure.py` -> 32 passed.
- `pytest -q tests/test_app.py` -> 9 passed.
- `ruff check src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/compact/__init__.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py tests/test_runtime_pressure.py tests/test_app.py` -> passed.
- `mypy src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py` -> passed.

Alignment:

- source files inspected:
  - `/root/claude-code-haha/src/services/compact/autoCompact.ts`
  - `/root/claude-code-haha/src/services/compact/compact.ts`
- aligned:
  - consecutive failure count
  - reset on successful compact
  - skip future proactive attempts after max failures
- deferred:
  - compact request PTL retry
  - structured compaction result
  - post-compact restoration and hooks
- do-not-copy:
  - cc-specific analytics/logging implementation
  - provider cache details

Architecture:

- primitive used: existing runtime pressure middleware state and runtime event seam.
- why no heavier abstraction: the circuit breaker is local to proactive
  AutoCompact attempts and does not need new persistence.

Boundary findings:

- Reactive compact retry remains unchanged.
- Skip evidence is bounded metadata only.
- Default `auto_compact_max_failures is None` preserves previous fail-open behavior.

Decision: continue

Reason:

- The sub-stage is complete and verified.
- Parent plan next stage remains valid: compact request prompt-too-long retry
  is a separate summarizer-source preparation concern.
