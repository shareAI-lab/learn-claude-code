# L3-c: H01 dynamic tool pool foundation

## Goal

Implement H01-#3: dynamic tool pool projection and validation foundation without hot-swap runtime.

## Requirements

* Represent tool pool selection as an explicit projection result, not an implicit global registry snapshot.
* Validate that enabled/disabled, role, source, trust, and exposure metadata produce correct visible tool surfaces.
* Preserve current startup/runtime simplicity; do not add live hot-swap.
* Leave ToolSearch/deferred schema discovery as future behavior.

## Acceptance Criteria

* [x] Tool pool projection can be tested independently from agent startup.
* [x] Invalid projection states fail deterministically with bounded errors.
* [x] Main, child, and extension surfaces remain stable after projection refactor.
* [x] H01 follow-up tests can build on this projection seam.

## Dependencies

* Depends on `L2-c`.

## Context Sources

* `.trellis/plans/coding-deepgent-h01-tool-module-alignment-plan.md`
* `.trellis/spec/backend/tool-capability-contracts.md`

## Out of Scope

* Hot-swapping tools mid-run.
* ToolSearch.
* Streaming tool execution.
