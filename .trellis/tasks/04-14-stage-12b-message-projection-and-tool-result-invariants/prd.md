# Stage 12B: Message Projection and Tool Result Invariants

## Goal

Add deterministic message/context projection primitives and tool-result invariants on top of the Stage 12A context payload foundation, so later context pressure management does not corrupt tool-use/tool-result semantics or silently break long-session continuity.

## What I already know

* Stage 12A is complete enough to continue:
  - a shared `context_payloads` foundation exists
  - todo and memory middleware now use the shared payload renderer
  - focused tests, ruff, and mypy passed
* The source-backed target design says H05 is currently weak:
  - no message projection layer
  - no compact boundary state
  - no micro/auto/reactive compact
  - no tool-result persistence/restore reference
  - no invariant tests around tool-use/tool-result pairing through projection/compaction
* cc-haha source treats context pressure management as runtime correctness, not just cost optimization:
  - `/root/claude-code-haha/src/query.ts`
  - `/root/claude-code-haha/src/services/compact/*`
  - `/root/claude-code-haha/src/utils/toolResultStorage.ts`
  - `/root/claude-code-haha/src/utils/messages.ts`
* This stage should not start with LLM summarization.

## Assumptions

* Stage 12B should stay deterministic and testable without live model calls.
* Projection should precede any LLM-based compaction work.
* The first concern is preserving invariants, not maximizing token savings.
* Existing `apply_tool_result_budget()` can likely be reused as one building block.

## Open Questions

* None for the initial 12B planning pass.

## Requirements

* Add a deterministic projection layer for oversized or low-priority message/context content.
* Preserve core runtime invariants:
  - tool call / tool result linkage
  - recent useful working context
  - state update correctness
  - no silent message corruption
* Keep the design LangChain/LangGraph-native:
  - no custom query runtime
  - no replacing LangChain message/state model
* Reuse the Stage 12A context payload boundary where appropriate.
* Add tests that explicitly prove projection does not break protocol assumptions.

## Acceptance Criteria

* [ ] A projection helper or small projection module exists.
* [ ] Oversized payload/tool-result handling remains deterministic.
* [ ] Tests prove tool-result / recent-window invariants.
* [ ] The stage does not introduce LLM summarization yet.
* [ ] The stage does not widen into session resume or memory policy work.

## Definition of Done

* No compact LLM calls are introduced.
* Deterministic tests cover the new projection layer.
* Existing relevant tests still pass.
* Planning docs stay aligned with the source-backed target design.

## Out of Scope

* auto-compact LLM summarization
* session memory compaction
* recovery brief
* memory quality rules
* full task/subagent context
* coordinator/team runtime

## Technical Notes

* Created task: `.trellis/tasks/04-14-stage-12b-message-projection-and-tool-result-invariants`
* Parent planning docs:
  - `.omx/plans/coding-deepgent-h01-h10-target-design.md`
  - `.omx/plans/coding-deepgent-cc-core-highlights-roadmap.md`
* This stage is the direct continuation of 12A after a `continue` checkpoint decision.

## Checkpoint: Stage 12B

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added deterministic message projection helper in `coding-deepgent/src/coding_deepgent/compact/projection.py`.
- Exported projection helper from `coding-deepgent/src/coding_deepgent/compact/__init__.py`.
- Switched `coding-deepgent/src/coding_deepgent/rendering.py::normalize_messages()` to use the projection helper.
- Added focused projection tests in `coding-deepgent/tests/test_message_projection.py`.
- Preserved existing rendering behavior for plain same-role text merges while preventing merges for structured content and metadata-bearing messages.

Verification:
- `pytest -q coding-deepgent/tests/test_message_projection.py coding-deepgent/tests/test_rendering.py coding-deepgent/tests/test_compact_budget.py coding-deepgent/tests/test_app.py`
- `ruff check coding-deepgent/src/coding_deepgent/compact/projection.py coding-deepgent/src/coding_deepgent/rendering.py coding-deepgent/src/coding_deepgent/compact/__init__.py coding-deepgent/tests/test_message_projection.py coding-deepgent/tests/test_rendering.py`
- `mypy coding-deepgent/src/coding_deepgent/compact/projection.py coding-deepgent/src/coding_deepgent/rendering.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/query.ts`
  - `/root/claude-code-haha/src/utils/messages.ts`
  - `/root/claude-code-haha/src/services/compact/microCompact.ts`
  - `/root/claude-code-haha/src/services/compact/compact.ts`
  - `/root/claude-code-haha/src/utils/toolResultStorage.ts`
- Aligned:
  - treat context pressure handling as runtime correctness, not just token trimming
  - projection preserves message/tool structure instead of flattening everything to raw strings
- Deferred:
  - compact boundary markers
  - tool-result persistence references
  - micro/auto/reactive compact
- Do-not-copy:
  - full compaction stack
  - custom query loop

LangChain architecture:
- Primitive used:
  - deterministic helper functions around existing LangChain message input shape
  - no runtime replacement
- Why no heavier abstraction:
  - 12B only needed a narrow projection seam and invariants, not a general compact subsystem.

Boundary findings:
- New issue:
  - the old `normalize_messages()` merged all same-role messages and dropped extra metadata, which is too weak for future structured context/tool-result handling.
- Impact on next stage:
  - 12C can now audit session/recovery semantics against a clearer message normalization boundary.

Decision:
- continue

Reason:
- Tests passed.
- Scope stayed inside deterministic projection.
- No blocker appeared that invalidates the next sub-stage.
