# L4-c: H01 result persistence and microcompact eligibility audit

## Goal

Implement H01-#6: lightweight audit of result persistence and microcompact eligibility across tool capabilities.

## Requirements

* Review tools that opt into large-output persistence or microcompact eligibility.
* Verify opt-in metadata matches actual recoverability and safety.
* Update tests/contracts when a tool's persisted preview or microcompact behavior is ambiguous.

## Acceptance Criteria

* [x] No tool is microcompact-eligible unless old output can be safely hidden or recovered.
* [x] Large-output persistence metadata matches tool result behavior.
* [x] Tool result storage contracts reflect any new audit rule.

## Dependencies

* Depends on `L3-c`.

## Context Sources

* `.trellis/spec/backend/tool-result-storage-contracts.md`
* `.trellis/spec/backend/tool-capability-contracts.md`
* `.trellis/plans/coding-deepgent-h01-tool-module-alignment-plan.md`

## Out of Scope

* New persistence backend.
* Provider-specific cache instrumentation.
