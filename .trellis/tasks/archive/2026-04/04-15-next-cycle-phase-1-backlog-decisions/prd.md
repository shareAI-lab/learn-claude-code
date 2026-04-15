# brainstorm: next-cycle phase 1 backlog decisions

## Goal

Decide what `next-cycle` should take as phase 1 after the Approach A MVP closeout, focusing first on three deferred backlog bands: `context pressure v2 / session-memory compaction`, `plugin lifecycle`, and `mailbox`. The chosen phase-1 band is `context pressure v2 / session-memory compaction`; the remaining goal is to lock its first implementation slice so it delivers concrete local benefit now without reopening broad coordinator/marketplace/background-runtime complexity by accident.

## What I already know

* User selected `context pressure v2 / session-memory compaction` as the next-cycle phase-1 direction.
* User selected `Deterministic Assist` as the first slice inside `context pressure v2 / session-memory compaction`.
* Stage 29 recorded the next-cycle backlog and explicitly deferred `H13 mailbox / SendMessage` and full `H17 plugin install/enable/update lifecycle`.
* Stage 23 closed MVP `H05/H06` as deterministic projection/compact/session continuity, while explicitly deferring richer auto-compact and session-memory runtime breadth.
* Stage 24 closed MVP `H07` as namespace-scoped durable memory with quality gating, while explicitly deferring session-memory extraction, compaction, snapshots, and memory file hooks.
* Stage 27 closed MVP `H17` only as local manifest/source validation; install/enable lifecycle stayed deferred.
* Current codebase already has strong local seams for `compact`, `sessions`, `memory`, `tasks`, `subagents`, and `plugins`, but no mailbox runtime or plugin state machine yet.
* Cross-session memory is a persistent project requirement and future stages must state whether they advance it directly, indirectly, or not at all.

## Assumptions (temporary)

* Phase 1 should stay inside the chosen `context pressure v2 / session-memory compaction` band rather than split effort across the other deferred bands.
* A good first slice should extend an existing strong seam rather than introduce a broad new runtime surface.
* The first slice should preserve today's deterministic compact/session contracts and avoid background timing or extraction races.
* `mailbox` likely has the largest dependency fan-out because it touches task ownership, subagent lifecycle, and later coordinator behavior.

## Open Questions

* None for phase-1 direction and first-slice scope.

## Requirements

* Produce a source-backed comparison of the three candidate backlog bands.
* State the concrete function and local benefit of taking each band now.
* Identify dependencies, risks, and likely MVP-sized phase-1 slices for each band.
* Recommend a phase-1 direction with explicit non-goals and an initial ranked order.
* Lock next-cycle phase 1 to `context pressure v2 / session-memory compaction`.
* Define the first slice so it improves cross-session continuity and compaction quality without adding coordinator, mailbox, marketplace, or full background-agent runtime.
* Lock the first slice to `Deterministic Assist`, not threshold-driven automatic updates or background extraction.

## Acceptance Criteria

* [x] Existing roadmap, handoff, spec, and stage PRDs relevant to the three backlog bands are inspected.
* [x] Current repo state for the relevant modules is inspected.
* [x] cc-haha source reference points are inspected for the three backlog bands.
* [x] The PRD records feasible approaches and a recommended phase-1 choice.
* [x] One high-value phase-1 direction decision is captured from the user.
* [x] One final high-value scope question is resolved for the first `context pressure v2` slice.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Implementing the chosen phase-1 feature in this brainstorm task
* Reopening Stage 29 MVP boundary or claiming all next-cycle items must start together
* `plugin lifecycle` as a phase-1 implementation target
* `mailbox` as a phase-1 implementation target
* threshold-driven automatic session-memory updates in the first phase-1 slice
* background extraction agent/runtime in the first phase-1 slice
* UI/TUI, marketplace, remote bridge, daemon, or full coordinator planning unless required by one of the three bands

## Expected Effect

Choosing the right phase-1 band should improve: cross-session continuity, context-efficiency, and roadmap discipline. The local effect should be: the next stage lands on an already-strong product seam and creates visible capability gain without accidentally importing coordinator or marketplace breadth.

## cc-haha Alignment

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Context pressure v2 / session-memory compaction | `sessionMemory.ts`, `sessionMemoryUtils.ts`, and `sessionMemoryCompact.ts` add threshold-gated extraction plus memory-assisted compaction on top of the compact/session flow | better long-session continuity and context pressure handling while preserving bounded deterministic recovery seams | extend `compact`, `sessions`, and `memory` with a smaller local session-memory-assisted compaction path | partial | Recommended phase 1 |
| Plugin lifecycle | `installedPluginsManager.ts`, `pluginOperations.ts`, `pluginLoader.ts`, and plugin commands separate install metadata from enable state and manage scope/version/cache lifecycle | extension platform becomes operational rather than metadata-only | add local install/enable state model and startup/runtime resolution contracts | defer | Good phase 2 candidate |
| Mailbox / SendMessage | `SendMessageTool.ts`, `teammateMailbox.ts`, `LocalAgentTask.tsx`, and coordinator mode add inbox delivery, pending messages, and resumable teammate task runtime | multi-agent collaboration becomes explicit and resumable | add durable inbox/message routing around `tasks` + `subagents` | defer | Too broad for phase 1 |

### Boundary findings

* `context pressure v2` directly advances the explicit project requirement for stronger cross-session memory/continuity.
* `plugin lifecycle` improves completeness of the extension platform, but does not materially advance cross-session continuity.
* `mailbox` is not just a tool addition; it depends on task-backed local-agent lifecycle and notification/runtime behavior that the local product does not yet own.

## Research Notes

### What the current repo already has

* `compact` and `sessions` already support deterministic manual compaction, compact records, load-time compact selection, recovery brief rendering, and compact-aware resume.
* `memory` already supports namespace-scoped durable memory, quality gating, and bounded middleware recall.
* `plugins` currently stop at deterministic manifest/source validation and declaration checks; there is no install metadata store, enable-state model, or lifecycle command surface.
* `tasks` and `subagents` already support durable task/plan records and bounded verifier execution, but child runtime is intentionally read-only/minimal and lacks mailbox or background message handling.

### Constraints from our repo/project

* The handoff states cross-session memory is a persistent product requirement.
* Stage 29 already closed MVP with H13/H14/H21/H22 deferred; phase 1 should not silently reopen coordinator breadth.
* Current compaction contracts are deterministic and test-heavy; adding opaque background automation too early would weaken that reliability story.
* Current plugin implementation is local-only and schema-first; a lifecycle stage would require new persisted state and CLI/runtime surfaces, not just registry tweaks.

### Feasible approaches here

**Approach A: `context pressure v2 / session-memory compaction`** (Recommended)

* How it works:
  * add a small local session-memory artifact/update seam on top of the existing memory + compact + session stack
  * keep the first slice deterministic and explicit, for example by producing a bounded session-memory summary/artifact that can assist continuation compaction without introducing a broad background runtime
* Pros:
  * strongest direct link to the cross-session memory requirement
  * reuses the most mature existing seams
  * can be staged without coordinator or marketplace side effects
* Cons:
  * needs careful boundary work so session memory does not become a second ad hoc transcript store
  * a fully automatic background extractor should still stay out of the first slice

### Feasible first slices inside Approach A

**A1: Deterministic Assist** (Chosen)

* How it works:
  * introduce an explicit local session-memory artifact/update seam
  * allow compact/resume flows to consume that artifact as a bounded assist when the user explicitly chooses the path or when a deterministic compact helper is invoked
  * keep all timing and state transitions synchronous, local, and testable
* Pros:
  * lowest-risk extension of current compact/session contracts
  * directly improves continuity without inventing a new background lifecycle
  * easiest to prove with targeted contract tests
* Cons:
  * less automatic than upstream
  * phase-1 user benefit is more bounded than a full reactive system

**A2: Threshold-Triggered Local Updates**

* How it works:
  * add local token/tool-call thresholds that refresh session-memory artifacts automatically within the active runtime
* Pros:
  * moves closer to reactive context-pressure management
  * more user-visible reduction of manual intervention
* Cons:
  * timing/state complexity appears immediately
  * higher risk of drift with current deterministic compact/session invariants

**A3: Background Extraction Path**

* How it works:
  * add a separate extraction/background execution path closer to cc-haha
* Pros:
  * strongest parity path
* Cons:
  * too much runtime expansion for phase 1
  * easiest way to reopen deferred agent lifecycle/coordinator complexity

**Approach B: `plugin lifecycle`**

* How it works:
  * add install metadata and per-scope enable/disable state, then teach startup/runtime loading to honor those states
* Pros:
  * makes H17 feel product-real rather than manifest-only
  * can stay mostly inside extension/startup/settings surfaces
* Cons:
  * lower direct user value than continuity work
  * quickly grows into cache/version/install/uninstall/update semantics
  * has weaker connection to the persistent cross-session memory requirement

**Approach C: `mailbox`**

* How it works:
  * add message delivery and pending inbox semantics between local agent tasks/subagents
* Pros:
  * highest visible step toward multi-agent parity
  * unlocks later coordinator/team work
* Cons:
  * largest runtime surface increase
  * depends on long-lived task objects, pending-message queues, and resumable agent lifecycle that are not currently local product seams
  * easiest path to accidentally reopen deferred H14 coordinator complexity

## Expansion Sweep

### Future evolution

* `context pressure v2` can later branch into threshold-based auto-compact, session-memory extraction, and agent-memory snapshots without changing the current compact/session contracts.
* `plugin lifecycle` can later branch into marketplace trust, version updates, and richer install UX.
* `mailbox` can later branch into coordinator synthesis, ownership transfer, and background worker orchestration.

### Related scenarios

* Any `context pressure v2` work should stay consistent with existing `sessions resume`, compact-record recovery, and memory middleware injection.
* Any `plugin lifecycle` work should stay consistent with skills/MCP/hooks startup validation.
* Any `mailbox` work should stay consistent with durable task ownership and verifier/subagent boundaries.

### Failure & edge cases

* `context pressure v2`: stale or low-quality session-memory artifacts, duplicate state between transcript and memory, invalid compact assists.
* `plugin lifecycle`: orphaned installs, enabled-but-missing plugins, scope precedence drift, partial update failures.
* `mailbox`: lost messages, duplicate delivery, unread-state drift, background task lifetime mismatches.

## Technical Approach

Recommended next-cycle phase-1 direction:

* Choose `Approach A: context pressure v2 / session-memory compaction`.
* Keep the first slice smaller than upstream:
  * include: explicit local session-memory artifact/update boundary, deterministic compact-assist integration, deterministic tests over artifact shape and recovery/continuity behavior
  * exclude: threshold-driven automatic updates, full background extraction agent, remote config, coordinator, agent mailbox, and provider-specific cache behavior
* Initial ranked order:
  1. `context pressure v2 / session-memory compaction`
  2. `plugin lifecycle`
  3. `mailbox`
* Chosen first slice inside phase 1:
  1. `A1: Deterministic Assist`
  2. `A2: Threshold-Triggered Local Updates`
  3. `A3: Background Extraction Path`

## Decision (ADR-lite)

**Context**: Stage 29 closed the MVP and moved several broad capabilities into next-cycle. The project now needs a first follow-on stage that creates concrete product value without reopening a large runtime redesign.

**Decision**: Recommend starting next-cycle phase 1 with `context pressure v2 / session-memory compaction`, not `plugin lifecycle` or `mailbox`.

Confirmed by user: yes.

Follow-up scope decision: choose `Deterministic Assist` as the first slice inside phase 1.

**Consequences**:

* Positive:
  * directly advances the persistent cross-session memory requirement
  * builds on already-strong local seams (`compact`, `sessions`, `memory`)
  * keeps next-cycle phase 1 inside a bounded infra slice rather than platform/runtime expansion
  * preserves the current deterministic compact/session contract while still opening a path toward richer session-memory behavior later
* Trade-offs:
  * the first slice stays smaller than cc-haha's background session-memory system
  * threshold/reactive behavior is intentionally postponed
  * plugin lifecycle remains visibly incomplete for one more phase
  * mailbox/coordinator readiness remains deferred until task-backed agent lifecycle is a deliberate goal

## Implementation Plan (small PRs)

* PR1: add session-memory artifact schema/boundary and fixture-level contract tests
* PR2: integrate deterministic compact-assist consumption into compact/resume path with regression coverage
* PR3: document deferred threshold/background follow-up and harden edge-case tests around stale/empty/invalid artifacts

## Checkpoint: Sub-stage 1 Artifact Boundary

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added a strict `session_memory` artifact boundary under `coding_deepgent.sessions`.
- Allowed state snapshots to roundtrip a valid session-memory artifact while ignoring invalid artifacts.
- Added an explicit CLI update seam via `sessions resume --session-memory ...` so a resumed run can persist deterministic session memory without adding a background runtime.

Verification:
- `pytest -q coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py`
- `ruff check coding-deepgent/src/coding_deepgent/sessions/session_memory.py coding-deepgent/src/coding_deepgent/runtime/state.py coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py coding-deepgent/src/coding_deepgent/sessions/__init__.py coding-deepgent/src/coding_deepgent/cli.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py`
- `mypy coding-deepgent/src/coding_deepgent/sessions/session_memory.py coding-deepgent/src/coding_deepgent/runtime/state.py coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py coding-deepgent/src/coding_deepgent/sessions/__init__.py coding-deepgent/src/coding_deepgent/cli.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemoryUtils.ts`
  - `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
- Aligned:
  - session memory is treated as an explicit artifact with its own boundary, not as ad hoc prompt text.
- Deferred:
  - threshold-driven updates
  - background extraction runtime
- Do-not-copy:
  - remote-config and background-session machinery in the first slice

LangChain architecture:
- Primitive used:
  - strict Pydantic artifact model plus existing session state snapshot seam
- Why no heavier abstraction:
  - the first slice only needed a persisted bounded artifact and explicit CLI update path

Boundary findings:
- New issue:
  - compact/resume paths still do not consume the artifact yet
- Impact on next stage:
  - sub-stage 2 remains valid and should integrate the artifact into recovery/resume and generated compaction only

Decision:
- continue

Reason:
- The artifact boundary is stable, tested, and small. The next sub-stage still holds without requiring a plan rewrite.

## Checkpoint: Sub-stage 2 Resume And Compact Assist Integration

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Recovery briefs and resume context now render `session_memory` when present.
- Generated compact summary requests now consume a current session-memory artifact as a bounded assist.
- Added regressions proving the CLI path can persist session memory and that generated compaction receives the assist text only through the intended seam.

Verification:
- `pytest -q coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_compact_summarizer.py`
- `ruff check coding-deepgent/src/coding_deepgent/sessions/resume.py coding-deepgent/src/coding_deepgent/compact/summarizer.py coding-deepgent/src/coding_deepgent/cli_service.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_compact_summarizer.py`
- `mypy coding-deepgent/src/coding_deepgent/sessions/resume.py coding-deepgent/src/coding_deepgent/compact/summarizer.py coding-deepgent/src/coding_deepgent/cli_service.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_compact_summarizer.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
  - `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
- Aligned:
  - session memory now influences compaction continuity rather than living only as inert state
- Deferred:
  - automatic thresholds and reactive refresh
- Do-not-copy:
  - background extraction side-agent and remote-growthbook wiring in this slice

LangChain architecture:
- Primitive used:
  - existing recovery brief and compact-summary request builders with one extra bounded assist input
- Why no heavier abstraction:
  - the product benefit came from consuming the artifact at two deterministic seams, not from a new middleware/runtime layer

Boundary findings:
- New issue:
  - stale artifacts still need an explicit policy so generated compaction does not over-trust them
- Impact on next stage:
  - sub-stage 3 should harden stale/empty/invalid artifact policy and update contracts

Decision:
- continue

Reason:
- Integration stayed small and passed focused validation. The remaining work is hardening/documentation, not a plan change.

## Checkpoint: Sub-stage 3 Edge Hardening And Contracts

State:
- terminal

Verdict:
- APPROVE

Implemented:
- Hardened stale-session-memory policy so generated compact summary ignores stale artifacts while recovery briefs still surface them as `[stale]`.
- Added negative-path regressions for blank CLI session-memory input and stale-assist suppression.
- Updated the runtime context and compaction contract doc to include the new session-memory CLI/state/assist rules.

Verification:
- `pytest -q coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_compact_summarizer.py`
- `ruff check coding-deepgent/src/coding_deepgent/sessions/session_memory.py coding-deepgent/src/coding_deepgent/sessions/resume.py coding-deepgent/src/coding_deepgent/compact/summarizer.py coding-deepgent/src/coding_deepgent/cli_service.py coding-deepgent/src/coding_deepgent/cli.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_compact_summarizer.py`
- `mypy coding-deepgent/src/coding_deepgent/sessions/session_memory.py coding-deepgent/src/coding_deepgent/sessions/resume.py coding-deepgent/src/coding_deepgent/compact/summarizer.py coding-deepgent/src/coding_deepgent/cli_service.py coding-deepgent/src/coding_deepgent/cli.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_compact_summarizer.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemoryUtils.ts`
  - `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
- Aligned:
  - stale/current distinction is now explicit at the local artifact boundary
  - compaction assistance stays bounded and continuity-oriented
- Deferred:
  - threshold scheduling
  - extraction wait/runtime lifecycle
- Do-not-copy:
  - background extraction waiting, remote config initialization, and broader automation

LangChain architecture:
- Primitive used:
  - strict state artifact plus existing recovery/summary builders and contract tests
- Why no heavier abstraction:
  - the slice is complete without new middleware, stores, or child-agent orchestration

Boundary findings:
- New issue:
  - none that require another prerequisite stage for this slice
- Impact on next stage:
  - later `Threshold-Triggered Local Updates` can build on the same artifact shape without changing the persisted boundary

Decision:
- terminal

Reason:
- The chosen Deterministic Assist slice is implemented, documented, and validated. The next planned work is a new stage, not a continuation of this one.

## Technical Notes

* Trellis context: `.trellis/workflow.md`, `.trellis/project-handoff.md`
* Canonical dashboard: `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
* Relevant prior stages:
  * `.trellis/tasks/archive/2026-04/04-15-stage-23-context-pressure-and-session-continuity-closeout/prd.md`
  * `.trellis/tasks/archive/2026-04/04-15-stage-24-scoped-memory-closeout/prd.md`
  * `.trellis/tasks/archive/2026-04/04-15-stage-27-local-extension-platform-closeout/prd.md`
  * `.trellis/tasks/archive/2026-04/04-15-stage-29-deferred-boundary-adr-mvp-release-checklist/prd.md`
* Current product seams:
  * `coding-deepgent/src/coding_deepgent/compact/`
  * `coding-deepgent/src/coding_deepgent/memory/`
  * `coding-deepgent/src/coding_deepgent/sessions/`
  * `coding-deepgent/src/coding_deepgent/plugins/`
  * `coding-deepgent/src/coding_deepgent/tasks/`
  * `coding-deepgent/src/coding_deepgent/subagents/`
* Current repo files inspected:
  * `coding-deepgent/src/coding_deepgent/compact/artifacts.py`
  * `coding-deepgent/src/coding_deepgent/compact/summarizer.py`
  * `coding-deepgent/src/coding_deepgent/memory/tools.py`
  * `coding-deepgent/src/coding_deepgent/memory/policy.py`
  * `coding-deepgent/src/coding_deepgent/memory/middleware.py`
  * `coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py`
  * `coding-deepgent/src/coding_deepgent/sessions/service.py`
  * `coding-deepgent/src/coding_deepgent/plugins/schemas.py`
  * `coding-deepgent/src/coding_deepgent/plugins/loader.py`
  * `coding-deepgent/src/coding_deepgent/plugins/registry.py`
  * `coding-deepgent/src/coding_deepgent/extensions_service.py`
  * `coding-deepgent/src/coding_deepgent/tasks/store.py`
  * `coding-deepgent/src/coding_deepgent/tasks/tools.py`
  * `coding-deepgent/src/coding_deepgent/subagents/tools.py`
* cc-haha files inspected:
  * `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
  * `/root/claude-code-haha/src/services/SessionMemory/sessionMemoryUtils.ts`
  * `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
  * `/root/claude-code-haha/src/tools/AgentTool/agentMemorySnapshot.ts`
  * `/root/claude-code-haha/src/utils/plugins/installedPluginsManager.ts`
  * `/root/claude-code-haha/src/services/plugins/pluginOperations.ts`
  * `/root/claude-code-haha/src/utils/plugins/pluginIdentifier.ts`
  * `/root/claude-code-haha/src/utils/plugins/pluginLoader.ts`
  * `/root/claude-code-haha/src/utils/teammateMailbox.ts`
  * `/root/claude-code-haha/src/tools/SendMessageTool/SendMessageTool.ts`
  * `/root/claude-code-haha/src/tasks/LocalAgentTask/LocalAgentTask.tsx`
  * `/root/claude-code-haha/src/coordinator/coordinatorMode.ts`
