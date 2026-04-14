# Stage 28: Observability Evidence Closeout

## Goal

Close H19 and minimal H20 MVP gaps by tightening structured runtime events, session evidence, recovery visibility, and any local-only metrics/counter decision needed by context/runtime behavior.

## Function Summary

This stage should decide and implement the smallest local observability closeout: evidence should survive session resume boundaries, runtime events should have stable envelopes, and H20 should be either minimal-local implemented or explicitly deferred beyond existing local counters.

## Expected Benefit

* Observability: important runtime and verification outcomes remain inspectable and recoverable.
* Testability: event/evidence envelopes are pinned by tests.
* Context-efficiency: H20 remains bounded to local metrics/counters only, avoiding telemetry/cache scope creep.

## Corresponding Highlights

* `H19 Observability and evidence ledger`
* `H20 Cost/cache instrumentation` minimal local slice

## Corresponding Modules

* `coding_deepgent.runtime`
* `coding_deepgent.sessions`
* `coding_deepgent.tool_system`
* `coding_deepgent.hooks`
* `coding_deepgent.subagents`
* `coding_deepgent.compact`

## Out Of Scope

* remote telemetry backend
* provider-specific cache instrumentation
* full cost accounting dashboard
* event bus / daemon
* coordinator/mailbox/background runtime

## Acceptance Criteria

* [x] cc-haha source mapping for H19/minimal H20 is recorded in this stage PRD.
* [x] local H19/H20 MVP closeout slices are explicit.
* [x] focused tests, targeted ruff, and targeted mypy pass for changed files.
* [x] checkpoint records whether H19 becomes implemented and H20 remains minimal/deferred with explicit boundary.

## cc-haha Alignment

### Expected Effect

Aligning this behavior should improve observability, recoverability, and testability. The local runtime effect is: high-value runtime/tool/hook failures survive resume boundaries as concise session evidence, while H20 remains limited to local context/budget counters and does not become a telemetry system.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Durable observability | transcript/evidence writes survive resume boundaries | blocked hooks and denied tools are recoverable and inspectable | whitelist runtime events into session evidence | align | Implement now |
| Event breadth | upstream emits many analytics/runtime events | avoid noisy or sensitive local ledger | only `hook_blocked` and `permission_denied` persist | partial | Defer all-event telemetry |
| Cost/cache metrics | upstream has token/cache/cost accounting | local MVP only needs budget/projection counters | existing budget/projection/compact counters | minimal | No new metrics system |
| Remote analytics | upstream has 1P/datadog/diagnostic tracking | not a local MVP requirement | none | do-not-copy/defer | Keep out of MVP |

### Source files inspected

Explorer A inspected:

* `/root/claude-code-haha/src/query.ts`
* `/root/claude-code-haha/src/QueryEngine.ts`
* `/root/claude-code-haha/src/utils/sessionStorage.ts`
* `/root/claude-code-haha/src/services/analytics/index.ts`
* `/root/claude-code-haha/src/services/analytics/firstPartyEventLogger.ts`
* `/root/claude-code-haha/src/services/analytics/metadata.ts`
* `/root/claude-code-haha/src/services/diagnosticTracking.ts`
* `/root/claude-code-haha/src/utils/tokens.ts`
* `/root/claude-code-haha/src/services/compact/autoCompact.ts`
* `/root/claude-code-haha/src/services/compact/compact.ts`
* `/root/claude-code-haha/src/services/compact/microCompact.ts`
* `/root/claude-code-haha/src/cost-tracker.ts`

## Technical Approach

* Added `sessions.evidence_events.append_runtime_event_evidence()` as the single whitelist bridge from `RuntimeEvent` to session evidence.
* Wired hook dispatch and tool guard events into the bridge.
* Persist only:
  * `hook_blocked`
  * `permission_denied`
* Store concise metadata only: source, event kind, hook event, tool, policy code, permission behavior, blocked flag.
* Keep H20 as the existing local budget/projection/counting contract; no provider-specific cost/cache instrumentation is added.

## Checkpoint: Stage 28

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added a whitelisted runtime-event-to-session-evidence bridge.
- Persisted blocked hook events as `runtime_event` evidence.
- Persisted permission-denied tool guard events as `runtime_event` evidence.
- Added roundtrip tests proving event evidence appears in recovery brief.
- Preserved H20 as local budget/projection/compact counters only.

Corresponding highlights:
- `H19 Observability and evidence ledger`
- `H20 Cost/cache instrumentation` minimal local slice

Corresponding modules:
- `coding_deepgent.runtime`
- `coding_deepgent.sessions`
- `coding_deepgent.hooks`
- `coding_deepgent.tool_system`
- `coding_deepgent.compact`

Tradeoff / complexity:
- Chosen: whitelist two high-value runtime events into the existing session evidence ledger.
- Deferred: remote telemetry, full analytics, provider-specific token/cache/cost accounting, event bus/daemon.
- Why this complexity is worth it now: H19 previously had in-memory runtime events and durable verifier evidence, but blocked/denied runtime facts did not survive resume boundaries.

Verification:
- `pytest -q coding-deepgent/tests/test_hooks.py coding-deepgent/tests/test_tool_system_middleware.py coding-deepgent/tests/test_sessions.py::test_session_evidence_roundtrip_and_recovery_brief coding-deepgent/tests/test_subagents.py::test_run_subagent_tool_persists_verifier_evidence_roundtrip coding-deepgent/tests/test_compact_budget.py coding-deepgent/tests/test_rendering.py coding-deepgent/tests/test_message_projection.py`
- `ruff check coding-deepgent/src/coding_deepgent/sessions/evidence_events.py coding-deepgent/src/coding_deepgent/hooks/dispatcher.py coding-deepgent/src/coding_deepgent/tool_system/middleware.py coding-deepgent/tests/test_hooks.py coding-deepgent/tests/test_tool_system_middleware.py`
- `mypy coding-deepgent/src/coding_deepgent/sessions/evidence_events.py coding-deepgent/src/coding_deepgent/hooks/dispatcher.py coding-deepgent/src/coding_deepgent/tool_system/middleware.py coding-deepgent/tests/test_hooks.py coding-deepgent/tests/test_tool_system_middleware.py`

Boundary findings:
- Runtime evidence persistence must stay whitelisted and summary-based; dumping arbitrary args/results would turn the session ledger into noisy telemetry.
- H20 is complete for MVP as local budget/projection/compact counters; rich cost/cache instrumentation is deferred.

Decision:
- continue

Reason:
- Stage 28 is complete and Stage 29 (deferred-boundary ADR + MVP release checklist) remains the next milestone from the canonical dashboard.
