# Stage 16B: Latest Valid Compact View Selection

## Goal

Harden virtual pruning so `load_session()` selects the latest valid compact-derived history view instead of blindly trusting only the final compact record.

## Concrete Benefit

* Reliability: a malformed or stale latest compact record no longer forces a fallback to full raw history if an earlier valid compact view exists.
* Recoverability: compact-aware load semantics become more robust across multiple compactions.
* Maintainability: compact view selection logic becomes explicit and testable.

## Requirements

* Scan compact records from newest to oldest.
* Use the newest compact record that yields a valid compacted history view.
* If none are valid, fall back to raw history.
* Preserve raw `history` unchanged.
* Preserve append-only transcript behavior.
* Add focused tests for multiple compact records and invalid-latest fallback.

## Acceptance Criteria

* [x] Latest valid compact record wins.
* [x] Invalid latest compact record falls back to the most recent earlier valid compact record.
* [x] No valid compact record still falls back to raw history.
* [x] Focused tests, ruff, and mypy pass.

## Out of Scope

* transcript pruning/deletion
* transcript relinking
* auto-compact
* prompt-too-long retry

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve recoverability and long-session continuity.

The local runtime effect is: compact-aware load semantics are resilient to stale or malformed later compact records, closer to cc-haha's boundary-aware transcript interpretation.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Boundary-aware load semantics | `sessionStorage.ts` treats compact boundaries as transcript interpretation, not a single fragile marker | local load path should tolerate more than one compact event | latest-valid compact selection | partial | Implement now |
| Full pruning/relinking | cc-haha prunes/relinks around latest live boundary | full semantic pruning | none now | defer | Out of scope |

## Technical Approach

* Refactor `JsonlSessionStore._build_compacted_history()` to iterate compact records from newest to oldest.
* Extract a helper that attempts to build a compacted view for one compact record.
* Add tests in `tests/test_sessions.py` and `tests/test_cli.py`.

## Checkpoint: Stage 16B

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Refactored compacted history derivation to scan compact records from newest to oldest.
- Added per-record compact view builder helper in `JsonlSessionStore`.
- `LoadedSession.compacted_history` now uses the latest valid compact record rather than blindly trusting only the final compact record.
- If the latest compact record is invalid but an earlier one is valid, the earlier valid compact record now drives the compacted history view.
- If no compact record yields a valid view, raw history is still preserved as the fallback.
- Added an explicit newest-valid-wins regression test for multiple valid compact records.

Verification:
- `pytest -q tests/test_sessions.py tests/test_cli.py`
- `pytest -q tests/test_context_payloads.py tests/test_message_projection.py tests/test_compact_artifacts.py tests/test_compact_summarizer.py tests/test_compact_budget.py tests/test_sessions.py tests/test_cli.py tests/test_memory.py tests/test_memory_integration.py tests/test_memory_context.py tests/test_app.py`
- `ruff check src/coding_deepgent/sessions/store_jsonl.py tests/test_sessions.py`
- `mypy src/coding_deepgent/sessions/store_jsonl.py`
- Latest local rerun:
  - `pytest -q tests/test_sessions.py`
  - `pytest -q tests/test_cli.py tests/test_context_payloads.py tests/test_message_projection.py tests/test_compact_artifacts.py tests/test_compact_summarizer.py tests/test_compact_budget.py tests/test_memory.py tests/test_memory_integration.py tests/test_memory_context.py tests/test_app.py`
  - `ruff check src/coding_deepgent/sessions/store_jsonl.py tests/test_sessions.py`
  - `mypy src/coding_deepgent/sessions/store_jsonl.py`

cc-haha alignment:
- Source-backed intent came from `sessionStorage.ts` compact-boundary-aware loading semantics.
- Aligned:
  - compact-aware loading is now more resilient across multiple compact events.
- Deferred:
  - transcript pruning/relinking
  - destructive compact semantics
  - auto/reactive compact

LangChain architecture:
- Primitive used:
  - load-time derived compacted view over append-only transcript records
- Why no heavier abstraction:
  - 16B only hardens virtual pruning selection; no transcript mutation or graph-level state replacement is needed.

Boundary findings:
- New issue handled:
  - a malformed latest compact record no longer forces a full fallback when an earlier valid compact view exists.
- Residual risk:
  - compact selection is still linear and based only on record ordering/count semantics, not a richer compact lineage graph.
- Impact on next stage:
  - virtual pruning is now strong enough for the current product slice; deeper work would need an explicit choice between richer lineage semantics and destructive pruning semantics.

Decision:
- continue

Terminal note:
- Stage 16 virtual pruning is complete for the current non-destructive scope. No further sub-stage starts automatically because the next work would materially change transcript semantics beyond the current approved boundary.

Reason:
- Tests, ruff, and mypy passed.
- Scope stayed virtual and append-only.
- No transcript deletion, rewrite, auto-compact, prompt-too-long retry, or `SummarizationMiddleware` was introduced.
