# release validation and pr cleanup for approach a mvp

## Goal

Run a focused release-validation and PR-cleanup pass for the current
`coding-deepgent` Approach A MVP closeout so the branch state, tests, and
canonical Trellis docs are consistent before any new next-cycle implementation
work begins.

## Requirements

- Validate the current mainline against the canonical MVP closeout docs:
  - `.trellis/project-handoff.md`
  - `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
  - relevant backend contract specs under `.trellis/spec/backend/`
- Run focused product validation on the most relevant `coding-deepgent` test
  slices and static checks for touched/risky domains.
- Identify release/PR cleanup gaps:
  - failing checks
  - doc/status mismatches
  - obviously stale or conflicting task/plan/task-status artifacts
- Fix issues directly when the fix is scoped and low-risk.
- If a broader or riskier issue appears, document it clearly instead of
  reopening unrelated implementation work.
- Keep `Stage 30-36` reserve work deferred unless validation exposes a concrete
  MVP gap.

## Acceptance Criteria

- [x] Relevant specs and canonical roadmap docs are re-read and recorded in task context.
- [x] Focused validation is run against the current `coding-deepgent` surface.
- [x] Any discovered blockers are either fixed or documented with clear follow-up.
- [x] PR/release-facing cleanup items are reconciled with current Trellis canonical wording.
- [x] The task ends with a concise status summary of MVP readiness and remaining risks.

## Technical Notes

- Current branch: `codex/stage-12-14-context-compact-foundation`
- Current recommended direction from handoff:
  - release validation / PR cleanup for Approach A MVP
- Explicit non-goal:
  - do not silently restart new feature-stage implementation during this task

## Validation Results

- Canonical docs re-read:
  - `.trellis/project-handoff.md`
  - `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
  - `.trellis/spec/backend/quality-guidelines.md`
  - `.trellis/spec/backend/langchain-native-guidelines.md`
  - `.trellis/spec/backend/runtime-context-compaction-contracts.md`
  - `.trellis/spec/backend/task-workflow-contracts.md`
- PR metadata refreshed:
  - draft PR `#220`
  - head: `codex/stage-12-14-context-compact-foundation`
  - base: `main`
- Product validation passed:
  - `python3 -m pytest tests -q` -> `256 passed`
  - `python3 -m ruff check src tests` -> passed
  - `python3 -m mypy src` -> `Success: no issues found in 106 source files`
- Release-facing doc cleanup applied:
  - `coding-deepgent/README.md`
  - `coding-deepgent/PROJECT_PROGRESS.md`
  - change type: clarify that `stage-11` remains a product-local compatibility
    anchor while canonical live MVP status now lives in Trellis and is complete
    through `Stage 29`
- Contract regression after doc cleanup passed:
  - `python3 -m pytest tests/test_runtime_foundation_contract.py tests/test_contract.py tests/test_structure.py -q` -> `14 passed`

## Outcome Summary

- No product-code blocker was found in the current Approach A MVP closeout line.
- The local product test suite and static checks passed cleanly.
- The main release-facing ambiguity found in this pass was documentation wording:
  `README.md` and `PROJECT_PROGRESS.md` still exposed the legacy `stage-11`
  compatibility anchor without making the Trellis live-status boundary explicit
  enough.
- That ambiguity was reduced without changing the product-local stage marker or
  `project_status.json` contract.

## Remaining Risks

- `coding-deepgent/project_status.json` and the product-local `stage-11`
  compatibility anchor remain intentionally unchanged because current contract
  tests and settings surfaces depend on them.
- Canonical live progress should continue to be read from Trellis, not inferred
  from the product-local stage marker alone.
