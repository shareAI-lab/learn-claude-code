# Stage 16A: Load-Time Compacted History View

## Goal

Add a load-time virtual compacted history view to `LoadedSession` so resume and future recovery paths can choose between raw transcript history and a compact-aware view without rewriting transcript files.

## Concrete Benefit

* Context-efficiency: compact-aware callers no longer need to reconstruct compacted history ad hoc.
* Recoverability: raw history and compacted history coexist in one loaded session object.
* Safety: transcript stays append-only; the compacted view is derived at load time only.

## Requirements

* Extend `LoadedSession` with `compacted_history`.
* `history` remains raw/full message history.
* `compacted_history` is derived from latest compact record when valid.
* If there is no valid compact-derived view, `compacted_history` falls back to the raw history.
* `cli_service.selected_continuation_history()` should use `loaded.compacted_history`.
* Add focused tests for load-time compacted history derivation.

## Acceptance Criteria

* [ ] `LoadedSession.compacted_history` exists.
* [ ] Sessions without compact records have `compacted_history == history`.
* [ ] Sessions with compact records get a compact boundary + compact summary + preserved tail as `compacted_history`.
* [ ] Invalid/out-of-range compact record counts fall back safely to raw history.
* [ ] `selected_continuation_history()` uses the loaded compacted view instead of rebuilding it inline.
* [ ] Focused tests, ruff, and mypy pass.

## Out of Scope

* transcript pruning/deletion
* auto-compact
* prompt-too-long retry
* changing compact record schema
* changing recovery brief display

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve recoverability, context-efficiency, and maintainability.

The local runtime effect is: compact-aware loading semantics become an explicit part of session load, not just a resume-time reconstruction trick.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Boundary-aware transcript loading | `/root/claude-code-haha/src/utils/sessionStorage.ts` treats compact boundary as transcript loading semantics | local load path should expose a compact-aware history view | `LoadedSession.compacted_history` | partial | Implement now |
| Raw transcript preservation | cc-haha still preserves metadata and reconstructs state around boundaries | local raw transcript should remain intact | keep `history` raw | align | Preserve now |
| Destructive pruning/relinking | cc-haha can prune/relink around latest compact boundary | advanced transcript semantics | none now | defer | Out of scope |

## LangChain Boundary

Use:

* existing `LoadedSession`
* existing compact artifact helper
* append-only compact records

Avoid:

* `SummarizationMiddleware`
* transcript rewrite
* state replacement

## Technical Approach

* Extend `LoadedSession` in `sessions/records.py`.
* Derive `compacted_history` in `JsonlSessionStore.load_session()`.
* Make `cli_service.selected_continuation_history()` use `loaded.compacted_history`.
* Add/extend tests in `tests/test_sessions.py` and `tests/test_cli.py`.

## Checkpoint: Stage 16A

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Extended `LoadedSession` with `compacted_history`.
- `JsonlSessionStore.load_session()` now derives a load-time virtual compacted history view from the latest compact record when valid.
- `LoadedSession.history` remains the raw/full transcript view.
- `LoadedSession.compacted_history` falls back to raw history when there is no compact record or the compact-derived tail is invalid/empty.
- `cli_service.selected_continuation_history()` now consumes the loaded compacted view instead of rebuilding compact semantics ad hoc.
- Updated backend code-spec with `compacted_history` contracts and validation cases.

Verification:
- `pytest -q tests/test_sessions.py tests/test_cli.py`
- `pytest -q tests/test_context_payloads.py tests/test_message_projection.py tests/test_compact_artifacts.py tests/test_compact_summarizer.py tests/test_compact_budget.py tests/test_sessions.py tests/test_cli.py tests/test_memory.py tests/test_memory_integration.py tests/test_memory_context.py tests/test_app.py`
- `ruff check src/coding_deepgent/sessions/records.py src/coding_deepgent/sessions/store_jsonl.py src/coding_deepgent/cli_service.py tests/test_sessions.py tests/test_cli.py`
- `mypy src/coding_deepgent/sessions/records.py src/coding_deepgent/sessions/store_jsonl.py src/coding_deepgent/cli_service.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/utils/sessionStorage.ts`
  - `/root/claude-code-haha/src/services/compact/compact.ts`
- Aligned:
  - compact boundary semantics are now part of load-time session interpretation, not only runtime continuation selection.
  - raw transcript and compact-aware view coexist.
- Deferred:
  - transcript pruning/relinking
  - physical deletion
  - auto/reactive compact

LangChain architecture:
- Primitive used:
  - append-only JSONL session store
  - load-time derived view
  - normal message dictionaries for continuation
- Why no heavier abstraction:
  - 16A formalizes a read/view model only; it does not rewrite transcript semantics on disk.

Boundary findings:
- New issue handled:
  - compact-aware continuation logic was previously duplicated in resume selection code; now the compacted history is part of the loaded session contract.
- Residual risk:
  - latest compact record is still treated as the authoritative compact boundary. Multi-boundary semantics remain intentionally simple.
- Impact on next stage:
  - Stage 16 can continue only by choosing whether to enrich virtual pruning semantics further or stop before destructive pruning.

Decision:
- continue

Terminal note:
- Stage 16A completes the core virtual-pruning view layer. No further Stage 16 sub-stage is started automatically because deeper work now needs an explicit choice about how far virtual pruning should go before destructive semantics are considered.

Reason:
- Tests, ruff, and mypy passed.
- Scope stayed append-only and non-destructive.
- No transcript deletion, transcript rewrite, auto-compact, prompt-too-long retry, or `SummarizationMiddleware` was introduced.
