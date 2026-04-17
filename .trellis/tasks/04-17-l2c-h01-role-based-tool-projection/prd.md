# L2-c: H01 role-based tool projection

## Goal

Implement H01-#2: role-based tool projection foundation for `main`, `child_only`, `extension`, and future `deferred` surfaces.

## Requirements

* Centralize projection logic so runtime surfaces consume metadata instead of hard-coded tool-name lists.
* Preserve distinct surfaces for main agent, child agents, verifier, and extension-provided capabilities.
* Make `child_only` behavior testable after real general child runtime exists.
* Keep future deferred ToolSearch/schema-discovery as a declared boundary, not implemented behavior.

## Acceptance Criteria

* [x] Main and child tool projections are deterministic and covered by tests.
* [x] Extension tools preserve source/trust metadata through projection.
* [x] Verifier/general child tool pools can be derived from definitions and capability metadata.
* [x] No hot-swap or deferred ToolSearch runtime is added.

## Dependencies

* Depends on `L1-c`.
* Depends on `L2-a` for validating `child_only` behavior against a real general runtime.

## Context Sources

* `.trellis/plans/coding-deepgent-h01-tool-module-alignment-plan.md`
* `.trellis/spec/backend/tool-capability-contracts.md`
* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md`

## Out of Scope

* Dynamic tool pool hot-swap.
* Parallel tool-call orchestration.
