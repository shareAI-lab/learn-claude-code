# Stage 16C: Virtual Pruning View Metadata

## Goal

Expose why `LoadedSession.compacted_history` was selected, so recovery/debug/test code can distinguish raw fallback from a compact-derived view.

## Concrete Benefit

* Observability: compact-aware session loading can explain which compact record drove the view.
* Testability: future invariants can assert selection reason instead of inferring it from message content.
* Maintainability: later recovery display or diagnostics can use a stable source object.

## Requirements

* Add a compacted-history source object to `LoadedSession`.
* Source must identify:
  - raw fallback vs compact-derived view
  - compact index when compact-derived
  - reason string
* Preserve existing `history` and `compacted_history` behavior.
* Add focused tests.

## Acceptance Criteria

* [ ] Sessions without compacts report raw/no_compacts.
* [ ] Sessions with invalid compacts report raw/no_valid_compact.
* [ ] Sessions using a compact view report compact/latest_valid_compact with compact index.
* [ ] Focused tests, ruff, and mypy pass.

## Out of Scope

* changing selected history behavior
* transcript pruning/deletion
* auto-compact
* prompt-too-long retry

## Technical Approach

* Add `CompactedHistorySource` dataclass in `sessions/records.py`.
* Change `JsonlSessionStore._build_compacted_history()` to return view + source.
* Populate `LoadedSession.compacted_history_source`.
* Extend `tests/test_sessions.py`.

## Checkpoint: Stage 16C

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added `CompactedHistorySource`.
- Added `LoadedSession.compacted_history_source`.
- `JsonlSessionStore._build_compacted_history()` now returns both the compacted view and the source metadata.
- Source metadata distinguishes:
  - `raw/no_compacts`
  - `raw/no_valid_compact`
  - `compact/latest_valid_compact/<compact_index>`
- Updated backend runtime context/compaction spec with the source contract.

Verification:
- `pytest -q tests/test_sessions.py tests/test_cli.py`
- `pytest -q tests/test_context_payloads.py tests/test_message_projection.py tests/test_compact_artifacts.py tests/test_compact_summarizer.py tests/test_compact_budget.py tests/test_sessions.py tests/test_cli.py tests/test_memory.py tests/test_memory_integration.py tests/test_memory_context.py tests/test_app.py`
- `ruff check src/coding_deepgent/sessions/records.py src/coding_deepgent/sessions/store_jsonl.py src/coding_deepgent/sessions/__init__.py tests/test_sessions.py`
- `mypy src/coding_deepgent/sessions/records.py src/coding_deepgent/sessions/store_jsonl.py src/coding_deepgent/sessions/__init__.py`

cc-haha alignment:
- Source-backed intent came from compact-boundary-aware loader semantics in `/root/claude-code-haha/src/utils/sessionStorage.ts`.
- Aligned:
  - local loader can explain which compact boundary/view is active.
- Deferred:
  - full parent-chain relinking
  - physical transcript pruning

LangChain architecture:
- Primitive used:
  - explicit dataclass metadata on loaded session state
  - no graph state replacement or middleware change

Boundary findings:
- New issue handled:
  - compacted history selection was previously observable only by inspecting message content; it now has explicit metadata.
- Residual risk:
  - source metadata is still count/index based, not a full compact lineage graph.

Decision:
- continue

Terminal note:
- Stage 16 virtual pruning is complete for the current non-destructive scope. Further work should either switch to another highlight family or explicitly open a new destructive/pruning semantics design.

Reason:
- Tests, ruff, and mypy passed.
- No transcript deletion, rewrite, auto-compact, prompt-too-long retry, or `SummarizationMiddleware` was introduced.
