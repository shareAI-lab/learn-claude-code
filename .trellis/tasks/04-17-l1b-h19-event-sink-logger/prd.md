# L1-b: H19 event sink and logger

## Goal

Implement H19-A: queued-until-sink runtime event emission plus an agent-scoped logger helper.

## Requirements

* Add buffered event behavior so events emitted before a concrete sink is attached are not silently lost.
* Preserve a test/null sink for deterministic tests.
* Add a small logger helper or convention that scopes debug output by agent/runtime component.
* Keep the implementation local and synchronous/bounded; do not add an analytics backend.

## Acceptance Criteria

* [x] Events emitted before sink attachment are drained to the attached sink in order.
* [x] Sink attachment is idempotent or explicitly rejects unsafe duplicate attachment.
* [x] Existing runtime event/evidence tests still pass.
* [x] Agent-scoped logger behavior is covered by focused tests or a documented convention.

## Dependencies

* None.

## Context Sources

* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h19-observability-alignment-research.md`
* `.trellis/spec/backend/logging-guidelines.md`
* `.trellis/spec/backend/runtime-pressure-contracts.md`

## Out of Scope

* External analytics backend.
* Perfetto tracing.
* Streaming/TTFT observability.
