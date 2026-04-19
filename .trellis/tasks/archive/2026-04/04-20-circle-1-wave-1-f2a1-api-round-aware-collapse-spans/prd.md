# Circle 1 Wave 1 F2a1 API-Round-Aware Collapse Spans

## Goal

Refine local collapse span selection so continuity-preserving units survive
long-task collapse/resume cycles better than the current coarse prefix model.

## Acceptance Targets

* Collapse coverage is chosen using a unit that better preserves
  assistant/tool-result structure.
* The resulting continuity behavior is more compatible with long same-day coding
  tasks than the current prefix-only collapse coverage.
* The slice remains bounded and directly testable.

## Planned Features

* Define a local grouping primitive for continuity-preserving collapse spans.
* Replace or refine prefix-only covered-message derivation for persisted
  collapse records.
* Add focused tests for runtime pressure and collapse replay continuity.

## Planned Extensions

* richer collapse subsystem parity
* stronger session-memory runtime
* broader long-task continuity work

## Decision (ADR-lite)

**Context**: The current local collapse path persists replayable collapse
records, but the preserved tail and covered span were still derived from a pure
message-count suffix/prefix model. Public `cc-haha` evidence points toward
assistant API-round boundaries as the safer continuity unit.

**Decision**: For this slice, refine collapse tail selection by snapping the
preserved tail backward to the nearest recent assistant-round boundary when the
tail would otherwise begin on a non-assistant message.

**Consequences**:

* local collapse becomes less coarse without requiring a full hidden
  `contextCollapse` subsystem clone
* long-task continuity should improve when the recent tail would otherwise cut
  through an assistant-led work unit
* deeper group/commit-log parity remains future work

## Implementation Summary

* `runtime_pressure.py` now computes collapse keep-start through a dedicated
  helper that first preserves tool-call/tool-result pairing, then snaps the
  preserved tail backward to the nearest assistant-round boundary when
  applicable.
* session-memory continuity handling was tightened in the same pass:
  - freshness/status now considers token and tool-call pressure when metrics
    exist
  - compact/runtime assist remains conservative: if `message_count` already
    lags, the session-memory artifact is not injected as a compact assist
* focused runtime-pressure tests cover:
  - preserving a recent assistant round in the live collapse tail
  - persisting collapse coverage that stops before the preserved assistant round
* focused session-memory tests cover:
  - stale status when token pressure crosses threshold
  - conservative assist behavior for stale memory artifacts
* runtime-pressure contract docs now record that preserved-tail selection may
  snap backward to a recent assistant-round boundary.

## Verification

* `pytest -q coding-deepgent/tests/compact/test_runtime_pressure.py -q`
* `pytest -q coding-deepgent/tests/sessions/test_session_memory_middleware.py coding-deepgent/tests/sessions/test_session_contributions.py coding-deepgent/tests/sessions/test_sessions.py -q`
* `pytest -q coding-deepgent/tests/compact/test_runtime_pressure.py coding-deepgent/tests/sessions/test_session_memory_middleware.py coding-deepgent/tests/sessions/test_session_contributions.py coding-deepgent/tests/sessions/test_sessions.py coding-deepgent/tests/cli/test_cli.py -q`
* `pytest -q coding-deepgent/tests/sessions/test_sessions.py coding-deepgent/tests/cli/test_cli.py -q`
* `ruff check coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/tests/compact/test_runtime_pressure.py .trellis/spec/backend/runtime-pressure-contracts.md`
* `python3 -m mypy coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/tests/compact/test_runtime_pressure.py`
* `python3 -m mypy coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py coding-deepgent/src/coding_deepgent/cli_service.py`
* `ruff check coding-deepgent/src/coding_deepgent/sessions/session_memory.py coding-deepgent/src/coding_deepgent/sessions/session_memory_middleware.py coding-deepgent/tests/sessions/test_session_memory_middleware.py coding-deepgent/tests/sessions/test_session_contributions.py coding-deepgent/tests/sessions/test_sessions.py`
* `python3 -m mypy coding-deepgent/src/coding_deepgent/sessions/session_memory.py coding-deepgent/src/coding_deepgent/sessions/session_memory_middleware.py coding-deepgent/tests/sessions/test_session_memory_middleware.py coding-deepgent/tests/sessions/test_session_contributions.py coding-deepgent/tests/sessions/test_sessions.py`

## Technical Notes

* Parent task:
  `.trellis/tasks/04-20-circle-1-wave-1-f2a-collapse-session-continuity-v2/`
