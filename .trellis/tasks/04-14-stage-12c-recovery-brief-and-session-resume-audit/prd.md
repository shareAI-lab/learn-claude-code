# Stage 12C: Recovery Brief and Session Resume Audit

## Goal

Audit and harden the current session resume path so resumed sessions expose enough execution context to continue useful work, including history, latest runtime state, and recent evidence through a recovery brief on the continuation path.

## What I already know

* This is Stage 12C of `Stage 12: Context and Recovery Hardening`.
* Current local session foundation is already useful:
  - `JsonlSessionStore`
  - message/state/evidence records
  - `LoadedSession`
  - `build_recovery_brief()` / `render_recovery_brief()`
  - CLI `sessions resume <id>` without `--prompt` already prints a recovery brief
  - CLI resume with `--prompt` loads history/state/session_id and continues
* Existing tests already prove important parts:
  - `tests/test_sessions.py` covers roundtrip, invalid records, evidence, fallback state, and resume state restore
  - `tests/test_cli.py` covers CLI resume with and without prompt
  - `tests/test_app.py` proves resumed sessions do not retrigger `SessionStart`
* Source-backed target design for H06 says:
  - session should be recoverable execution evidence, not just chat history
  - keep JSONL transcript + state snapshot + evidence
  - map session id to LangGraph `thread_id`
  - add a recovery brief target for continuation
* Explorer audit found the main current gap:
  - recovery brief/evidence is shown to the user on no-`--prompt` resume, but not fed into the resumed continuation path when `--prompt` is used

## Assumptions

* Stage 12C should remain a narrow audit/hardening stage, not a full session runtime redesign.
* The smallest valuable change is to make recovery brief context visible on resume-with-prompt, without inventing a larger session framework.
* Session transcript store, state snapshot semantics, and recovery brief formatting should remain deterministic.

## Open Questions

* None for the current 12C slice.

## Requirements

* Audit the current session/resume path against H06.
* Preserve current local session storage architecture:
  - JSONL transcript
  - state snapshots
  - evidence records
* Keep session id mapped to LangGraph `thread_id`.
* Make resumed continuation with `--prompt` include a recovery brief context, not only raw loaded history/state.
* Add focused tests for:
  - evidence ordering and limiting in recovery brief
  - runtime state overwrite semantics on resume
  - CLI resume with `--prompt` using a recovery brief in continuation history
  - resumed sessions still suppress `SessionStart`

## Acceptance Criteria

* [ ] Existing session/resume architecture is audited and documented by the PRD + tests.
* [ ] Recovery brief behavior is tested more explicitly.
* [ ] Resume-with-prompt includes recovery brief context in the continuation path.
* [ ] Resumed session state is still restored deterministically.
* [ ] Existing session/CLI/app tests still pass.

## Definition of Done

* Focused session and CLI tests are added/updated.
* No database persistence or full agent runtime resume is introduced.
* No context pressure/compact work is folded into this stage.

## Out of Scope

* full agent runtime resume parity
* task-level evidence store
* database persistence
* auto-compact / compaction
* memory quality policy
* coordinator/team runtime

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve recoverability, reliability, testability, and product parity.

The local runtime effect is: a resumed session can continue with not just chat history and state, but also a compact recovery brief carrying recent evidence, making continuation more useful without rebuilding a full cc-haha runtime resume platform.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Transcript + metadata resume | `/root/claude-code-haha/docs/must-read/02-agent-runtime.md` and `resumeAgent.ts` treat transcript/metadata as resume prerequisites | resumed work has enough state to continue usefully | keep JSONL + state snapshot + evidence | align | Preserve current seam |
| Recovery brief | H06 target calls for recent evidence visible as a recovery brief | continuation has concise execution context, not only raw history | inject rendered recovery brief into resume-with-prompt path | partial | Implement now |
| LangGraph thread binding | cc-haha and LangChain both rely on stable session identity | resumed conversation stays on the same thread boundary | preserve `thread_id = session_id` | align | Keep as-is |
| Full runtime resume breadth | cc-haha resume reconstructs richer runtime objects | avoid scope blow-up in 12C | none now | defer | Do not implement full runtime resume |

### Non-goals

* Do not rebuild cc-haha transcript/metadata runtime objects.
* Do not add database-backed session persistence.
* Do not mix memory/task stores into transcript storage.
* Do not add full task/subagent recovery.

### State boundary

* Session transcript is durable evidence.
* Session state snapshot restores short-term runtime state relevant to current product behavior.
* Recovery brief is a transient continuation aid, not durable state itself.

### Model-visible boundary

On `sessions resume --prompt ...`, the model should see:

* the resumed history
* the restored state
* a compact recovery brief that includes recent evidence and active todos

It should not see:

* internal storage metadata
* raw evidence JSON
* implementation-only session bookkeeping

### LangChain boundary

Use:

* existing `create_agent` runtime
* existing `thread_id` mapping
* normal message history continuation

Avoid:

* custom query runtime
* new graph nodes/checkpointers
* replacing the current session store seam

## Technical Approach

Recommended minimal design:

* Add a helper in `cli_service.py` to build continuation history from `LoadedSession` plus a rendered recovery brief.
* Update `cli.py` `sessions_resume --prompt` path to use that helper.
* Keep `sessions/resume.py` recovery-brief builders as the source of truth.
* Expand tests in:
  - `tests/test_sessions.py`
  - `tests/test_cli.py`
  - optionally `tests/test_app.py`

## Research Notes

### Current local gaps

* Recovery brief exists, but currently only the no-`--prompt` resume path shows it.
* Resume-with-prompt currently passes only `loaded.history`, `loaded.state`, and `session_id`.
* This means evidence and active-todo summary are not visible to the continuation path unless they happen to be reconstructible from raw history/state alone.

### Feasible approaches

**Approach A: Inject recovery brief into resume-with-prompt history** (Recommended)

How it works:

* Reuse existing `build_recovery_brief()` / `render_recovery_brief()`
* Add one helper for continuation history construction
* Prepend a small system message with the recovery brief to resumed history when `--prompt` is used

Pros:

* Smallest useful change
* Reuses current session primitives
* Improves resumed continuation immediately

Cons:

* Not full runtime resume parity

**Approach B: Audit-only, tests-only**

How it works:

* Add tests but do not change runtime behavior

Pros:

* Very low risk

Cons:

* Leaves the main useful gap unchanged

**Approach C: Full richer runtime resume**

How it works:

* Reconstruct more session/runtime objects beyond history/state/evidence

Pros:

* Closer to future parity

Cons:

* Too wide for 12C
* Pulls in task/subagent/session architecture prematurely

## Decision (ADR-lite)

**Context**: The current session foundation is already useful, but resume-with-prompt does not yet carry the compact recovery brief into the continuation path.

**Decision**: Use Approach A, inject recovery brief into resume-with-prompt history and strengthen resume/recovery tests.

**Consequences**:

* 12C stays narrow.
* The current session store seam remains intact.
* Continuation gets more useful execution context without introducing a new runtime.

## Checkpoint: Stage 12C

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added a model-visible resume context message in `coding-deepgent/src/coding_deepgent/sessions/resume.py` using the existing recovery brief builder/render path.
- Added `cli_service.continuation_history()` and updated `sessions resume --prompt` to pass recovery brief context, restored state, and the same session id into the continuation path.
- Updated session recording to keep transcript `message_index` counts based on persisted messages, excluding the synthetic resume context message.
- Strengthened tests for recovery brief evidence limiting/order, runtime state overwrite/deep-copy semantics, resume-with-prompt recovery brief injection, transcript persistence, and resumed `SessionStart` suppression.

Verification:
- `pytest -q tests/test_cli.py tests/test_sessions.py tests/test_app.py`
- `pytest -q tests/test_context_payloads.py tests/test_message_projection.py tests/test_sessions.py tests/test_cli.py tests/test_app.py`
- `ruff check src/coding_deepgent/sessions/resume.py src/coding_deepgent/cli_service.py src/coding_deepgent/cli.py src/coding_deepgent/sessions/service.py src/coding_deepgent/sessions/__init__.py tests/test_cli.py tests/test_sessions.py tests/test_app.py`
- `mypy src/coding_deepgent/sessions/resume.py src/coding_deepgent/cli_service.py src/coding_deepgent/cli.py src/coding_deepgent/sessions/service.py src/coding_deepgent/sessions/__init__.py`

cc-haha alignment:
- Source-backed premise came from the 12C PRD and earlier H06 mapping:
  - `/root/claude-code-haha/docs/must-read/02-agent-runtime.md`
  - `resumeAgent.ts`
- Aligned:
  - resumed sessions carry transcript, state snapshot, recent evidence, and a compact recovery brief into continuation.
  - session id remains the stable LangGraph thread id boundary.
- Deferred:
  - full runtime object reconstruction.
  - database-backed persistence.
  - task/subagent recovery.

LangChain architecture:
- Primitive used:
  - normal message history continuation with a small `system` resume context message.
  - existing `create_agent` runtime and `thread_id = session_id` mapping remain unchanged.
- Why no heavier abstraction:
  - 12C only needed model-visible recovery context on resume; a new graph node/checkpointer/store would widen the stage without immediate benefit.

Boundary findings:
- New issue handled:
  - synthetic resume context must not be persisted as transcript history or skew message indexes.
- Residual risk:
  - an independent subagent review was attempted but failed due usage limits, so final review was local-only.
- Impact on next stage:
  - 12D can focus on memory quality policy without also solving resume recovery context.

Decision:
- continue

Reason:
- Tests, ruff, and mypy passed.
- Scope stayed inside session/recovery hardening.
- No blocker appeared that invalidates `Stage 12D: Memory Quality Policy`.
