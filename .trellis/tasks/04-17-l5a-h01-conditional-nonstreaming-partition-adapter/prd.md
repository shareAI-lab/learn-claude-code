# L5-a: H01 conditional non-streaming partition adapter

## Goal

Implement or explicitly reject H01-#4 non-streaming concurrency partition adapter based on `L4-a` research.

## Requirements

* If LangChain already provides sufficient ordering/safety guarantees, update specs and do not add code.
* If LangChain behavior is insufficient, add a thin adapter that partitions only by `ToolCapability` metadata.
* Preserve LangChain-native runtime boundaries and existing middleware.

## Acceptance Criteria

* [ ] `L4-a` research is cited.
* [ ] Either a spec-only decision is recorded or adapter tests prove ordered results and exclusive unsafe tools.
* [ ] No custom query loop or streaming tool executor is introduced.

## Dependencies

* Depends on `L4-a`.

## Context Sources

* `.trellis/plans/coding-deepgent-h01-tool-module-alignment-plan.md`
* `.trellis/spec/backend/langchain-native-guidelines.md`

## Out of Scope

* Streaming executor.
* Provider-specific cancellation semantics.
