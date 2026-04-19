# Circle 1 Wave 1 F2a Collapse-Session Continuity v2

## Goal

Improve long single-day continuity by making local collapse/session behavior
more continuity-preserving and less coarse, so repeated collapse/resume cycles
retain the working thread more like a projection system and less like a blunt
prefix summary rewrite.

## What I already know

* Parent family `F2` already concluded that the first high-value continuity
  slice should target collapse/session continuity rather than richer
  session-memory runtime.
* Public `cc-haha` evidence shows:
  - collapse is described as a read-time projection over full history
  - summary messages live in a collapse store
  - prompt-too-long recovery drains staged collapses before reactive compact
  - safe grouping logic elsewhere in compaction uses **API-round boundaries**
    instead of arbitrary message cuts or coarse human-turn grouping
* Current local runtime collapse still builds its persisted collapse coverage as
  a **prefix** of the current projected message list:
  - `collapse_live_messages_with_result()` collapses `clean_messages[:keep_start]`
  - `_append_collapse_record()` uses `_covered_projection_ids_for_prefix(...)`
* Current local baseline already has:
  - collapse transcript events
  - collapsed history replay on load/resume
  - overflow drain before reactive compact
  - continuity-facing compression view infrastructure

## Assumptions (temporary)

* The highest-value next improvement is not “more summaries,” but
  **better span selection semantics** for what gets collapsed.
* If collapse spans better preserve task/assistant/tool-result structure, long
  same-day continuity should improve even before deeper session-memory work.

## Open Questions

* None for the decomposition pass.

## Acceptance Targets

* The next implementation slice is narrowed to one concrete continuity
  improvement, not a broad context-system rewrite.
* The chosen slice directly improves Workflow B:
  single-day long-task continuity under repeated collapse/resume cycles.
* The slice stays inside Circle 1 and does not sprawl into cross-day memory or
  team-runtime behavior.

## Planned Features

* Reframe local collapse coverage from a prefix-only model toward a more
  continuity-preserving span model.
* Prefer spans that preserve assistant/tool-result structure rather than
  arbitrary coarse prefix truncation.
* Add tests proving the new collapse coverage semantics preserve better
  continuity under realistic coding-agent message topologies.

## Planned Extensions

* richer session-memory extraction/runtime
* cross-day continuity
* stronger continuity across team-runtime/mailbox/coordinator features

## Out of Scope

* complete `cc-haha` contextCollapse subsystem parity
* cross-day memory productization
* mailbox/coordinator/team-runtime continuity
* broad CLI/TUI changes not required to validate the runtime semantics

## Source Notes

### `cc-haha` evidence

Reviewed:

* `/root/claude-code-haha/src/query.ts`
* `/root/claude-code-haha/src/services/compact/grouping.ts`
* `/root/claude-code-haha/src/utils/sessionStorage.ts`

High-signal facts:

* `query.ts` comments describe collapse as read-time projection over full REPL
  history, with summary messages outside the REPL array and replay across turns.
* `query.ts` tries collapse drain before reactive compact on prompt-too-long.
* `groupMessagesByApiRound(...)` explicitly treats **assistant API-round
  boundaries** as the safe split point.
* `sessionStorage.ts` explains transcript topology can be DAG-like, especially
  around parallel tool use / tool results, which means arbitrary message cuts
  are continuity-risky.

### Local evidence

Reviewed:

* `coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`
* `coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py`
* `coding-deepgent/src/coding_deepgent/compact/projection.py`

High-signal facts:

* local collapse chooses `collapsed_source = clean_messages[:keep_start]`
* persisted collapse coverage is derived by `_covered_projection_ids_for_prefix(...)`
* local replay and compression view already support non-destructive
  collapse-event projections over raw history
* local projection layer already knows about tool-use/tool-result repair and
  pairing-sensitive message handling

## Current Gap

The main local continuity gap is:

* collapse persistence/replay exists,
* but the **unit of what gets collapsed** is still too coarse and too tied to
  a prefix model.

This means the local system is more likely to summarize away a large front chunk
of history without respecting the more stable work-unit boundaries implied by:

* assistant API rounds
* tool-use / tool-result closure
* coding-agent message topology

## Recommended Implementation Slice

### Recommendation: `F2a1 API-round-aware collapse spans`

Make the first implementation slice:

* replace or refine prefix-only collapse coverage so persisted collapse spans
  align better with continuity-preserving work units
* use a grouping model that better respects assistant/tool-result boundaries
* keep replay/resume infrastructure unchanged where possible

Why this first:

* it directly targets continuity quality
* it is smaller and more source-backed than “do full collapse subsystem parity”
* it should improve repeated collapse/resume behavior without reopening the
  entire memory/runtime family

## Decision (ADR-lite)

**Context**: Circle 1 raises the continuity bar from MVP-safe to daily-driver
usable. Public `cc-haha` evidence suggests that collapse should preserve
granular context better than a blunt prefix summary model. Local collapse
already has durable records and replay, but its span selection remains coarse.

**Decision**: Define the next implementation slice as `F2a1 API-round-aware
collapse spans`.

**Consequences**:

* the next concrete implementation task should focus on span selection and
  coverage semantics
* session-memory runtime can remain secondary for now
* the slice remains bounded and testable inside Circle 1

## Technical Approach

The next implementation PRD should decide:

* what local grouping primitive to use for collapse span selection
* how to preserve tool-call/tool-result structure while collapsing older
  context
* how persisted `covered_message_ids` should be derived from those spans
* which current tests to extend:
  - runtime pressure
  - sessions/compression replay
  - selected continuation history

## Technical Notes

* Parent task:
  `.trellis/tasks/04-20-circle-1-wave-1-f2-context-session-memory-continuity/`
* Parent roadmap:
  `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`
