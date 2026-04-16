# post compact restoration contributions

## Goal

Add bounded post-compact restoration context through the structured live compaction result so the model does not lose active short-term planning state after live AutoCompact.

## Scope Implemented In This Pass

This sub-stage implemented the lowest-risk restoration source: active TodoWrite state already present in runtime state.

Deferred until stable runtime-state sources exist:

- durable plan references
- verifier evidence summaries
- loaded skill refs
- subagent lineage

## Requirements

- Add bounded restoration messages through `LiveCompactionResult.restoration_messages`.
- Restore active todos only when `status in {"pending", "in_progress"}`.
- Do not include completed todos.
- Do not dump raw transcript or large payloads.
- Preserve existing persisted-output path restoration behavior.

## Acceptance Criteria

- [x] post-compact context includes active todos when present.
- [x] completed todos are excluded.
- [x] restoration message renders before preserved tail.
- [x] no raw transcript mutation is introduced.
- [x] runtime pressure contract is updated.
- [x] focused tests, ruff, and targeted mypy pass.

## Verification

- `pytest -q tests/test_runtime_pressure.py` -> 38 passed.
- `pytest -q tests/test_app.py` -> 9 passed.
- `ruff check src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/compact/__init__.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py tests/test_runtime_pressure.py tests/test_app.py` -> passed.
- `mypy src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py` -> passed.

## Checkpoint

State: checkpoint

Verdict: APPROVE

Decision: continue

Reason:

- The active-todo restoration slice is implemented and verified.
- The parent plan next sub-stage remains valid: hooks can now contribute through the structured result boundary.
