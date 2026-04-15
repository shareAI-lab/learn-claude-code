# brainstorm: Stage 16 Compact Transcript Pruning Semantics

## Goal

Define the pruning semantics for compacted transcripts before implementation, so future compact work can reduce replayed history without losing auditability, recovery correctness, or transcript integrity.

## What I already know

* Stage 15A is done:
  - append-only `compact` transcript records exist
  - compact records are loaded separately from `history`
  - compacted continuation message indexes remain correct
* Stage 15B is done:
  - recovery brief displays recent compact summaries
* Stage 15C is done:
  - resume continuation now prefers latest compact summary + preserved tail when compact records exist
* Current local behavior is still non-destructive:
  - no transcript deletion
  - no transcript pruning
  - no transcript rewrite
* cc-haha source already has more advanced transcript semantics:
  - compact-boundary-aware loading
  - preserved-segment relinking
  - pre-boundary metadata recovery
  - selective pruning before the latest compact boundary
  - separate snip-removal semantics for middle-range deletions
* LangChain short-term memory docs support trimming/deleting/summarizing messages, but those mechanisms persistently alter state and are not equivalent to our current append-only transcript ledger.

## Assumptions (temporary)

* The next compact milestone should still preserve auditability.
* Transcript semantics should remain recoverable from JSONL without requiring provider-specific runtime state.
* We should avoid immediately adopting cc-haha's most aggressive pruning/relinking logic without narrowing our local product need first.

## Open Questions

* Which pruning model should become the next product contract?

## Requirements (evolving)

* Define what must remain append-only.
* Define what may be pruned or skipped at load time.
* Define what compact metadata must stay auditable.
* Define exact recovery invariants for:
  - resume display
  - resume continuation
  - message ordering
  - tool-use/tool-result integrity
* Define whether pruning should be:
  - virtual at load time only
  - recorded via tombstones/markers
  - physically destructive

## Acceptance Criteria (evolving)

* [ ] A chosen pruning model is explicit.
* [ ] Recovery invariants are written in testable terms.
* [ ] The next implementation stage can be scoped without ambiguity.

## Definition of Done (team quality bar)

* Decision captured with trade-offs
* Follow-on implementation scope is explicit
* Out-of-scope risks are named

## Out of Scope (explicit)

* Implementing pruning logic in this brainstorm task
* Auto-compact
* Prompt-too-long retry
* Provider-specific cache/runtime behavior

## Technical Notes

* Task dir: `.trellis/tasks/04-14-stage-16-compact-transcript-pruning-semantics`
* Local files inspected:
  - `coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py`
  - `coding-deepgent/src/coding_deepgent/sessions/service.py`
  - `coding-deepgent/src/coding_deepgent/cli_service.py`
  - `coding-deepgent/src/coding_deepgent/compact/artifacts.py`
  - `.trellis/spec/backend/runtime-context-compaction-contracts.md`
* cc-haha files inspected:
  - `/root/claude-code-haha/src/utils/sessionStorage.ts`
  - `/root/claude-code-haha/src/utils/messages.ts`
  - `/root/claude-code-haha/src/services/compact/compact.ts`
* Key cc-haha observations:
  - compact boundary is not just display metadata; loader uses it to skip old transcript
  - preserved tail keeps original parent links and is relinked in memory
  - pre-boundary metadata may need separate recovery
  - pruning is bounded by “latest compact boundary”, not arbitrary deletion

## Research Notes

### What cc-haha effectively does

* Treats compact boundary as transcript semantics, not only a UI hint.
* Preserves a recent tail after compaction.
* Lets loader recover metadata from pre-boundary bytes even when older transcript is skipped.
* Uses relinking/pruning logic to keep resumed continuation coherent without replaying the full pre-compact transcript.

### Constraints from our project

* We already have append-only JSONL transcript records and compact records.
* We do not yet have parentUuid-style transcript chain semantics.
* Our current resume logic is simpler: `LoadedSession.history` is plain ordered user/assistant messages.
* We already have a non-destructive compact-aware continuation selector.
* We need to preserve:
  - auditability
  - deterministic loading
  - simple tests
  - no premature custom runtime explosion

### Feasible approaches here

**Approach A: Virtual pruning at load time** (Recommended)

* How it works:
  - Keep transcript fully append-only on disk.
  - `load_session()` optionally derives a pruned/selected history view from latest compact record.
  - Raw full transcript remains available for audit/debug paths.
* Pros:
  - safest
  - preserves auditability
  - minimal storage risk
  - aligns with current non-destructive direction
* Cons:
  - transcript file keeps growing
  - load path becomes smarter

**Approach B: Append-only tombstones / prune markers**

* How it works:
  - Add explicit “pruned range” or “superseded before boundary” records.
  - Loader respects markers and skips older segments.
  - Raw lines remain in JSONL, but semantic visibility is narrowed by markers.
* Pros:
  - still auditable
  - semantics become explicit in transcript
  - easier future evolution toward snip-like behavior
* Cons:
  - more record types
  - more loader complexity
  - more chances to get invariants wrong

**Approach C: Physical destructive pruning**

* How it works:
  - Rewrite the JSONL and remove old lines after compaction.
* Pros:
  - smallest on-disk transcript
  - simplest load path after rewrite
* Cons:
  - worst auditability
  - risk of corruption
  - highest implementation risk
  - mismatched with current product direction

## Decision (ADR-lite)

**Context**: We now have compact records and compact-aware continuation selection, but not transcript pruning semantics.

**Provisional decision**: Prefer Approach A unless a stronger product reason appears.

**Consequences**:

* Resume behavior can become more compact-aware without rewriting transcript files.
* Future destructive pruning remains possible later, but only after invariants are explicit.
