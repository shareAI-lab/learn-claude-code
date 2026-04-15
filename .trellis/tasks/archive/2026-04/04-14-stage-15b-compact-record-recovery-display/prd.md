# Stage 15B: Compact Record Recovery Display

## Goal

Expose the latest compact transcript records in recovery brief rendering and resume display, without changing continuation selection semantics.

## Concrete Benefit

* Recoverability: users can see that a session has already been compacted and what the latest compact summary says.
* Auditability: compact transcript records become visible product behavior rather than hidden JSONL metadata.
* Continuity: later stages can use the same compact summary display surface without yet changing resume selection.

## Requirements

* Extend recovery brief to include recent compact summaries.
* Keep compact display bounded.
* Do not add compact summaries to `LoadedSession.history`.
* Do not change `continuation_history()` or `compacted_continuation_history()` semantics in 15B.
* Update resume context message output to reflect the enhanced recovery brief.
* Add focused session/CLI tests.

## Acceptance Criteria

* [ ] `build_recovery_brief()` includes recent compact records in a separate field.
* [ ] `render_recovery_brief()` renders a compact section.
* [ ] `sessions resume <id>` without `--prompt` shows recent compact summary when available.
* [ ] resume-with-prompt still uses the same history semantics as before.
* [ ] Focused tests, ruff, and mypy pass.

## Out of Scope

* using compact summary instead of history for continuation
* transcript pruning/deletion
* auto-compact
* prompt-too-long retry
* changing message index behavior

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve recoverability, auditability, and long-session continuity.

The local runtime effect is: compact metadata becomes user-visible during resume/recovery, similar to how cc-haha keeps compact/session metadata recoverable around transcript boundaries.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Pre/post compact metadata continuity | `/root/claude-code-haha/src/utils/sessionStorage.ts` preserves metadata around compact boundaries so resume paths can still recover state | local resume display should expose compact information, not just raw chat/evidence | recovery brief compact section | partial | Implement now |
| Compact boundary visibility | `/root/claude-code-haha/src/services/compact/compact.ts` emits boundary + summary before post-compact continuation | local operator can inspect latest compact summary at resume time | render latest compact summaries in recovery brief | partial | Implement now |
| Continuation semantics | cc-haha later uses compact-boundary-aware loading logic | local continuation can evolve later | none now | defer | 15C decides continuation selection |

## LangChain Boundary

Use:

* existing session JSONL durability
* existing recovery brief builder/render path
* append-only compact records from 15A

Avoid:

* `SummarizationMiddleware`
* `RemoveMessage`
* transcript pruning
* changing runtime message history in this sub-stage

## Technical Approach

* Extend `sessions.resume.RecoveryBrief` with compact summaries.
* Render a new `Recent compacts:` section.
* Update tests in `tests/test_sessions.py` and `tests/test_cli.py`.

## Checkpoint: Stage 15B

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Extended `RecoveryBrief` with `recent_compacts`.
- `build_recovery_brief()` now includes bounded recent compact records.
- `render_recovery_brief()` now renders a `Recent compacts:` section.
- `sessions resume <id>` without `--prompt` now shows recent compact summaries when present.
- Resume-with-prompt semantics are unchanged except that the recovery brief now includes the compact section.

Verification:
- `pytest -q tests/test_sessions.py tests/test_cli.py`
- `ruff check src/coding_deepgent/sessions/resume.py tests/test_sessions.py tests/test_cli.py`
- `mypy src/coding_deepgent/sessions/resume.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/utils/sessionStorage.ts`
  - `/root/claude-code-haha/src/services/compact/compact.ts`
- Aligned:
  - compact/session metadata is now visible during recovery display rather than hidden in the transcript only.
- Deferred:
  - compact-boundary-aware continuation selection
  - transcript pruning/relinking

LangChain architecture:
- Primitive used:
  - existing recovery brief builder/render path
  - no runtime message-history mutation in this sub-stage
- Why no heavier abstraction:
  - 15B is display-only hardening; selection semantics belong to 15C.

Boundary findings:
- New issue handled:
  - recovery display previously hid compact transcript state entirely.
- Residual risk:
  - compact summaries are visible but not yet used to select a reduced continuation path.
- Impact on next stage:
  - 15C can now make continuation selection decisions with an already user-visible compact record surface.

Decision:
- continue

Reason:
- Tests, ruff, and mypy passed.
- Scope stayed display-only and non-destructive.
- 15C remains valid and does not require pruning or auto-compact.
