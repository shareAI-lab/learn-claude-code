# pre post compact hooks

## Goal

Add deterministic local `PreCompact` / `PostCompact` hook contribution seams around live AutoCompact without allowing hooks to call tools or mutate transcript records.

## Requirements

- Add `PreCompact` and `PostCompact` hook event names.
- Use existing `LocalHookRegistry` and `additional_context` only.
- `PreCompact` context flows into compact summarizer assist text.
- `PostCompact` context flows into structured restoration messages.
- Blank hook output is ignored.
- Hook context is bounded before becoming model-visible.

## Acceptance Criteria

- [x] PreCompact contribution can add compact instructions.
- [x] PostCompact contribution can add bounded restoration context.
- [x] invalid/blank hook output is ignored through existing hook result schema and local filtering.
- [x] hook output is represented through structured compaction result restoration.
- [x] runtime pressure contract is updated.
- [x] focused tests, ruff, and targeted mypy pass.

## Verification

- `pytest -q tests/test_runtime_pressure.py tests/test_hooks.py` -> 46 passed.
- `pytest -q tests/test_app.py` -> 9 passed.
- `ruff check src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/compact/__init__.py src/coding_deepgent/hooks/events.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py tests/test_runtime_pressure.py tests/test_app.py tests/test_hooks.py` -> passed.
- `mypy src/coding_deepgent/compact/runtime_pressure.py src/coding_deepgent/hooks/events.py src/coding_deepgent/sessions/evidence_events.py src/coding_deepgent/settings.py src/coding_deepgent/containers/app.py` -> passed.

## Checkpoint

State: checkpoint

Verdict: APPROVE

Decision: continue

Reason:

- Stage 2 AutoCompact reliability backbone is now complete through the planned hook seam.
- The parent plan next stage remains valid: Collapse Store And Projection.
