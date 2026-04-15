# Stage 12D: Memory Quality Policy

## Goal

Prevent long-term memory from becoming a dumping ground for transient task state, duplicated facts, or derivable session details.

## Concrete Benefit

* Reliability: recalled memory is less likely to mislead the agent with stale task/session state.
* Context-efficiency: bounded recall contains reusable knowledge rather than low-value noise.
* Maintainability: memory remains separate from todo/task/session recovery state.

## What I already know

* Stage 12A added a shared context payload boundary for memory/todo context.
* Stage 12B added deterministic message projection.
* Stage 12C now carries session recovery brief/evidence into resume-with-prompt.
* Current memory foundation uses:
  - `langgraph.store.memory.InMemoryStore`
  - `runtime.store`
  - `save_memory`
  - `MemoryContextMiddleware`
  - deterministic namespace/key helpers
* Current gap:
  - `save_memory` accepts any non-blank string and only relies on descriptions to discourage transient todos/current plans/task status.

## Requirements

* Add a deterministic memory quality policy before saving long-term memory.
* Reject obvious low-value memory entries:
  - transient current-session/task status
  - active todo/next-step/current-plan content
  - exact normalized duplicates in the same namespace
  - trivially short content that is not reusable knowledge
* Preserve LangChain-native memory architecture:
  - keep `runtime.store`
  - keep `@tool(..., args_schema=...)`
  - keep LangGraph Store namespace/key storage
* Keep recall bounded and deterministic.
* Add focused tests for:
  - policy acceptance/rejection
  - duplicate detection
  - `save_memory` not writing rejected memory
  - bounded recall behavior

## Acceptance Criteria

* [ ] A small memory quality policy exists and is unit-tested.
* [ ] `save_memory` uses the policy before writing to the LangGraph store.
* [ ] Duplicate and transient memory are not saved.
* [ ] Durable reusable memory still saves normally.
* [ ] Bounded recall behavior is explicitly tested.
* [ ] No background extraction or vector recall is introduced.

## Definition of Done

* Focused memory tests pass.
* Existing memory integration tests pass.
* Ruff and mypy pass on changed files.
* The stage checkpoint records verdict and next action.

## Out of Scope

* embedding/vector recall
* auto memory extraction
* session-memory side agent
* memory file editing / CLAUDE.md promotion flow
* team memory sync
* LLM-based memory review

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve reliability, context-efficiency, maintainability, and product parity.

The local runtime effect is: the model can still save useful long-term memory through LangGraph Store, but obvious transient task/session state and duplicates are rejected before they pollute future recall.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Memory review and promotion | `/root/claude-code-haha/src/skills/bundled/remember.ts` classifies memory across CLAUDE.md, CLAUDE.local.md, team memory, and auto-memory; detects duplicates, outdated entries, conflicts, and ambiguous destination | local memory should distinguish durable reusable knowledge from transient/ambiguous notes | deterministic quality gate for `save_memory` | partial | Implement static gate now; defer review/promotion UI |
| Session memory extraction | `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts` extracts notes only after thresholds and natural boundaries, using isolated forked agent context | avoid hot-path over-saving and avoid low-value memory churn | no auto extraction in 12D | defer | Needs later background/side-agent capability |
| Session memory prompt quality | `/root/claude-code-haha/src/services/SessionMemory/prompts.ts` preserves section structure, avoids note-taking leakage, keeps sections budgeted, and emphasizes current state/errors | memory content should stay structured and bounded | bounded recall plus simple quality categories | partial | Implement bounded deterministic local policy now |
| Memory command UX | `/root/claude-code-haha/src/commands/memory/memory.tsx` opens explicit memory files for human editing | human review is important for memory quality | no local file editor now | defer | Outside 12D product scope |

### Non-goals

* Do not copy cc-haha's session-memory forked extraction agent.
* Do not implement memory file editing or team memory sync.
* Do not add LLM review/classification in this stage.

### State boundary

* Long-term memory: durable reusable facts/preferences/project conventions.
* Session recovery: transcript/state/evidence/recovery brief from 12C.
* Todo/task state: active work items and status; must not be saved as long-term memory.

### Model-visible boundary

The model still sees the `save_memory` tool, but the tool should reject low-value content with an explicit result rather than silently writing it.

### LangChain boundary

Use:

* LangChain `@tool(..., args_schema=...)`
* Pydantic schema validation for shape
* LangGraph Store via `runtime.store`
* deterministic pure functions for policy decisions

Avoid:

* custom memory runtime
* background agent extraction
* vector recall
* prompt-only memory quality enforcement

## Technical Approach

Recommended minimal design:

* Add `memory/policy.py` with `evaluate_memory_quality()`.
* Keep the policy deterministic and conservative.
* Update `memory/tools.py::save_memory()` to inspect existing namespace records and reject duplicates/transient entries before writing.
* Update `memory/schemas.py` descriptions to make the model-visible quality rule clearer.
* Add/extend tests in:
  - `tests/test_memory.py`
  - `tests/test_memory_integration.py`

## Research Notes

LangChain official docs note that long-term memory is stored in LangGraph stores as JSON documents organized by namespace and key, and tools can read/write through `runtime.store`. 12D should preserve this architecture and avoid replacing it with a custom memory runtime.

Docs consulted:

* `/oss/python/langchain/long-term-memory`
* `/oss/python/concepts/memory`
* `/oss/python/langgraph/add-memory`

## Checkpoint: Stage 12D

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added `coding-deepgent/src/coding_deepgent/memory/policy.py` with deterministic `evaluate_memory_quality()`.
- Exported the policy from `coding-deepgent/src/coding_deepgent/memory/__init__.py`.
- Updated `coding-deepgent/src/coding_deepgent/memory/tools.py::save_memory()` to reject duplicate, transient task/session state, and trivially short low-value memory before writing to `runtime.store`.
- Tightened the model-visible `SaveMemoryInput.content` description to distinguish durable reusable memory from current conversation/task/recovery notes.
- Added focused unit/integration coverage for memory policy decisions, duplicate/transient rejection, rejected tool calls not writing to store, and bounded recall.

Verification:
- `pytest -q tests/test_memory.py tests/test_memory_integration.py tests/test_memory_context.py tests/test_app.py`
- `pytest -q tests/test_context_payloads.py tests/test_message_projection.py tests/test_sessions.py tests/test_cli.py tests/test_memory.py tests/test_memory_integration.py tests/test_memory_context.py tests/test_app.py`
- `ruff check src/coding_deepgent/memory/policy.py src/coding_deepgent/memory/schemas.py src/coding_deepgent/memory/tools.py src/coding_deepgent/memory/__init__.py tests/test_memory.py tests/test_memory_integration.py`
- `mypy src/coding_deepgent/memory/policy.py src/coding_deepgent/memory/schemas.py src/coding_deepgent/memory/tools.py src/coding_deepgent/memory/__init__.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/skills/bundled/remember.ts`
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
  - `/root/claude-code-haha/src/services/SessionMemory/prompts.ts`
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemoryUtils.ts`
  - `/root/claude-code-haha/src/commands/memory/memory.tsx`
- Aligned:
  - memory is treated as quality-controlled durable context, not a scratchpad.
  - duplicate/transient memory pollution is rejected before future recall.
  - memory remains separated from todo/session recovery state.
- Deferred:
  - background/session-memory extraction thresholds.
  - forked memory extraction agent.
  - memory file promotion/review UX.
  - team memory sync.

LangChain architecture:
- Primitive used:
  - LangChain tool with Pydantic args schema.
  - LangGraph Store through `runtime.store`.
  - deterministic pure policy function before `store.put`.
- Why no heavier abstraction:
  - 12D only needed a reusable quality gate; background extraction, vector indexing, or a separate memory runtime would be premature.

Boundary findings:
- New issue handled:
  - exact duplicate content previously upserted silently and still returned "Saved memory"; the tool now reports rejection before write.
- Residual risk:
  - current policy is intentionally conservative and heuristic. It rejects obvious transient phrases only; nuanced stale/conflicting memory still needs a later review/promotion workflow.
- Impact on next stage:
  - Stage 12 planned sub-stages are now complete. Later memory automation can reuse this policy but should not bypass it.

Decision:
- continue

Terminal note:
- No next Stage 12 sub-stage remains; this `continue` maps to staged-run completion rather than starting a speculative 12E.

Reason:
- Verdict is APPROVE.
- Tests, ruff, and mypy passed.
- Stage 12A-12D planned sub-stages are complete and no additional 12E prerequisite was discovered.
