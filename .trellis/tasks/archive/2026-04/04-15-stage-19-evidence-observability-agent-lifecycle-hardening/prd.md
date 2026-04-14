# Stage 19: Evidence Observability and Agent Lifecycle Hardening

## Goal

Advance H19 evidence/observability and H11 agent-as-tool lifecycle with the smallest useful post-18B slices: make verifier evidence easier to interpret on resume, and add minimal lineage metadata that links verifier evidence back to the parent session and child verifier invocation.

## Mode

`stage-iterate lean-batch + multi-agent`

Explorer usage:

* Explorer A mapped relevant cc-haha source for H19/H11/H06/H10.
* Explorer B audited local `coding_deepgent` module boundaries and tests.

## Corresponding Highlights

* `H19 Observability and evidence ledger` - primary for both 19A and 19B.
* `H11 Agent as tool and runtime object` - primary for 19B lineage metadata.
* `H06 Session transcript, evidence, and resume` - primary for 19A recovery brief visibility.
* `H10 Plan / Execute / Verify workflow discipline` - indirect; verifier remains the workflow boundary.

## Sub-Stage 19A: Verifier Evidence Provenance In Recovery Brief

### Function Summary

When recovery brief renders verification evidence, include a concise provenance suffix derived from existing evidence fields, such as `plan=<plan_id>` and `verdict=<verdict>`.

### Expected Benefit

* Observability: resume context says which plan/verdict a verifier evidence row belongs to.
* Recoverability: users and agents can interpret verifier evidence after session resume without re-opening raw JSONL.
* Testability: recovery brief rendering proves verifier evidence metadata survives into resume-facing text.

### Corresponding Modules

* `coding_deepgent.sessions.resume`
* `coding_deepgent.sessions.records`
* `coding_deepgent.tests.test_sessions`
* `coding_deepgent.tests.test_subagents`

### In Scope

* Render short provenance only for `kind="verification"` evidence.
* Preserve the existing recovery brief evidence path.
* Keep ordinary runtime evidence concise.

### Out Of Scope

* Dumping full evidence metadata into recovery brief.
* New evidence store or transcript schema.
* New resume picker UI.

## Sub-Stage 19B: Verifier Evidence Lineage Metadata

### Function Summary

Persist minimal parent/child lineage metadata with verifier evidence: parent session id, parent thread id, verifier child thread id, and verifier agent name.

### Expected Benefit

* Agent-runtime observability: verifier evidence can be traced to the parent session and child verifier invocation.
* H11 readiness: child verifier execution becomes more runtime-object-like without adding background lifecycle or mailbox state.
* Debuggability: failures can be correlated with exact child thread naming.

### Corresponding Modules

* `coding_deepgent.subagents.tools`
* `coding_deepgent.runtime.context`
* `coding_deepgent.sessions.store_jsonl`
* `coding_deepgent.tests.test_subagents`

### In Scope

* Add stable lineage fields to verifier evidence metadata.
* Derive lineage from existing `ToolRuntime.context` and `ToolRuntime.config`.
* Keep verifier JSON output contract unchanged.

### Out Of Scope

* Coordinator runtime.
* Mailbox / SendMessage.
* Background worker execution.
* Agent task objects or automatic task/plan mutation.
* Storing full runtime context in evidence metadata.

## cc-haha Alignment

### Expected Effect

Aligning these slices should improve observability, recoverability, and agent-runtime traceability. The local runtime effect is: verifier evidence becomes understandable after resume and can be traced to the bounded child verifier invocation, while intentionally deferring cc-haha's richer background agent lifecycle.

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Session transcript / resume visibility | `sessionStorage` records transcript and sidechain material that resume/loading paths can inspect | verifier evidence should be first-class resume context, not only immediate tool output | render verification provenance in recovery brief using existing evidence ledger | partial | Align now without new store or UI |
| Agent lifecycle trace | task notifications and local-agent flows carry lifecycle identity / agent scoping | verifier evidence can be correlated with parent session and child verifier invocation | add minimal parent/child lineage metadata to evidence | partial | Align as metadata, not full runtime object |
| Background/local agent lifecycle | cc-haha has richer task status, queued notifications, sidechain files, and event plumbing | useful later for H11/H13, but too broad now | none | defer | Do not add coordinator/mailbox/background runtime |

### Source Files Inspected

Explorer A inspected:

* `/root/claude-code-haha/src/query.ts`
* `/root/claude-code-haha/src/cli/print.ts`
* `/root/claude-code-haha/src/cli/remoteIO.ts`
* `/root/claude-code-haha/src/utils/sessionStorage.ts`
* `/root/claude-code-haha/src/services/api/claude.ts`
* `/root/claude-code-haha/src/Task.ts`

## LangChain Architecture

Use:

* Existing `run_subagent` LangChain tool boundary.
* Existing `ToolRuntime.context` and `ToolRuntime.config` access.
* Existing session evidence ledger and recovery brief renderer.

Avoid:

* New graph nodes.
* New custom query loop.
* Middleware that secretly owns verifier workflow persistence.
* New persistence store.

## Acceptance Criteria

* [x] Verification evidence in recovery brief includes concise plan/verdict provenance.
* [x] Non-verification evidence rendering remains concise.
* [x] Verifier evidence metadata includes parent session id, parent thread id, child verifier thread id, and verifier agent name when runtime context is available.
* [x] Verifier JSON output contract remains unchanged.
* [x] No task/plan mutation is introduced.
* [x] Focused tests, targeted ruff, and targeted mypy pass.

## Test Plan

* Extend `tests/test_sessions.py` for recovery brief provenance rendering.
* Extend `tests/test_subagents.py` for verifier lineage metadata roundtrip.
* Run targeted app/subagent/session tests affected by runtime/session context.
* Run targeted `ruff check` and `mypy` on changed files.

## Checkpoint: Stage 19A

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- `render_recovery_brief()` now renders concise provenance for verification evidence when stable fields exist.
- Provenance uses `plan=<plan_id>` and `verdict=<verdict>`.
- Non-verification evidence remains concise and does not dump arbitrary metadata.

Corresponding highlights:
- `H19`: evidence rows are more observable in resume/recovery context.
- `H06`: recovery brief carries enough provenance to interpret verification evidence after resume.
- `H10`: verifier workflow evidence is clearer without changing the verifier contract.

Corresponding modules:
- `coding_deepgent.sessions.resume`
- `coding_deepgent.sessions.records`
- `coding_deepgent.tests.test_sessions`

Tradeoff / complexity:
- Chosen: render only short, stable provenance for verification evidence.
- Deferred: resume picker UI changes, full metadata rendering, separate evidence store.
- Why now: Stage 18B made verifier evidence durable; 19A makes that durable evidence readable at the resume boundary.

Verification:
- `pytest -q coding-deepgent/tests/test_sessions.py::test_session_evidence_roundtrip_and_recovery_brief coding-deepgent/tests/test_sessions.py::test_recovery_brief_renders_verification_provenance_only coding-deepgent/tests/test_sessions.py::test_recovery_brief_limits_recent_evidence_in_original_order`

Decision:
- continue

Reason:
- 19A is complete and 19B remains a narrow, source-backed H11/H19 metadata extension on the same evidence path.

## Checkpoint: Stage 19B

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Verifier evidence metadata now includes bounded lineage fields:
  - `parent_session_id`
  - `parent_thread_id`
  - `child_thread_id`
  - `verifier_agent_name`
- The verifier JSON result contract remains unchanged.
- No task or plan mutation was introduced.

Corresponding highlights:
- `H11`: verifier evidence can now be traced as an agent-as-tool child invocation without adding a background runtime object.
- `H19`: evidence has enough lineage metadata to debug verifier execution.
- `H06`: lineage survives session load through the existing JSONL evidence ledger.
- `H10`: verifier workflow remains bounded to `run_subagent`.

Corresponding modules:
- `coding_deepgent.subagents.tools`
- `coding_deepgent.sessions.store_jsonl`
- `coding_deepgent.tests.test_subagents`

Tradeoff / complexity:
- Chosen: add four stable lineage metadata fields.
- Deferred: coordinator runtime, mailbox, background workers, local-agent task objects, automatic task/plan mutation, and full runtime-context serialization.
- Why now: this gives useful H11 traceability from the existing child verifier invocation with minimal storage and no new scheduler.

Verification:
- `pytest -q coding-deepgent/tests/test_subagents.py::test_run_subagent_tool_persists_verifier_evidence_roundtrip coding-deepgent/tests/test_subagents.py::test_run_subagent_tool_returns_structured_verifier_result coding-deepgent/tests/test_subagents.py::test_run_subagent_task_verifier_executes_real_child_agent`
- `pytest -q coding-deepgent/tests/test_sessions.py::test_session_evidence_roundtrip_and_recovery_brief coding-deepgent/tests/test_sessions.py::test_recovery_brief_renders_verification_provenance_only coding-deepgent/tests/test_sessions.py::test_recovery_brief_limits_recent_evidence_in_original_order coding-deepgent/tests/test_subagents.py::test_run_subagent_tool_persists_verifier_evidence_roundtrip coding-deepgent/tests/test_subagents.py::test_run_subagent_tool_returns_structured_verifier_result coding-deepgent/tests/test_subagents.py::test_run_subagent_task_verifier_executes_real_child_agent coding-deepgent/tests/test_cli.py::test_sessions_resume_uses_recovery_brief_continuation_history`
- `ruff check coding-deepgent/src/coding_deepgent/sessions/resume.py coding-deepgent/src/coding_deepgent/subagents/tools.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_subagents.py`
- `mypy coding-deepgent/src/coding_deepgent/sessions/resume.py coding-deepgent/src/coding_deepgent/subagents/tools.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_subagents.py`

cc-haha alignment:
- Explorer A inspected:
  - `/root/claude-code-haha/src/query.ts`
  - `/root/claude-code-haha/src/cli/print.ts`
  - `/root/claude-code-haha/src/cli/remoteIO.ts`
  - `/root/claude-code-haha/src/utils/sessionStorage.ts`
  - `/root/claude-code-haha/src/services/api/claude.ts`
  - `/root/claude-code-haha/src/Task.ts`
- Aligned now:
  - session/resume-facing evidence visibility
  - lightweight parent/child verifier lineage
- Deferred:
  - sidechain transcript files
  - queued task notifications
  - full background/local-agent lifecycle
  - coordinator/mailbox runtime

LangChain architecture:
- Used existing `run_subagent` tool and `ToolRuntime` context/config.
- Added no new graph node, middleware layer, custom query loop, or persistence store.

Boundary findings:
- Arbitrary evidence metadata should not be rendered into recovery brief; only stable provenance fields are safe.
- H11 lineage can advance as metadata now, while task-backed agent lifecycle should wait for a dedicated source-backed stage.

Decision:
- terminal

Reason:
- 19A and 19B complete the narrow lean-batch. The optional runtime-event evidence stage is valid but higher-risk because it can expand into all-event persistence; it should get its own PRD before implementation.
