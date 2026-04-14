# Stage 13B: Manual Compact Entry Point

## Goal

Wire the Stage 13A compact artifact into an explicit manual continuation entry point for session resume, while keeping compaction non-destructive and user-controlled.

## Concrete Benefit

* Context-efficiency: a resumed session can continue from a compact summary and recent tail instead of replaying the full loaded history.
* Reliability: manual compact continuation still carries the Stage 12C recovery brief and preserves recent message invariants from 13A.
* Maintainability: CLI/service wiring proves the artifact boundary without adding auto-compact or session-store rewrite semantics.

## Requirements

* Add an explicit manual compact continuation path.
* Keep existing `sessions resume --prompt` behavior unchanged unless the user passes a compact summary option.
* Support:
  - user-provided compact summary text
  - bounded recent tail count
  - recovery brief context from Stage 12C
* Reject compact options when no continuation prompt is provided.
* Do not persist compacted history or delete transcript records in 13B.
* Add focused CLI/service tests.

## Acceptance Criteria

* [ ] `sessions resume --prompt ... --compact-summary ...` uses compacted continuation history.
* [ ] Recovery brief remains present in compacted continuation.
* [ ] Compact boundary + summary artifact appear before preserved recent messages.
* [ ] Existing non-compact resume behavior still passes.
* [ ] Compact options without `--prompt` fail clearly.
* [ ] Focused tests, ruff, and mypy pass.

## Definition of Done

* No auto-compact trigger is introduced.
* No LLM summarization call is introduced.
* No session transcript pruning or mutation is introduced.
* Stage 13A artifact helpers remain the compaction source of truth.

## Out of Scope

* automatic token thresholds
* prompt-too-long retry
* live summarizer model call
* session store compact records or delete semantics
* post-compact restoration attachments
* tool-result file persistence

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve context-efficiency, recoverability, and long-session continuity.

The local runtime effect is: manual resume can continue from a compacted history with explicit compact boundary, summary, recovery brief, and preserved recent messages.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Manual compact path | `/root/claude-code-haha/src/services/compact/compact.ts::compactConversation()` creates boundary/summary and returns post-compact messages | local manual compact has a concrete continuation entry point | `sessions resume --prompt --compact-summary` | partial | Wire explicit manual path without LLM summarizer |
| Post-compact ordering | `/root/claude-code-haha/src/services/compact/compact.ts::buildPostCompactMessages()` orders boundary, summary, kept messages, attachments, hooks | local continuation sees compact artifact before recent tail | reuse 13A artifact output | align | Implement now |
| Recovery / transcript | cc-haha keeps transcript and metadata available for continuation | local resume still carries recovery brief and does not delete transcript | prepend Stage 12C recovery brief | partial | Preserve current session store |
| Hooks/restoration | cc-haha executes pre/post compact hooks and restores context attachments | later full compact can restore files/tools/skills | none now | defer | Too wide for 13B |

## LangChain Boundary

Use:

* normal message history continuation through existing `agent_loop`
* existing CLI service seam
* deterministic compact artifact helper from 13A

Avoid:

* custom query runtime
* automatic `SummarizationMiddleware` before manual artifact behavior is validated
* persistence changes before compacted transcript semantics are designed

## Technical Approach

* Add `cli_service.compacted_continuation_history()`.
* Update `cli.py sessions resume` with:
  - `--compact-summary`
  - `--compact-keep-last`
* Reject compact options without `--prompt`.
* Update `tests/test_cli.py`.

## Test Plan

* CLI test for compacted resume history.
* CLI test for compact option validation.
* Existing resume tests remain unchanged.
* Focused compact/projection/app smoke tests.

## Checkpoint: Stage 13B

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added `cli_service.compacted_continuation_history()` to combine Stage 12C recovery brief with the Stage 13A compact artifact.
- Added `sessions resume --prompt ... --compact-summary ... --compact-keep-last N`.
- Preserved existing non-compact `sessions resume --prompt` behavior.
- Rejected `--compact-summary` when `--prompt` is absent.
- Added CLI coverage for compacted resume history and compact option validation.

Verification:
- `pytest -q tests/test_cli.py tests/test_compact_artifacts.py tests/test_message_projection.py tests/test_app.py`
- `pytest -q tests/test_context_payloads.py tests/test_message_projection.py tests/test_compact_artifacts.py tests/test_compact_budget.py tests/test_sessions.py tests/test_cli.py tests/test_memory.py tests/test_memory_integration.py tests/test_memory_context.py tests/test_app.py`
- `ruff check src/coding_deepgent/cli_service.py src/coding_deepgent/cli.py tests/test_cli.py`
- `mypy src/coding_deepgent/cli_service.py src/coding_deepgent/cli.py`

cc-haha alignment:
- Source-backed intent came from:
  - `/root/claude-code-haha/src/services/compact/compact.ts::compactConversation()`
  - `/root/claude-code-haha/src/services/compact/compact.ts::buildPostCompactMessages()`
  - `/root/claude-code-haha/src/services/compact/prompt.ts`
- Aligned:
  - manual compact continuation now has explicit compact summary + boundary + preserved tail.
  - resume recovery context remains in the continuation path.
- Deferred:
  - model-generated summary.
  - pre/post compact hooks.
  - transcript pruning.
  - auto/reactive compact.

LangChain architecture:
- Primitive used:
  - existing CLI service seam and normal LangChain message history continuation.
  - deterministic Stage 13A compact artifact helper.
- Why no heavier abstraction:
  - 13B only proves explicit manual wiring; automatic middleware and persistent state updates are later concerns.

Boundary findings:
- New issue handled:
  - compact options without a continuation prompt would otherwise be ambiguous, so the CLI rejects them.
- Residual risk:
  - summary text is still supplied by the user; no local summarizer seam exists yet.
- Impact on next stage:
  - 13C should add a summary generation seam/prompt contract, still avoiding auto-compact.

Decision:
- continue

Reason:
- Tests, ruff, and mypy passed.
- Scope stayed inside explicit manual compact entry point.
- The next sub-stage is still valid if constrained to summary generation seam/prompt contract, not auto-compact.
