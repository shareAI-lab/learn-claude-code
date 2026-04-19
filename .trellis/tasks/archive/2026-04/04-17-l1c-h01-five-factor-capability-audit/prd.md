# L1-c: H01 five-factor capability audit

## Goal

Implement H01-#1: audit all registered model-facing capabilities against the five-factor protocol and add tests for safe metadata defaults.

## Requirements

* Verify every registered tool has explicit name, schema, permission, execution, and rendering/result metadata.
* Fill missing `ToolCapability` metadata where the current defaults are too implicit.
* Add or tighten tests around safe defaults, exposure, trust/source, large-output persistence, and microcompact eligibility.
* Do not add new orchestration behavior in this task.

## Acceptance Criteria

* [x] Builtin and extension-projected tools have deterministic capability metadata.
* [x] Unsafe or unknown tools do not default to read-only, concurrency-safe, trusted, persisted, or microcompact-eligible.
* [x] Focused `tool_system` registry/middleware tests cover the audit.
* [x] H01 plan can treat Child 1 as complete.

## Dependencies

* None.

## Context Sources

* `.trellis/plans/coding-deepgent-h01-tool-module-alignment-plan.md`
* `.trellis/spec/backend/tool-capability-contracts.md`
* `.trellis/spec/backend/langchain-native-guidelines.md`

## Out of Scope

* Role-based projection changes.
* Dynamic tool pool.
* Parallel tool-call orchestration.
