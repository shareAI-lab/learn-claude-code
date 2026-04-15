# Stage 30B: Session Memory Threshold Local Updates

## Goal

Add threshold-triggered local `session_memory` updates on top of the Stage 30A contribution seams, without adding background extraction, implicit LLM calls on plain resume, mailbox, coordinator, or plugin runtime registration.

## Concrete Benefit

* Cross-session continuity: generated compact summaries can refresh the session-memory artifact when the existing artifact is missing or stale enough.
* Modularity: update behavior should live behind module-owned contribution providers rather than central `session_memory` wiring.
* Safety: updates happen only inside an already explicit generated compact-summary path, avoiding surprise model calls.

## Scope Decision

This stage implements a narrow form of "threshold-triggered local updates":

* It does not auto-run summarization on plain `sessions resume --prompt`.
* It does not add a background/session-memory extractor.
* It piggybacks on explicit `--generate-compact-summary`, because that path already intentionally invokes the summarizer.
* If the module-owned threshold policy says the artifact is missing or stale enough by message, estimated-token, or tool-call pressure, the generated compact summary is saved back into `loaded.state["session_memory"]`.

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve cross-session continuity and context-efficiency. The local runtime effect is: session memory can refresh at a deterministic boundary after generated compaction, without copying cc-haha's background post-sampling extractor.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Threshold policy | `SessionMemory/sessionMemoryUtils.ts` tracks initialization/update thresholds and extraction state | avoid refreshing session memory on every run | message-count threshold policy | partial | Align principle, not token/tool-call breadth |
| Explicit/manual extraction | `sessionMemory.ts::manuallyExtractSessionMemory()` bypasses thresholds for explicit command paths | explicit user action can refresh session memory without background scheduling | generated compact summary path can refresh state | partial | Align explicit local update boundary |
| Background extraction | post-sampling hook + forked agent extraction | richer future automation | none now | defer | Do not add in 30B |
| Compaction consumption | `sessionMemoryCompact.ts` waits/loads session memory for compact | compact can benefit from current session memory | reuse Stage 30A compact assist contribution | align | Keep deterministic |

### Source files inspected

* `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
* `/root/claude-code-haha/src/services/SessionMemory/sessionMemoryUtils.ts`
* `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`

## LangChain-Native Boundary

Surface:
* state and compact-summary service code

Primary boundary:
* product code under `coding_deepgent`, with no new LangChain middleware or graph runtime

Smallest viable change:
* add a compact-summary update contribution type
* let `session_memory` own its refresh threshold and update behavior
* have `cli_service.generated_compacted_continuation_history()` call generic update contributions after summary generation

## Requirements

* Add a generic compact-summary update contribution seam.
* Add a `session_memory` provider that decides whether to refresh from a generated compact summary.
* Refresh when:
  * no valid artifact exists, or
  * `current_message_count - artifact.message_count >= threshold`, or
  * `current_estimated_token_count - artifact.token_count >= threshold`, or
  * `current_tool_call_count - artifact.tool_call_count >= threshold`
* Do not refresh when the artifact is still current enough.
* Use the generated compact summary as the refreshed artifact content.
* Preserve existing current/stale recovery and compact assist behavior.
* Keep explicit `--session-memory` behavior unchanged.

## Acceptance Criteria

* [ ] Missing session-memory artifact refreshes from generated compact summary.
* [ ] Stale-enough session-memory artifact refreshes from generated compact summary.
* [ ] Current/recent session-memory artifact does not refresh.
* [ ] Refresh behavior is owned by `session_memory` provider code.
* [ ] `cli_service` consumes a generic compact-summary update contribution, not `session_memory` directly.
* [ ] Focused tests, targeted ruff, and targeted mypy pass.

## Out of Scope

* plain resume auto-summarization
* new CLI flags
* token/tool-call thresholds
* background session-memory extraction
* forked child-agent extraction
* plugin/dynamic contribution registration
* mailbox/coordinator lifecycle

## Technical Approach

### Sub-stage 1: Compact Summary Update Contribution

* Extend `sessions.contributions` with a `CompactSummaryUpdateContribution`.
* Add helper to apply update contributions after a generated compact summary.
* Add generic helper tests.

### Sub-stage 2: Session Memory Threshold Provider

* Add `session_memory` update-decision helpers and local pressure metrics.
* Add provider that refreshes state from generated compact summaries when threshold says due.
* Register provider in static contribution registry.
* Wire `cli_service.generated_compacted_continuation_history()` to the generic helper.

### Sub-stage 3: Contracts And Verification

* Update runtime/compaction contract docs.
* Run focused tests and targeted lint/typecheck.
* Record terminal checkpoint.

## Test Plan

* `pytest -q coding-deepgent/tests/test_session_contributions.py`
* `pytest -q coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_compact_summarizer.py`
* targeted `ruff check`
* targeted `mypy`

## Definition of Done

* Focused tests pass.
* Targeted ruff and mypy pass.
* Stage checkpoint records cc-haha alignment and deferred background/session-memory behavior.

## Checkpoint: Sub-stage 1 Compact Summary Update Contribution

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added `CompactSummaryUpdateContribution`.
- Added `apply_compact_summary_update_contributions()` helper.
- Added focused tests proving update contributions report which providers updated state.

Verification:
- `pytest -q coding-deepgent/tests/test_session_contributions.py`
- `ruff check coding-deepgent/src/coding_deepgent/sessions/contributions.py coding-deepgent/tests/test_session_contributions.py`
- `mypy coding-deepgent/src/coding_deepgent/sessions/contributions.py coding-deepgent/tests/test_session_contributions.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/utils/hooks.ts`
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
- Aligned:
  - introduced a lifecycle-style contribution point after generated compaction
- Deferred:
  - full hook runtime
  - background extraction
- Do-not-copy:
  - pre/post compact shell hook breadth

LangChain architecture:
- Primitive used:
  - pure dataclass descriptor and helper function
- Why no heavier abstraction:
  - no middleware or graph node is needed for a deterministic post-summary state update

Boundary findings:
- New issue:
  - no blocker; session_memory still needs a provider
- Impact on next stage:
  - sub-stage 2 remains valid

Decision:
- continue

Reason:
- The update seam is small, tested, and behavior-neutral.

## Checkpoint: Sub-stage 2 Session Memory Threshold Provider

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added `session_memory` refresh policy based on missing artifact, message-count delta, estimated-token delta, or tool-call delta.
- Added local `session_memory_metrics()` for deterministic message/token/tool-call pressure calculation.
- Added `session_memory` compact-summary update provider.
- Registered the provider in the static contribution registry.
- Wired generated compact summary flow through the generic update contribution helper.
- Added regressions for missing, stale-enough, token pressure, tool-call pressure, and recent artifacts.

Verification:
- `pytest -q coding-deepgent/tests/test_session_contributions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_compact_summarizer.py`
- `ruff check ...` on changed files
- `mypy ...` on changed files

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemoryUtils.ts`
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
- Aligned:
  - local update policy now has a threshold instead of refreshing every time
  - local threshold policy includes message, estimated-token, and tool-call pressure
  - explicit/generated compact path can refresh session memory without background extraction
- Deferred:
  - provider-accurate token accounting
  - post-sampling hook
  - forked extraction agent
- Do-not-copy:
  - remote config and extraction lifecycle

LangChain architecture:
- Primitive used:
  - module-owned provider plus existing service flow
- Why no heavier abstraction:
  - generated compact summary already owns the summarizer call; no extra middleware or graph node is needed

Boundary findings:
- New issue:
  - token counts are deterministic estimates from local message text, not provider tokenizer values
- Impact on next stage:
  - later provider-accurate token accounting can replace the metric internals without changing central flow

Decision:
- continue

Reason:
- The feature behavior is implemented behind contribution seams and passed focused validation. Remaining work is docs/final validation.

## Checkpoint: Sub-stage 3 Contracts And Terminal Validation

State:
- terminal

Verdict:
- APPROVE

Implemented:
- Updated runtime/compaction contract docs for `CompactSummaryUpdateContribution`.
- Documented the exact local-update boundary:
  - only `--generate-compact-summary` can refresh `session_memory`
  - plain resume does not trigger implicit summarization
  - missing/stale-enough artifacts refresh from generated summary based on message, estimated-token, or tool-call pressure
  - current/recent artifacts do not refresh
- Ran focused tests, targeted lint, and targeted typecheck.

Verification:
- `pytest -q coding-deepgent/tests/test_session_contributions.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_compact_summarizer.py`
- `ruff check ...` on changed source/test files
- `mypy ...` on changed source/test files

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemoryUtils.ts`
  - `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
- Aligned:
  - threshold-gated session-memory updates now exist in local form
  - local threshold policy includes message, estimated-token, and tool-call pressure
  - compaction path can refresh continuity state at an explicit boundary
- Deferred:
  - provider-accurate token accounting
  - post-sampling hook
  - forked extraction agent
  - automatic background update lifecycle
- Do-not-copy:
  - remote config and background extraction state machine

LangChain architecture:
- Primitive used:
  - contribution provider and existing generated compact summary service
- Why no heavier abstraction:
  - local updates can piggyback on the already-explicit summarizer call; no extra model/middleware/runtime layer is needed

Boundary findings:
- New issue:
  - token counts are deterministic estimates from local message text, not provider tokenizer values
- Impact on next stage:
  - next stage can either improve token accuracy with provider metrics or move to another module now that contribution seams exist

Decision:
- terminal

Reason:
- Stage 30B met scope without adding hidden model calls or background runtime.
