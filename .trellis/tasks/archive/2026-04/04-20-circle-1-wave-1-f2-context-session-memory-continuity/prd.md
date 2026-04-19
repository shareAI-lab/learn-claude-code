# Circle 1 Wave 1 F2 Context-Session-Memory Continuity

## Goal

Strengthen context, compact, session, and memory continuity so
`coding-deepgent` can survive long single-day coding tasks without losing the
main working thread after multiple rounds of pressure, compaction, resume, and
continued editing.

## What I already know

* Circle 1 uses workflow-first acceptance, and this family primarily serves:
  - Workflow A: repository takeover and sustained coding
  - Workflow B: single-day long-task continuity
* Current local baseline already includes:
  - staged runtime pressure pipeline in `RuntimePressureMiddleware`
  - live `snip -> microcompact -> collapse -> auto_compact`
  - collapse transcript events and load-time collapsed history replay
  - scoped session-memory artifact plus bounded assist/update policy
  - resume/recovery brief/session evidence seams
* Current local baseline is strong enough for the old MVP line, but that is not
  sufficient for Circle 1 daily-driver parity.
* Recent research already established that public `cc-haha` collapse behavior is
  richer than our current local collapse semantics.

## Assumptions (temporary)

* The next implementation slice for this family should focus first on
  continuity under long same-day work, not cross-day or team-runtime behavior.
* The highest-value gap is likely in the interaction between:
  - collapse/projection semantics
  - session continuity/resume
  - session-memory continuity aid quality
* This task should choose the next implementation slice, not implement all
  continuity improvements at once.

## Open Questions

* None for the decomposition pass.

## Acceptance Targets

* After this planning pass, the most important Circle 1 continuity gap is
  explicit rather than hidden inside broad “context system” language.
* The task identifies which parts of the current baseline are already strong
  enough, and which parts remain only MVP-complete.
* The next implementation slice is specific enough to turn into one concrete
  code task without reopening the whole Circle 1 scope.

## Planned Features

* Re-audit current local context/session/memory continuity against the stronger
  Circle 1 standard.
* Map `cc-haha` / Claude Code continuity evidence onto current local modules.
* Choose the next implementation slice for this family.

## Planned Extensions

* Cross-day continuity
* Richer session-memory extraction/runtime
* Team-runtime continuity
* Remote / IDE / daemon continuity concerns

## Out of Scope

* Broad CLI/TUI work beyond what is needed to expose continuity semantics
* Mailbox/coordinator/team-runtime continuity
* Full extension-ecosystem lifecycle
* Provider-specific internals that do not materially improve local continuity

## Research Notes

### `cc-haha` / Claude Code evidence

Primary source points reviewed:

* `/root/claude-code-haha/src/query.ts`
* `/root/claude-code-haha/src/services/compact/grouping.ts`
* `/root/claude-code-haha/src/utils/sessionStorage.ts`
* `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
* `/root/claude-code-haha/src/services/SessionMemory/sessionMemoryUtils.ts`

High-signal source-backed findings:

* `contextCollapse.applyCollapsesIfNeeded(...)` runs before autocompact, and if
  collapse gets the context under threshold, autocompact becomes a no-op.
* Public comments describe collapse as a **read-time projection over full REPL
  history**, with summary messages living in a collapse store and
  `projectView()` replaying commits across turns.
* Prompt-too-long recovery first tries `contextCollapse.recoverFromOverflow(...)`
  to drain staged collapses before falling through to reactive compact.
* `groupMessagesByApiRound(...)` defines the safe split unit as
  **assistant API round / tool-complete round**, not arbitrary message cuts or
  coarse human-turn grouping.
* Transcript persistence and recovery code in `sessionStorage.ts` explicitly
  handles DAG-like assistant/tool-result topologies, which matters for safe
  continuity under long sessions.
* Session memory in `cc-haha` is not just a static local note: it has
  thresholds, initialization state, last summarized point, and isolated
  extraction using `runForkedAgent(...)`.

### Current local baseline

Primary local surfaces reviewed:

* `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`
* `coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py`
* `coding-deepgent/src/coding_deepgent/sessions/session_memory.py`

Current strengths:

* Runtime pressure order is already coherent and source-backed.
* Live collapse can persist transcript events and load-time collapsed history is
  replayable from raw session messages.
* Overflow drain before reactive compact already exists locally.
* Session-memory artifact is bounded, typed, and can assist compaction.
* Resume and recovery surfaces already exist and are test-covered.

Current likely parity pressure:

* Local collapse is still centered on a **live request rewrite** mental model,
  while `cc-haha` public comments point to a deeper projection/store-first
  continuity system.
* Local session-memory continuity is bounded and useful, but much simpler than
  `cc-haha`'s thresholded, isolated extraction/runtime model.
* Long-task continuity is likely limited less by raw existence of features and
  more by how coherently collapse/session-memory/resume compose under repeated
  use.

## Evaluation

### What is already strong enough

* Runtime pressure ordering
* Collapse-before-autocompact ordering
* Overflow drain before reactive compact
* Resume/continuity replay foundation
* Bounded local session-memory artifact

### What is still only MVP-complete

* collapse as a daily-driver continuity system rather than a lighter
  summarizer stage
* richer preservation of granular working context across repeated pressure
* stronger coupling between session-memory freshness and continuity after long
  local work

## Recommended Next Slice

### Recommendation: `F2a collapse-session continuity v2`

Recommended first implementation slice:

* push the local collapse/session continuity path further toward a
  **projection-first continuity system**
* improve how long-task continuity survives repeated collapse/resume cycles
* keep the implementation bounded to Circle 1 single-day continuity rather than
  jumping immediately to cross-day memory/runtime complexity

Why this slice first:

* it directly serves Workflow B
* it addresses the clearest current gap against public `cc-haha` continuity
  shape
* it improves both long-session work and resumed continuation quality
* it avoids prematurely expanding into team-runtime or full session-memory
  runtime parity

### Deferred second slice: `F2b richer session-memory runtime`

This remains important, but should follow after `F2a` unless new evidence shows
session-memory freshness is the dominant blocker.

## Decision (ADR-lite)

**Context**: The current local baseline is good enough for MVP, but Circle 1
raises the bar to long single-day task continuity. Public `cc-haha` evidence
suggests a more projection-first collapse/session continuity system than the
current local mental model, while session memory also appears richer upstream.

**Decision**: Treat the next implementation target for this family as
`F2a collapse-session continuity v2`, not “generic context improvements” and
not “session-memory runtime v2 first.”

**Consequences**:

* The next concrete implementation task should focus on continuity semantics
  under repeated collapse/resume cycles.
* Session-memory runtime can remain bounded for now, but should be revisited
  after `F2a`.
* The family now has a concrete progression path rather than one broad
  continuity bucket.

## Technical Approach

The next implementation PRD under this family should:

* define the exact continuity effect to improve
* map the target Claude Code / `cc-haha` behavior
* state what continuity semantics must match:
  - projection behavior
  - resume behavior
  - continuity after repeated pressure events
* state what may remain local for now:
  - full cross-day memory behavior
  - provider-specific internals
  - team-runtime continuity

## Technical Notes

* Parent roadmap: `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`
* Parent decomposition: `.trellis/plans/coding-deepgent-circle-1-wave-1-runtime-core-plan.md`
* Relevant historical notes:
  - `.trellis/tasks/archive/2026-04/04-16-cc-level-3-collapse-alignment/prd.md`
  - `.trellis/tasks/archive/2026-04/04-16-cc-style-collapse-store-pressure-guard/prd.md`
  - `.trellis/tasks/archive/2026-04/04-15-stage-23-context-pressure-and-session-continuity-closeout/prd.md`
