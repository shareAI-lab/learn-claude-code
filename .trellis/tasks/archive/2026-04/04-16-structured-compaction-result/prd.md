# structured compaction result

## Goal

Introduce a local structured result for live compaction/collapse rendering so later restoration contributions and hooks can add bounded messages without duplicating ordering logic.

## Expected Effect

Live AutoCompact/Collapse should have one explicit object describing boundary, summary, restoration messages, preserved tail, trigger, and estimated token counts. Rendering order becomes testable and extensible.

## Requirements

- Add `LiveCompactionResult` or equivalent local dataclass.
- Include boundary message, summary message, restoration messages, preserved tail, trigger, and estimated pre/post token counts.
- Provide one render function/method that emits final model-facing messages in stable order.
- Use the structured result internally for live AutoCompact and live Collapse.
- Preserve current public helper return types where possible.
- Keep raw transcript unchanged.
- Keep current restoration-path behavior compatible.

## Acceptance Criteria

- [ ] AutoCompact uses structured result internally.
- [ ] Collapse uses structured result internally.
- [ ] Final message order is covered by focused tests.
- [ ] Runtime event metadata can use structured result metadata.
- [ ] Current live compact/collapse helper behavior remains compatible.
- [ ] Runtime pressure contract updated.
- [ ] Focused tests, ruff, and targeted mypy pass.

## Source Evidence

- `/root/claude-code-haha/src/services/compact/compact.ts`
- Source PRD: `.trellis/tasks/04-16-cc-style-autocompact-hardening/prd.md`

## Out of Scope

- No new restoration contribution providers in this sub-stage.
- No PreCompact/PostCompact hooks yet.
- No session schema migration.
- No provider cache sharing.

## Status

Checkpoint complete.

State: checkpoint

Verdict: APPROVE

Implemented:

- Added `LiveCompactionResult` with boundary, summary, restoration messages,
  preserved tail, trigger, restored-path count, and estimated token fields.
- Added `compact_live_messages_with_result(...)`.
- Added `collapse_live_messages_with_result(...)`.
- Kept `compact_live_messages_with_summary(...)` and
  `collapse_live_messages_with_summary(...)` as list-return compatibility
  wrappers.
- Added render-order tests for compact and collapse.
- Updated runtime pressure contracts.

Verification:

- `pytest -q tests/test_runtime_pressure.py` -> 37 passed.
- `pytest -q tests/test_app.py` -> 9 passed.
- `ruff check src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/compact/__init__.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py tests/test_runtime_pressure.py tests/test_app.py` -> passed.
- `mypy src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py` -> passed.

Alignment:

- source files inspected:
  - `/root/claude-code-haha/src/services/compact/compact.ts`
  - `/root/claude-code-haha/src/services/compact/autoCompact.ts`
- aligned:
  - structured result object for consistent post-compact message ordering
  - explicit metadata for restoration and token estimates
- deferred:
  - restoration contribution providers
  - PreCompact/PostCompact hooks
- do-not-copy:
  - cc UI progress lifecycle
  - provider cache-sharing details

Architecture:

- primitive used: local dataclass plus existing live projection helpers.
- why no heavier abstraction: this is a stable return object for one domain
  boundary, not a new runtime subsystem.

Boundary findings:

- Existing public helper behavior remains list-compatible.
- No raw transcript mutation introduced.

Decision: continue

Reason:

- The sub-stage is complete and verified.
- Parent plan next stage can now add restoration messages through the structured
  result boundary instead of editing render order ad hoc.
