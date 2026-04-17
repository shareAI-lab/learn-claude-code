# L4-b: H01 tool-use/result pairing and failure tests

## Goal

Implement H01-#5: tests and small hardening for tool_use/tool_result pairing and protocol-correct failure behavior.

## Requirements

* Add focused tests for unknown tool, schema failure, permission denial, hook block, and tool exception results.
* Verify tool_use/tool_result pairing remains valid through projection, compact, and failure paths.
* Prefer synthetic bounded model-consumable errors over broken protocol state.

## Acceptance Criteria

* [x] Protocol-correct errors are returned for common tool failure classes.
* [x] Pairing tests cover projected/dynamic tool surfaces.
* [x] Existing runtime pressure and tool middleware tests remain green.

## Dependencies

* Depends on `L2-c`.
* Depends on `L3-c`.

## Context Sources

* `.trellis/plans/coding-deepgent-h01-tool-module-alignment-plan.md`
* `.trellis/spec/backend/tool-capability-contracts.md`
* `.trellis/spec/backend/tool-result-storage-contracts.md`

## Out of Scope

* Streaming fallback repair.
* Full custom tool execution engine.
