# Stage 18B: Verifier Result Persistence and Evidence Integration

## Goal

Persist bounded verifier outcomes from `run_subagent` into the existing session evidence ledger, so verification work survives chat history boundaries and appears in recovery/resume context without introducing coordinator runtime, mailbox state, or automatic task mutation.

## Function Summary

This stage adds one concrete function:

* when a verifier subagent returns `VERDICT: PASS|FAIL|PARTIAL`, that verifier outcome is written into the current session's durable evidence ledger so later resume/recovery flows can see it again

## Upgraded Function

The workflow system is upgraded from real synchronous verifier execution to durable verifier result recording in the existing session transcript/evidence model.

## Expected Benefit

* Recoverability: verifier outcomes survive beyond the immediate tool return and can reappear in session recovery briefs.
* Reliability: the product gets a durable audit trail for verifier verdicts instead of relying on the parent agent to restate them accurately.
* Testability: verifier execution can be checked end-to-end through a concrete persisted evidence record instead of only an in-memory JSON result.

## Cross-Session Memory Impact

Direct, but narrow.

* This stage improves cross-session continuity because verifier results will persist across resume/recovery boundaries.
* This stage does not yet implement the full cross-session memory system.
* It is still worth doing now because it strengthens a real durable memory path that already exists locally: session evidence.

## Out of Scope

* automatic task status mutation from verifier verdicts
* coordinator runtime
* mailbox / SendMessage
* background worker execution
* separate verifier evidence store outside the existing session JSONL ledger
* deepening the general subagent path
* richer verifier artifact formats beyond the current session evidence record

## Requirements

* Keep `run_subagent` as the only model-visible verifier entrypoint.
* Preserve the existing `VerifierSubagentResult` JSON contract.
* After verifier execution succeeds, append one session evidence record for the verifier result when session recording context is available.
* Use the existing session evidence ledger rather than creating a new verifier-specific persistence mechanism.
* Persist the verifier result with:
  * `kind="verification"`
  * a status derived from the verifier verdict
  * a concise summary derived from the verifier content
  * metadata that includes at least `plan_id` and verifier verdict
* Keep persistence explicit and bounded to the same synchronous tool call.
* Do not mutate durable tasks or plans based on the recorded verifier result.
* Keep general subagent behavior unchanged.

## Why Now

* `18A` already made verifier execution real; without persistence, verifier conclusions still disappear too easily after the tool return.
* This is the smallest next step that improves cross-session memory without introducing a larger coordinator or task-lifecycle runtime.

## Acceptance Criteria

* [x] verifier calls append exactly one evidence record to the current recorded session when session recording is available.
* [x] persisted verifier evidence roundtrips through `JsonlSessionStore.load_session()`.
* [x] verifier evidence appears in the existing recovery brief / session evidence path without extra ad hoc rendering seams.
* [x] verifier evidence status is derived deterministically from `VERDICT: PASS|FAIL|PARTIAL`.
* [x] verifier calls without usable session recording context fail or skip in one explicit, tested way rather than silently pretending to persist.
* [x] general subagent behavior and verifier JSON return contract remain unchanged.
* [x] Focused tests, targeted lint, and targeted mypy pass.

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve recoverability, reliability, and product parity. The local runtime effect is: verifier work no longer disappears after the tool return, and the session ledger gains a durable verification trail while intentionally deferring cc-haha's richer background/task lifecycle.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Verification agent output | verification agent requires an explicit `VERDICT: PASS|FAIL|PARTIAL` line | local persistence can derive deterministic verifier status from a bounded textual contract | verdict parser + evidence status mapping | partial | Align now using existing verifier output contract |
| Agent runtime persistence | subagent/session runtime writes transcript material under session storage | verifier outcome should survive the immediate tool return | append verifier evidence into session JSONL ledger | partial | Reuse existing session evidence path now |
| Background/task lifecycle | upstream runtime has richer local-agent task state and summaries | local product should avoid task-object/runtime expansion for this stage | none | defer | Keep out of scope |

### Source files inspected

* `/root/claude-code-haha/src/tools/AgentTool/built-in/verificationAgent.ts`
* `/root/claude-code-haha/src/tools/AgentTool/runAgent.ts`
* `/root/claude-code-haha/src/utils/sessionStorage.ts`

## LangChain Architecture

Use:

* the existing `run_subagent` verifier path
* the existing session JSONL evidence model
* a small verifier-result persistence helper with explicit seams

Avoid:

* global hidden workflow mutation
* new coordinator/mailbox abstractions
* a second verifier persistence store
* deepening the general subagent runtime just to record verifier outcomes

## Technical Approach

* Reuse the Stage 18A verifier execution path and structured result contract.
* Add a small verifier result parser that extracts:
  * terminal verdict
  * concise summary text for session evidence
* Add a bounded persistence helper that records verifier evidence through the existing session store seam for the active session/workdir.
* Keep the persistence seam explicit rather than scattering session writes inside generic tool or middleware code.
* Add focused tests for:
  * verdict-to-evidence status mapping
  * verifier evidence append + session roundtrip
  * recovery brief exposure of verifier evidence
  * unchanged general subagent behavior

## Checkpoint: Stage 18B

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added optional `session_context` to `RuntimeContext` and threaded it through the app/runtime invocation path when `run_prompt_with_recording()` has an active recorded session.
- Tightened the verifier child prompt to require a final `VERDICT: PASS|FAIL|PARTIAL` line.
- Added deterministic verifier verdict parsing and evidence summary derivation.
- Added bounded verifier evidence persistence on the `run_subagent` verifier tool path.
- Persisted verifier evidence through the existing `JsonlSessionStore.append_evidence()` ledger with:
  - `kind="verification"`
  - `status` mapped as `PASS -> passed`, `FAIL -> failed`, `PARTIAL -> partial`
  - `subject=<plan_id>`
  - metadata containing `plan_id`, `plan_title`, `verdict`, `task_ids`, and `tool_allowlist`
- Preserved the existing `VerifierSubagentResult` JSON contract and general subagent behavior.
- Updated backend task/session contracts for the runtime `session_context` and verifier evidence persistence behavior.

Corresponding highlights:
- `H10 Plan / Execute / Verify workflow discipline`: verifier results are now durable workflow evidence instead of only immediate tool output.
- `H11 Agent as tool and runtime object`: verifier still enters only through `run_subagent`, with a bounded child-agent path and structured result protocol.
- `H19 Observability and evidence ledger`: verifier verdicts now enter the session evidence ledger.
- `H06 Session transcript, evidence, and resume`: verifier evidence roundtrips through session load and appears in recovery brief rendering.

Corresponding modules:
- `coding_deepgent.subagents`: verifier prompt, verdict parser, evidence summary, and `run_subagent` persistence hook.
- `coding_deepgent.runtime`: optional `RuntimeContext.session_context` boundary.
- `coding_deepgent.sessions`: recorded-session context injection and existing JSONL evidence ledger reuse.
- `coding_deepgent.tasks`: durable `PlanArtifact` remains the verifier boundary and evidence subject.
- `coding_deepgent.tool_system`: verifier tool allowlist and guard middleware remain unchanged.

Tradeoff / complexity:
- Chosen: reuse the existing session evidence ledger and pass a narrow optional session context through runtime invocation.
- Deferred: coordinator runtime, mailbox / SendMessage, background workers, task-backed local-agent lifecycle, automatic task/plan mutation, and a verifier-specific persistence store.
- Why this complexity is worth it now: Stage 18A made verifier execution real, but without durable evidence the result still disappears across resume boundaries. This adds cross-session continuity through an existing persistence mechanism with minimal new surface area.

Verification:
- `pytest -q coding-deepgent/tests/test_subagents.py`
- `pytest -q coding-deepgent/tests/test_sessions.py::test_session_evidence_roundtrip_and_recovery_brief coding-deepgent/tests/test_cli.py::test_run_once_records_new_and_resumed_session_transcript`
- `pytest -q coding-deepgent/tests/test_subagents.py coding-deepgent/tests/test_sessions.py::test_session_evidence_roundtrip_and_recovery_brief coding-deepgent/tests/test_cli.py::test_run_once_records_new_and_resumed_session_transcript coding-deepgent/tests/test_cli.py::test_run_once_passes_recording_session_context_to_agent coding-deepgent/tests/test_cli.py::test_sessions_resume_rejects_manual_and_generated_compact_together coding-deepgent/tests/test_cli.py::test_sessions_resume_rejects_compact_instructions_without_generation`
- `pytest -q coding-deepgent/tests/test_app.py coding-deepgent/tests/test_tool_system_registry.py coding-deepgent/tests/test_tool_system_middleware.py`
- `ruff check coding-deepgent/src/coding_deepgent/subagents/tools.py coding-deepgent/src/coding_deepgent/runtime/context.py coding-deepgent/src/coding_deepgent/runtime/invocation.py coding-deepgent/src/coding_deepgent/app.py coding-deepgent/src/coding_deepgent/bootstrap.py coding-deepgent/src/coding_deepgent/agent_loop_service.py coding-deepgent/src/coding_deepgent/sessions/service.py coding-deepgent/tests/test_subagents.py coding-deepgent/tests/test_cli.py`
- `mypy coding-deepgent/src/coding_deepgent/subagents/tools.py coding-deepgent/src/coding_deepgent/runtime/context.py coding-deepgent/src/coding_deepgent/runtime/invocation.py coding-deepgent/src/coding_deepgent/app.py coding-deepgent/src/coding_deepgent/bootstrap.py coding-deepgent/src/coding_deepgent/agent_loop_service.py coding-deepgent/src/coding_deepgent/sessions/service.py coding-deepgent/tests/test_subagents.py coding-deepgent/tests/test_cli.py`

cc-haha alignment:
- Source mapping reused from the stage PRD:
  - `/root/claude-code-haha/src/tools/AgentTool/built-in/verificationAgent.ts`
  - `/root/claude-code-haha/src/tools/AgentTool/runAgent.ts`
  - `/root/claude-code-haha/src/utils/sessionStorage.ts`
- Aligned now:
  - explicit verifier verdict line drives deterministic local status
  - verifier outcome is persisted into session transcript/evidence storage
- Deferred:
  - upstream richer background/task lifecycle
  - coordinator/team runtime
  - agent mailbox and resumable local-agent task objects

LangChain architecture:
- Used existing `run_subagent` tool path and `ToolRuntime.context`.
- Kept persistence outside generic tool middleware so only verifier result recording owns this workflow-specific behavior.
- Added no custom query loop, no new graph node, and no extra verifier store.

Boundary findings:
- Runtime context needed one narrow optional session-recording field. Guessing session storage from `session_id` alone would have broken custom `session_dir` settings and hidden the persistence boundary.
- Verifier calls without `session_context` now explicitly skip persistence and keep returning the structured verifier JSON.

Decision:
- terminal

Reason:
- Stage 18B completes the remaining Stage 18 persistence step with focused verification passing. There is no next Stage 18 sub-stage left to auto-continue into under lean mode.
