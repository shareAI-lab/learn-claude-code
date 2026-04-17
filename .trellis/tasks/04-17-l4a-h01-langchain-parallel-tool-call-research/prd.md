# L4-a: H01 LangChain parallel tool-call research

## Goal

Run a research-only spike to determine whether LangChain's current tool execution behavior is sufficient for non-streaming parallel tool calls.

## Requirements

* Inspect official LangChain/LangGraph behavior and local usage around multiple tool calls in one model turn.
* Determine whether `ToolCapability.concurrency_safe` needs a local partition adapter.
* Record source-backed findings and a recommendation for `L5-a`.
* Do not change product code in this task.

## Acceptance Criteria

* [x] Research notes state what LangChain already guarantees.
* [x] Research notes state what local tests should prove before adding an adapter.
* [x] `L5-a` is either justified as implementation work or downgraded to spec-only.

## Dependencies

* Depends on `L2-c`.

## Context Sources

* `.trellis/plans/coding-deepgent-h01-tool-module-alignment-plan.md`
* `.trellis/spec/backend/langchain-native-guidelines.md`

## Out of Scope

* Implementing a partition adapter.
* Streaming tool execution.
