# L5-b: deferred boundary ADR refresh

## Goal

Refresh deferred-boundary documentation after H11/H12, H19, and H01 closeout tasks land.

## Requirements

* Merge H11/H12 deferred items with existing H13/H14/H21/H22 and H19 deferred items.
* Capture why background agents, mailbox, coordinator, bridge/remote/IDE, daemon/cron, Perfetto, analytics backend, and provider-specific cache/cost remain out of scope.
* Reference cc-haha source/research notes so future reopen requests are source-backed.

## Acceptance Criteria

* [x] A Trellis spec or plan ADR documents deferred boundaries with concrete reasons.
* [x] The ADR supersedes or links to the older Stage 29 ADR.
* [x] Future agents can tell what is intentionally deferred versus missing by accident.

## Dependencies

* Depends on `L3-a`.
* Depends on `L3-b`.
* Depends on Layer 4 H01 closeout tasks.

## Context Sources

* `.trellis/tasks/archive/2026-04/04-15-stage-29-deferred-boundary-adr-mvp-release-checklist/prd.md`
* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md`
* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h19-observability-alignment-research.md`

## Out of Scope

* Implementing deferred runtime features.
