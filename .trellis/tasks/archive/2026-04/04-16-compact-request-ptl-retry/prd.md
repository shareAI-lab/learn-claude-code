# compact request ptl retry

## Goal

当 proactive AutoCompact 的 summarizer 请求本身 prompt-too-long 时，裁掉最老的 summary source 消息后 bounded retry，而不是立即放弃。该行为只影响 summarizer source，不修改 raw transcript，也不改变 reactive model-call retry 语义。

## Expected Effect

超长历史下，AutoCompact 更有机会成功生成 summary。即使 compact request 太长，也最多重试有限次数，失败后继续 fail-open，不破坏主模型调用。

## Requirements

- Add settings-backed `auto_compact_ptl_retry_limit: int`.
- Detect prompt-too-long style errors from the compact summarizer call.
- On each retry, drop the oldest message group from the summarizer source.
- Retry count must be bounded.
- Preserve tool-call/tool-result pairing in the remaining summary source as much as possible.
- If retries still fail, return original model-facing messages and count as proactive AutoCompact failure for the circuit breaker.
- Do not change `reactive_compact_messages(...)` retry semantics.

## Acceptance Criteria

- [ ] Prompt-too-long from proactive compact summarizer retries with older source removed.
- [ ] Retry count is bounded by setting.
- [ ] Non prompt-too-long summarizer failures still fail open without retry loop.
- [ ] Successful retry produces normal live compact output.
- [ ] Exhausted retries fail open and can increment circuit breaker count.
- [ ] Runtime pressure contract updated.
- [ ] Focused tests, ruff, and targeted mypy pass.

## Source Evidence

- `/root/claude-code-haha/src/services/compact/compact.ts`
- `/root/claude-code-haha/src/services/compact/autoCompact.ts`
- Source PRD: `.trellis/tasks/04-16-cc-style-autocompact-hardening/prd.md`

## Out of Scope

- No structured compaction result yet.
- No post-compact restoration contributions.
- No PreCompact/PostCompact hooks.
- No provider-specific cache sharing.

## Status

Checkpoint complete.

State: checkpoint

Verdict: APPROVE

Implemented:

- Added settings-backed `auto_compact_ptl_retry_limit`.
- Added bounded prompt-too-long retry inside proactive AutoCompact summary
  generation.
- Dropped the oldest summary-source message group per retry while preserving the
  original model-facing messages for final live compact projection.
- Kept non prompt-too-long summarizer failures on the existing fail-open path
  without retry.
- Exhausted PTL retries fail open and can increment the circuit breaker count.
- Updated runtime pressure contracts.

Verification:

- `pytest -q tests/test_runtime_pressure.py` -> 35 passed.
- `pytest -q tests/test_app.py` -> 9 passed.
- `ruff check src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/compact/__init__.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py tests/test_runtime_pressure.py tests/test_app.py` -> passed.
- `mypy src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py` -> passed.

Alignment:

- source files inspected:
  - `/root/claude-code-haha/src/services/compact/compact.ts`
  - `/root/claude-code-haha/src/services/compact/autoCompact.ts`
- aligned:
  - compact request prompt-too-long retry
  - bounded retry count
  - fail-open on exhaustion
- deferred:
  - richer API-round grouping
  - structured compaction result
  - hooks/restoration
- do-not-copy:
  - UI progress events
  - provider cache-sharing implementation

Architecture:

- primitive used: existing compact summarizer seam and middleware fail-open path.
- why no heavier abstraction: this stage only changes the summary source retry
  loop, not the runtime projection shape.

Boundary findings:

- Reactive compact retry remains unchanged.
- Raw transcript remains untouched.
- Circuit breaker integration works through existing AutoCompact status result.

Decision: continue

Reason:

- The sub-stage is complete and verified.
- Parent plan next stage remains valid: structured result can now consolidate
  AutoCompact output metadata and ordering.
