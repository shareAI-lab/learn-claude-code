# Stage 13A: Manual Compact Boundary and Summary Artifact

## Goal

Add the first compact boundary and summary artifact primitive for `Stage 13 Context Compaction v1`, without introducing automatic compaction, live LLM summarization, or session-store deletion semantics yet.

## Concrete Benefit

* Context-efficiency: older conversation can be represented by an explicit summary artifact rather than an unbounded raw transcript.
* Reliability: compaction has a model-visible boundary and preserves recent messages without silently splitting tool-use/tool-result pairs.
* Maintainability: later manual CLI, auto-compact, and session-memory compact paths can reuse one deterministic artifact boundary.
* Testability: compaction correctness can be tested without live model calls.

## What I already know

* Stage 12A added shared context payload rendering.
* Stage 12B added deterministic message projection and prevented metadata/structured message corruption.
* Stage 12C added recovery brief continuation context.
* Stage 12D added memory quality policy.
* Existing compact code has:
  - `compact.budget.apply_tool_result_budget()`
  - `compact.projection.project_messages()`
* Current gap:
  - no compact boundary marker
  - no summary artifact message shape
  - no deterministic compacted-history builder
  - no tool-use/tool-result preservation when selecting a recent tail

## Requirements

* Add a deterministic manual compaction artifact builder.
* Produce ordered post-compact messages:
  - compact boundary marker
  - compact summary message
  - preserved recent messages
* Preserve recent messages verbatim.
* Avoid merging the summary artifact with adjacent user messages during projection.
* Do not mutate input messages.
* If preserved recent messages include tool results, expand the preserved window backward to include matching tool-use messages when present.
* Add tests for:
  - boundary + summary artifact order
  - summary formatting
  - non-mutating behavior
  - projection does not merge compact summary into adjacent user message
  - tool-use/tool-result pair preservation

## Acceptance Criteria

* [ ] A compact artifact helper exists under `coding_deepgent.compact`.
* [ ] The helper is deterministic and has no live model dependency.
* [ ] Summary artifacts are model-visible but structurally protected from accidental message merging.
* [ ] Recent-window tool-use/tool-result pairing is preserved.
* [ ] Focused compact tests pass.
* [ ] Existing projection/app smoke tests still pass.

## Definition of Done

* Focused compact tests are added/updated.
* No automatic compact middleware is introduced.
* No session store rewrite/delete semantics are introduced.
* No LLM summarization call is introduced.
* Ruff and mypy pass on changed files.

## Out of Scope

* auto-compact thresholds
* reactive prompt-too-long retry
* forked summarizer / live LLM summary generation
* session-memory-assisted compact
* persisted compact transcript pruning
* tool-result file persistence
* post-compact file/skill/tool restoration attachments

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve context-efficiency, reliability, maintainability, testability, and long-session continuity.

The local runtime effect is: compacted history has an explicit boundary + summary artifact and a preserved recent tail, so later compaction paths can reduce context without corrupting continuation semantics.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Boundary + summary ordering | `/root/claude-code-haha/src/services/compact/compact.ts::buildPostCompactMessages()` orders boundary marker, summary messages, preserved messages, attachments, hook results | local compacted history has a stable continuation boundary | boundary + summary + preserved tail | partial | Implement boundary/summary/tail only |
| Summary prompt/output cleanup | `/root/claude-code-haha/src/services/compact/prompt.ts::formatCompactSummary()` strips `<analysis>` and unwraps `<summary>` | compact summary artifact is cleaner and avoids scratchpad leakage | deterministic `format_compact_summary()` | align | Implement now |
| Recent tail preservation | `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts::calculateMessagesToKeepIndex()` expands kept tail and avoids splitting API invariants | local tail selection does not orphan recent tool results | deterministic tail selector over dict messages | partial | Implement tool_use/tool_result pair protection now |
| Full manual compact flow | `/root/claude-code-haha/src/services/compact/compact.ts::compactConversation()` runs hooks, forked/streaming summary, restores files/tools/skills, logs usage, writes transcript metadata | full manual compact product flow | none in 13A | defer | Needs later runtime/CLI integration |
| Tool-result persistence | `/root/claude-code-haha/src/utils/toolResultStorage.ts` persists oversized tool results and leaves references | avoid losing large tool outputs | existing deterministic budget only | defer | Separate stage after artifact boundary |

### Non-goals

* Do not copy the full cc-haha query/runtime loop.
* Do not run pre/post compact hooks yet.
* Do not implement prompt-too-long retry.
* Do not persist or delete transcript segments yet.
* Do not add auto-compact.

### State boundary

* Compact artifact: model-visible continuation context.
* Runtime session state: todos/recovery/memory state remain separate.
* Transcript persistence: unchanged in 13A.

### Model-visible boundary

The model sees:

* a compact boundary message
* a compact summary message
* preserved recent messages

The model should not see:

* `<analysis>` scratchpad output from the summarizer
* internal artifact metadata as separate user requests
* duplicate old compact boundaries from summarized history

### LangChain Boundary

Use:

* normal LangChain message dictionaries
* structured text content blocks to avoid accidental projection merges
* deterministic pure helpers under `compact/`

Avoid:

* custom query runtime
* replacing LangChain message/state model
* automatic middleware before the artifact semantics are proven
* LLM summarization until boundary tests pass

## LangChain Docs Consulted

* `/oss/python/langchain/short-term-memory`
* `/oss/python/langchain/context-engineering`
* `/oss/python/langgraph/add-memory`

Relevant local decision:

LangChain supports trim/delete/summarize strategies for short-term memory; summarization is lifecycle context that can persistently replace old messages while keeping recent messages. 13A only implements the deterministic artifact boundary needed before introducing that lifecycle behavior.

## Technical Approach

Recommended minimal design:

* Add `compact/artifacts.py`.
* Export the helper from `compact/__init__.py`.
* Add `tests/test_compact_artifacts.py`.
* Keep the helper pure:
  - input: message dictionaries, manually supplied summary text, `keep_last`
  - output: compact artifact metadata + post-compact messages
* Use structured text blocks for boundary/summary content so `project_messages()` preserves the artifact boundary.

## Research Notes

Key cc-haha source inspected:

* `/root/claude-code-haha/src/services/compact/compact.ts`
* `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
* `/root/claude-code-haha/src/services/compact/prompt.ts`
* `/root/claude-code-haha/src/services/compact/microCompact.ts`
* `/root/claude-code-haha/src/utils/toolResultStorage.ts`

## Checkpoint: Stage 13A

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added `coding-deepgent/src/coding_deepgent/compact/artifacts.py` with:
  - `CompactArtifact`
  - `compact_messages_with_summary()`
  - compact boundary and summary message builders
  - `format_compact_summary()`
  - compact artifact detection
- Exported compact artifact helpers from `coding-deepgent/src/coding_deepgent/compact/__init__.py`.
- Added `coding-deepgent/tests/test_compact_artifacts.py` covering:
  - boundary + summary + preserved-tail order
  - `<analysis>` stripping and `<summary>` unwrapping
  - non-mutating behavior
  - projection-preserved structured summary artifacts
  - tool-use/tool-result pair preservation when selecting the recent tail
  - invalid input rejection

Verification:
- `pytest -q tests/test_compact_artifacts.py tests/test_message_projection.py tests/test_compact_budget.py tests/test_app.py`
- `pytest -q tests/test_context_payloads.py tests/test_message_projection.py tests/test_compact_artifacts.py tests/test_compact_budget.py tests/test_sessions.py tests/test_cli.py tests/test_memory.py tests/test_memory_integration.py tests/test_memory_context.py tests/test_app.py`
- `ruff check src/coding_deepgent/compact/artifacts.py src/coding_deepgent/compact/__init__.py tests/test_compact_artifacts.py`
- `mypy src/coding_deepgent/compact/artifacts.py src/coding_deepgent/compact/__init__.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/services/compact/compact.ts`
  - `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
  - `/root/claude-code-haha/src/services/compact/prompt.ts`
  - `/root/claude-code-haha/src/services/compact/microCompact.ts`
  - `/root/claude-code-haha/src/utils/toolResultStorage.ts`
- Aligned:
  - post-compact message order starts with boundary and summary before preserved recent messages.
  - compact summary formatting strips summarizer scratchpad and unwraps summary content.
  - recent tail selection preserves tool-use/tool-result pairs when the kept tail includes a result.
- Deferred:
  - full manual compact flow with hooks and model summarization.
  - auto-compact and reactive prompt-too-long recovery.
  - session-memory-assisted compact.
  - persisted transcript pruning and tool-result file references.

LangChain architecture:
- Primitive used:
  - normal LangChain message dictionaries.
  - structured text content blocks for artifact messages so Stage 12B projection does not merge the summary into adjacent user messages.
  - pure deterministic helper functions under `compact/`.
- Why no heavier abstraction:
  - 13A only needed the artifact boundary; runtime middleware, CLI mutation, and LLM summary calls would widen the stage before invariants were proven.

Boundary findings:
- New issue handled:
  - plain `role/content` compact summary messages would be merged into adjacent user messages by the Stage 12B projector; structured text blocks avoid that.
- Residual risk:
  - 13A does not persist compacted history or invoke a summarizer; it only builds the artifact shape that later runtime/CLI work can use.
- Impact on next stage:
  - 13B should wire this artifact into an explicit manual compact entry point, still avoiding auto-compact.

Decision:
- continue

Reason:
- Tests, ruff, and mypy passed.
- Scope stayed inside deterministic compact artifact behavior.
- The next sub-stage remains valid if constrained to explicit manual compact wiring rather than automatic compaction.
