# L2-b: H19 compact observability events

## Goal

Implement H19-B compact observability trio: split auto-compact events, post-auto-compact canary, and orphan tombstone event.

## Requirements

* Split proactive auto-compact observability into attempted and succeeded events with bounded metadata.
* Emit `post_autocompact_turn` canary after the first turn following compact/collapse.
* Record four canary metrics: `pre_compact_total`, `post_compact_total`, `new_turn_input`, `new_turn_output`.
* Emit `orphan_tombstoned` when projection repair replaces orphaned tool-use/result material with tombstones.
* Persist only whitelisted bounded event metadata into session evidence.

## Acceptance Criteria

* [x] Auto-compact attempted and succeeded are distinguishable in runtime events/evidence.
* [x] Canary event appears once at the correct post-compact boundary.
* [x] Orphan tombstone repair emits a bounded event with count and reason.
* [x] Existing compact/session recovery tests remain green.

## Dependencies

* Depends on `L1-b` so event sink semantics are stable.

## Context Sources

* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h19-observability-alignment-research.md`
* `.trellis/spec/backend/runtime-pressure-contracts.md`
* `.trellis/spec/backend/session-compact-contracts.md`

## Out of Scope

* Query-error events.
* API dump.
* External analytics or Perfetto.
