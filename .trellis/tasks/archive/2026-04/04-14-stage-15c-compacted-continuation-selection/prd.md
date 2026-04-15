# Stage 15C: Compacted Continuation Selection

## Goal

When a session already contains compact transcript records, prefer a compacted continuation history for `sessions resume --prompt` instead of always replaying the full raw history, while keeping transcript storage append-only and non-destructive.

## Concrete Benefit

* Context-efficiency: resumed sessions stop replaying already-compacted full history when a latest compact summary is available.
* Continuity: resume uses the same compact summary + preserved tail semantics that earlier compact actions established.
* Safety: transcript remains intact; only continuation history selection changes.

## Requirements

* Add a compact-aware continuation selector for loaded sessions.
* Use the latest compact record when no explicit compact override is provided.
* Preserve:
  - recovery brief system message
  - compact summary from latest compact record
  - all real messages from the preserved tail start onward
* Keep explicit overrides higher priority:
  - manual `--compact-summary`
  - generated `--generate-compact-summary`
* Keep transcript append-only and non-destructive.
* Add focused CLI/service tests.

## Acceptance Criteria

* [ ] Resume-with-prompt defaults to latest compacted continuation when compact records exist.
* [ ] The selected tail includes all real messages from the compact preserved window onward, including later continuation messages.
* [ ] Sessions without compact records still use the existing recovery-brief + full-history path.
* [ ] Explicit compact CLI options still override default selection behavior.
* [ ] Focused tests, ruff, and mypy pass.

## Out of Scope

* transcript pruning/deletion
* auto-compact
* prompt-too-long retry
* changing compact record schema
* altering recovery brief rendering beyond what 15B added

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve long-session continuity, recoverability, and context-efficiency.

The local runtime effect is: once a session has a compact boundary/summary recorded, later resume continuation can start from that compact summary and preserved tail instead of replaying the full pre-compact transcript.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Compaction boundary-aware loading | `/root/claude-code-haha/src/utils/sessionStorage.ts` and portable loader treat compact boundaries as transcript semantics, not just display hints | local resume should respect compacted continuation state | compact-aware continuation history selector | partial | Implement selector now |
| Preserved tail semantics | `/root/claude-code-haha/src/services/compact/compact.ts` and `sessionMemoryCompact.ts` preserve a recent tail after summary | local resume should keep the preserved tail plus later messages | derive tail start from latest compact record | align | Implement now |
| Transcript pruning/relinking | cc-haha later prunes/relinks transcript chains around boundaries | full transcript rewrite semantics | none now | defer | Out of scope |

## LangChain Boundary

Use:

* existing `LoadedSession`
* compact artifact helper from Stage 13
* append-only compact records from 15A
* existing CLI service seam

Avoid:

* `SummarizationMiddleware`
* `RemoveMessage`
* transcript rewrite/prune logic
* provider-specific compact runtime

## Technical Approach

* Add `cli_service.selected_continuation_history()`.
* If `loaded.compacts` is non-empty, derive:
  - latest compact summary
  - preserved tail start = `original_message_count - kept_message_count`
  - compacted history using that tail window
* Wire `cli.py sessions_resume` default path to `selected_continuation_history()`.
* Update tests in `tests/test_cli.py`.

## Checkpoint: Stage 15C

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added `cli_service.selected_continuation_history()`.
- Resume-with-prompt now defaults to a compact-aware continuation path when `loaded.compacts` is non-empty and no explicit compact override is provided.
- The selected compact continuation uses:
  - the latest compact summary
  - preserved tail start = `original_message_count - kept_message_count`
  - all real messages from that tail onward, including post-compact continuation messages
- Explicit compact controls still win:
  - manual `--compact-summary`
  - generated `--generate-compact-summary`
- Sessions without compact records still use the recovery-brief + full-history continuation path.

Verification:
- `pytest -q tests/test_cli.py tests/test_sessions.py tests/test_compact_artifacts.py tests/test_compact_summarizer.py tests/test_message_projection.py`
- `pytest -q tests/test_context_payloads.py tests/test_message_projection.py tests/test_compact_artifacts.py tests/test_compact_summarizer.py tests/test_compact_budget.py tests/test_sessions.py tests/test_cli.py tests/test_memory.py tests/test_memory_integration.py tests/test_memory_context.py tests/test_app.py`
- `ruff check src/coding_deepgent/cli_service.py src/coding_deepgent/cli.py tests/test_cli.py`
- `mypy src/coding_deepgent/cli_service.py src/coding_deepgent/cli.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/utils/sessionStorage.ts`
  - `/root/claude-code-haha/src/services/compact/compact.ts`
  - `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
- Aligned:
  - resume continuation can now respect the latest compact boundary/summary instead of always replaying the full raw transcript.
  - preserved-tail semantics are applied non-destructively from recorded compact metadata.
- Deferred:
  - transcript pruning/relinking.
  - auto/reactive compact.
  - prompt-too-long retry.

LangChain architecture:
- Primitive used:
  - existing CLI service seam and normal message history continuation.
  - no `SummarizationMiddleware`, no `RemoveMessage`, and no transcript rewrite.
- Why no heavier abstraction:
  - 15C changes only continuation selection, not transcript storage or runtime lifecycle policy.

Boundary findings:
- New issue handled:
  - compact records were visible after 15B but unused for continuation selection; 15C closes that gap.
- Residual risk:
  - compact selection currently trusts the latest compact record as authoritative. More complex multi-compact / pruning semantics remain deferred.
- Impact on next stage:
  - any next step now moves into materially different behavior: transcript pruning/relinking, auto/reactive compact, or richer compact recovery semantics.

Decision:
- continue

Terminal note:
- Stage 15B and 15C complete the current non-destructive compact persistence semantics slice. No further sub-stage should start automatically without an explicit choice between pruning semantics, reactive/auto compact, or richer recovery behavior.

Reason:
- Tests, ruff, and mypy passed.
- Scope stayed non-destructive.
- Further work would widen the product contract beyond the current approved Stage 15 family.
