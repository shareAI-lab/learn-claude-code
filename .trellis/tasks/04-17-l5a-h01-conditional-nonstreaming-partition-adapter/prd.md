# L5-a: H01 conditional non-streaming partition adapter

## Goal

Implement or explicitly reject H01-#4 non-streaming concurrency partition adapter based on `L4-a` research.

## Requirements

* If LangChain already provides sufficient ordering/safety guarantees, update specs and do not add code.
* If LangChain behavior is insufficient, add a thin adapter that partitions only by `ToolCapability` metadata.
* Preserve LangChain-native runtime boundaries and existing middleware.

## Acceptance Criteria

* [x] `L4-a` research is cited.
* [x] A spec-only rejection decision is recorded because `L4-b` / `L4-c` did not expose a concrete capability-aware partitioning failure.
* [x] No custom query loop or streaming tool executor is introduced.

## Resolution (2026-04-19)

* Cited source: `.trellis/tasks/04-17-l4a-h01-langchain-parallel-tool-call-research/research.md`
* `L4-a` established that LangChain `ToolNode` already provides non-streaming parallel tool execution with preserved output ordering.
* `L4-b` pairing/failure tests and `L4-c` persistence audit did not expose a repo-level failure that requires capability-aware partitioning.
* Decision: explicitly reject implementing a local partition adapter for now and close this task as a spec-only follow-up.

## Verification

* `L4-a` research, `L4-b` tests, and `L4-c` audit all remain consistent with keeping runtime execution LangChain-native.
* No product runtime code changes were required for this task.

## Dependencies

* Depends on `L4-a`.

## Context Sources

* `.trellis/plans/coding-deepgent-h01-tool-module-alignment-plan.md`
* `.trellis/spec/backend/langchain-native-guidelines.md`

## Out of Scope

* Streaming executor.
* Provider-specific cancellation semantics.
