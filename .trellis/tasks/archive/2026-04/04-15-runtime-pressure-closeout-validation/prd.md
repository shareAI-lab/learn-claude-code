# runtime pressure closeout and validation

## Goal

Close out the current `coding-deepgent` runtime context pressure work as one integrated optimization pass: turn the recent live compact/runtime-pressure loop into something easier to observe, configurable enough to tune locally, capable of refreshing live session-memory state after successful compact operations, and validated more broadly across compact/session/runtime boundaries.

## What I already know

* The parent task `.trellis/tasks/04-15-runtime-context-pressure-management` already implemented:
  * tool result storage
  * live microcompact
  * live auto-compact
  * post-compact restoration for persisted-output paths
  * reactive compact
  * live session-memory assist during compact
  * runtime pressure events and bounded session evidence
* The user explicitly asked to avoid "挤牙膏" delivery for this family and wants a one-pass closeout where practical.
* Existing observability is event-level, but there is not yet a compact/runtime-pressure summary view in recovery surfaces.
* Existing session memory helpers already have:
  * artifact parsing
  * status rendering
  * threshold policy
  * metric estimation
  * generated-compact summary update contribution
* Current `agent_runtime_service.session_payload()` now forwards `session_memory` into live runtime payload, but live compact does not yet refresh the artifact after successful compact operations.
* Current live auto-compact threshold and keep counts are hard-coded in `compact/runtime_pressure.py`.

## Assumptions

* This task should build on the current runtime-pressure implementation rather than reopening the parent family.
* "Optimize these contents" for this closeout pass means:
  * compact/runtime counters or summary visibility
  * live session-memory refresh after compact
  * configurable pressure thresholds
  * broader regression/validation
* Provider-specific context-window logic and richer plan/skill/agent restoration are still too wide for this task unless a concrete blocker appears.

## Open Questions

* None. The closeout scope is derived from the user's direct request and the current parent task state.

## Requirements

* Add a bounded runtime-pressure summary view that can survive resume boundaries.
* Reuse existing session evidence or contribution seams rather than inventing a second compact metrics system.
* After successful live auto-compact or reactive compact, refresh the in-memory/live `session_memory` artifact using the existing local threshold policy when due.
* Make the live pressure loop locally configurable through settings for at least:
  * auto-compact threshold
  * kept recent tool results
  * kept recent messages after compact
* Keep the implementation LangChain-native and middleware-first.
* Run a broader focused regression covering compact/session/runtime/evidence integration.

## Acceptance Criteria

* [ ] Recovery/resume surfaces can show a bounded runtime-pressure summary derived from current compact/runtime evidence.
* [ ] Successful live compact can refresh session-memory state when the current threshold policy says it is due.
* [ ] Runtime-pressure thresholds are configurable from settings rather than hard-coded only in code.
* [ ] Broader focused regression for compact/session/runtime/evidence passes.
* [ ] No new custom query runtime or compact-specific persistence stack is introduced.

## Definition of Done

* Focused product tests pass.
* `ruff check` and `mypy` pass on changed files.
* Trellis contracts/PRD are updated where behavior changes.
* Residual risks or deferred items are stated explicitly.

## Out of Scope

* Provider-specific context-window discovery
* Richer plan/skill/agent/task restoration after compact
* Full release validation across the whole repo
* New analytics/telemetry backend
* Remote/team/runtime control-plane work

## Expected Effect

Aligning this closeout behavior should improve reliability, recoverability, maintainability, and observability.

The local runtime effect is:

* compact/runtime pressure behavior becomes easier to inspect after resume
* live compact can keep session-memory continuity fresher without waiting for explicit CLI compact paths
* pressure thresholds become tunable without code edits
* the compact/session/runtime stack is validated as one integrated product path

If these effects do not show up in focused runtime and session tests, the closeout is not worth shipping.

## cc-haha Alignment

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Compact/runtime observability | cc compact/query flow records compact transitions and metadata as first-class runtime behavior | compact activity is inspectable after the fact, not only while live | recovery summary built from current runtime-event evidence | align | Implement now |
| Session-memory compact continuity | cc session-memory compact is part of the compaction system, not only a manual assist path | live compact can improve continuity, not only consume stale memory | refresh local `session_memory` artifact after successful live compact when due | partial | Implement bounded local equivalent now |
| Compact tuning | cc has explicit compact thresholds/configs | local tuning does not require code edits | settings-backed thresholds and keep counts | partial | Implement now, local-only |
| Rich provider-specific compact telemetry | cc has deeper analytics/provider-aware compact machinery | richer insight but higher complexity | none for this task | defer | Not needed for local closeout |

## Technical Approach

* Add one small session contribution that aggregates compact/runtime-event evidence into a bounded recovery brief section.
* Extend runtime pressure middleware so a successful live compact can update `request.state["session_memory"]` through the existing threshold helpers when appropriate.
* Move current hard-coded runtime pressure defaults behind `Settings` and thread them through container wiring.
* Run a broader but still scoped validation set across:
  * runtime pressure
  * sessions
  * hooks/runtime events
  * tool-system middleware

## Technical Notes

* Parent task: `.trellis/tasks/04-15-runtime-context-pressure-management`
* New task: `.trellis/tasks/04-15-runtime-pressure-closeout-validation`
* Likely modules:
  * `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`
  * `coding-deepgent/src/coding_deepgent/sessions/evidence_events.py`
  * `coding-deepgent/src/coding_deepgent/sessions/contribution_registry.py`
  * `coding-deepgent/src/coding_deepgent/sessions/contributions.py`
  * `coding-deepgent/src/coding_deepgent/sessions/session_memory.py`
  * `coding-deepgent/src/coding_deepgent/settings.py`
  * `coding-deepgent/src/coding_deepgent/containers/app.py`

## Checkpoint: Integrated Closeout Pass

State:

* checkpoint

Verdict:

* APPROVE

Implemented:

* Added runtime-pressure recovery summary support through a new session
  contribution module:
  * `coding_deepgent.sessions.runtime_pressure`
  * wired into recovery brief contributions
* Extended live compact so successful auto/reactive compact can refresh
  `session_memory` state via the existing local threshold policy using
  `source=live_compact`
* Extended runtime state and session state propagation so `session_memory`
  survives the live runtime path and outer session state update
* Moved runtime-pressure tuning knobs into `Settings` and threaded them through
  container wiring:
  * `auto_compact_threshold_tokens`
  * `keep_recent_tool_results`
  * `keep_recent_messages_after_compact`
* Updated backend compact/runtime contracts to cover:
  * settings-backed thresholds
  * live session-memory refresh
  * runtime-pressure recovery summary

Verification:

* `pytest -q coding-deepgent/tests/test_agent_runtime_service.py coding-deepgent/tests/test_runtime_pressure.py coding-deepgent/tests/test_session_contributions.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_hooks.py coding-deepgent/tests/test_tool_system_middleware.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_compact_summarizer.py coding-deepgent/tests/test_memory_integration.py`
* `ruff check coding-deepgent/src/coding_deepgent/runtime/state.py coding-deepgent/src/coding_deepgent/agent_runtime_service.py coding-deepgent/src/coding_deepgent/settings.py coding-deepgent/src/coding_deepgent/containers/app.py coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/src/coding_deepgent/sessions/session_memory.py coding-deepgent/src/coding_deepgent/sessions/runtime_pressure.py coding-deepgent/src/coding_deepgent/sessions/contribution_registry.py coding-deepgent/tests/test_agent_runtime_service.py coding-deepgent/tests/test_runtime_pressure.py coding-deepgent/tests/test_session_contributions.py coding-deepgent/tests/test_app.py`
* `mypy coding-deepgent/src/coding_deepgent/runtime/state.py coding-deepgent/src/coding_deepgent/agent_runtime_service.py coding-deepgent/src/coding_deepgent/settings.py coding-deepgent/src/coding_deepgent/containers/app.py coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/src/coding_deepgent/sessions/session_memory.py coding-deepgent/src/coding_deepgent/sessions/runtime_pressure.py coding-deepgent/src/coding_deepgent/sessions/contribution_registry.py`

cc-haha alignment:

* Source bands reused:
  * compact/query/runtime observability expectations from cc compact flow
  * session-memory compact as part of the compaction family rather than a
    disconnected manual-only seam
* Aligned now:
  * runtime pressure activity is inspectable after resume through bounded
    summary counts
  * live compact can improve current session-memory continuity locally
  * pressure thresholds are explicit product config, not magic constants only
* Deferred:
  * provider-specific context-window discovery
  * richer restoration breadth
  * full release validation

LangChain architecture:

* Primitive used:
  * middleware-owned runtime pressure behavior
  * settings/config threading through container wiring
  * existing session contribution and evidence seams
* Why this stays LangChain-native:
  * no second compact stack, no custom query loop, no extra persistence system

Residual risk:

* live session-memory refresh currently updates runtime/session state locally but
  is not yet tied to a richer post-compact review or promotion workflow
* provider-specific error typing and context-window calibration remain heuristic

Decision:

* APPROVE

Reason:

* the requested closeout items are implemented in one integrated pass
* broader focused validation passed
* no new architecture drift was introduced

## Checkpoint: Product Validation Closeout

State:

* terminal

Verdict:

* APPROVE

Validation:

* `pytest -q coding-deepgent/tests`
  * `256 passed`
* `ruff check coding-deepgent/src coding-deepgent/tests`
  * passed
* `mypy coding-deepgent/src/coding_deepgent`
  * passed

Scope:

* This was product-mainline validation for `coding-deepgent`.
* It did not run root/tutorial/reference tests because the current mainline
  scope is `coding-deepgent/`, and the worktree includes unrelated deletions in
  tutorial/reference paths.

Residual risk:

* No live LLM integration test was run.
* Provider-specific context-window behavior remains heuristic.
* Broader repository validation should wait until unrelated worktree churn is
  intentionally reconciled.
