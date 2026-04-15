# brainstorm: runtime context pressure management

## Goal

Plan and implement a cc-haha-aligned runtime context pressure management upgrade for `coding-deepgent` so long-running sessions can keep working under context pressure through live runtime mechanisms, not only through explicit resume-time compact helpers. The target is to prioritize the highest-value cc context/compact behaviors and avoid spending time on tutorial-shell parity or low-value edge embellishments.

## What I already know

* The user clarified that `agents/*.py` tutorial chapters are feature previews only, not the product target.
* The user wants `coding-deepgent` to prioritize cc-haha "feature highlights" rather than continuing to accumulate edge features that are weaker product differentiators.
* For the current context/compact band, the user accepted this initial priority order:
  * tool result storage
  * microcompact
  * live auto-compact
  * post-compact restoration
  * defer session-memory compact to a later pass
* Current `coding-deepgent` already has:
  * prompt/context payload seams
  * tool-result truncation budget helper
  * compact artifact helpers
  * persisted compact transcript records
  * load-time compacted history selection
  * recovery brief and session memory assist/update seams
* Current `coding-deepgent` does not yet appear to have:
  * live tool-result persistence with preview references
  * live microcompact in the query loop
  * live auto-compact in the query loop
  * post-compact restoration attachments
* Existing roadmap/dashboard says H05/H06/H20 minimal slices are implemented for MVP, but recent review suggests the cc-haha high-value runtime context pressure loop still has meaningful gaps that may justify a focused next-cycle stage rather than more edge behavior.

## Assumptions (temporary)

* The immediate deliverable should be a narrow staged product task, not a broad redesign of all prompt/context/memory code.
* The preferred implementation should reuse current `coding-deepgent` domains (`compact`, `sessions`, `runtime`, `tool_system`, `memory`) instead of adding a new runtime subsystem.
* `session-memory compact` is valid but should stay out of the first implementation slice unless earlier sub-stages reveal it is required to make the core flow coherent.
* The current work should target product code in `coding-deepgent/`, not the tutorial or `agents_deepagents/` tracks.

## Open Questions

* None after scope confirmation. The user explicitly chose the full task family:
  * tool result storage
  * microcompact
  * live auto-compact
  * post-compact restoration
  * reactive compact
  * session-memory compact

## Requirements (evolving)

* Align the context/compact work against cc-haha source behavior, not tutorial chapter shells.
* State the expected effect of each proposed sub-stage before implementation.
* Preserve LangChain/LangGraph as the runtime boundary.
* Prioritize the highest-value runtime context pressure behaviors:
  * tool result storage
  * microcompact
  * live auto-compact
  * post-compact restoration
  * reactive compact
  * session-memory compact
* Keep scope narrow and avoid unrelated resume/CLI polish unless it directly supports the runtime pressure loop.
* Update executable backend contracts if model-visible or cross-layer compact/runtime behavior changes.
* Use staged checkpoints so later sub-stages can be adjusted if earlier ones change the boundary.
* Preserve existing Stage 12A/12B/12C/12D foundations and build on them rather than reopening payload/projection/recovery/memory-quality work.

## Acceptance Criteria (evolving)

* [ ] A source-backed cc-haha alignment matrix exists for the selected context pressure features.
* [ ] The PRD identifies the concrete benefit and LangChain-native boundary for each planned sub-stage.
* [ ] The first implementation slice excludes tutorial-shell parity work that lacks concrete runtime value.
* [ ] The staged plan names explicit out-of-scope items beyond the six selected compact/runtime behaviors.
* [ ] The staged plan identifies focused tests and checkpoint conditions per sub-stage.
* [ ] The staged plan identifies the smallest LangChain-native interception points for tool-result pressure handling and model-call pressure handling.
* [ ] The staged plan breaks the broader family into checkpointed sub-stages rather than one unreviewable implementation blob.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Reproducing the tutorial `s06_context_compact.py` shell for its own sake
* Adding a model-visible `compact` tool solely for chapter parity
* Expanding recovery brief presentation without direct runtime benefit
* Broad prompt/context redesign outside the targeted context pressure loop
* Compact/recovery work that only adds presentation or tutorial parity without strengthening the runtime pressure loop

## Technical Notes

* New task: `.trellis/tasks/04-15-runtime-context-pressure-management`
* Likely product modules:
  * `coding-deepgent/src/coding_deepgent/compact/*`
  * `coding-deepgent/src/coding_deepgent/sessions/*`
  * `coding-deepgent/src/coding_deepgent/runtime/*`
  * `coding-deepgent/src/coding_deepgent/tool_system/*`
  * `coding-deepgent/src/coding_deepgent/memory/*`
* Existing contracts to revisit if scope becomes executable:
  * `.trellis/spec/backend/runtime-context-compaction-contracts.md`
* Existing planning/history likely relevant:
  * `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
  * `.trellis/plans/coding-deepgent-h01-h10-target-design.md`
  * prior Stage 12/13/16 compact PRDs
* Primary cc-haha source bands already identified:
  * `src/utils/queryContext.ts`
  * `src/utils/attachments.ts`
  * `src/utils/toolResultStorage.ts`
  * `src/query.ts`
  * `src/services/compact/microCompact.ts`
  * `src/services/compact/autoCompact.ts`
  * `src/services/compact/compact.ts`
  * `src/services/compact/sessionMemoryCompact.ts`

## Complexity

Complex.

Reasons:

* multiple product modules are involved
* the work changes runtime behavior rather than isolated helpers
* there are several valid staging choices
* correctness and boundary preservation matter more than raw feature count

## Expected Effect

Aligning this feature band should improve context-efficiency, reliability, recoverability, and product parity.

The local runtime effect is:

* large tool outputs stop bloating the live model context
* older low-value tool results can be compacted without breaking tool-use/tool-result invariants
* the agent can stay alive under context pressure during a live invocation instead of relying mainly on explicit resume-time compact helpers
* compacted continuations retain the minimum working context needed to continue coding

If these effects do not appear in focused runtime tests, the change is not worth shipping.

## LangChain Guard

Surface:

* middleware
* tool result handling
* compact/runtime services
* tests

Primary boundary:

* product code in `coding-deepgent/`

Smallest viable change:

* add one cross-cutting tool-result pressure seam and one model-call pressure seam
* reuse existing `context_payloads`, `compact`, `sessions`, and `RuntimeContext`
* avoid a custom query runtime

## cc-haha Alignment

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Cache-safe prefix split | `src/utils/queryContext.ts` splits default system prompt, user context, and system context for stable prefix assembly | keep stable prompt/context prefix and isolate dynamic pressure logic from core prompt | keep current `PromptContext` / runtime context split; do not redesign base prompt | partial | Reuse current boundary; do not make this task a prompt rewrite |
| Dynamic attachment protocol | `src/utils/attachments.ts` treats files, memories, plan/task reminders, compaction reminders, session memory, and restoration hints as typed dynamic context, not raw prompt concatenation | compact/restoration logic can re-inject critical context after pressure events | build on existing `ContextPayload` seam for post-compact restoration rather than cloning full attachment unions | partial | Align the restoration principle, not the full attachment catalog |
| Large tool result spill-to-disk | `src/utils/toolResultStorage.ts` persists oversized tool results to session-scoped files and returns preview references | live runtime stops carrying giant tool outputs while preserving full output retrievability | add tool-result persistence + preview reference seam for selected large-output tools | align | Implement now |
| Microcompact before full compact | `src/services/compact/microCompact.ts` clears older compactable tool results first and preserves API invariants | lower-cost pressure relief before full summarization; fewer unnecessary compactions | add deterministic live microcompact over model-call message history | align | Implement now |
| Auto-compact in query loop | `src/query.ts` + `src/services/compact/autoCompact.ts` proactively compact when context crosses thresholds | live invocations stay recoverable under pressure, not only resumed sessions | add live threshold-triggered compact in LangChain-native runtime seam | align | Implement now |
| Session-memory-first compact | `src/services/compact/sessionMemoryCompact.ts` uses session memory as a preferred compaction summary when available | smarter compaction with better continuity after long sessions | reuse and extend existing session-memory assist/update into a live compact path | align | Implement after earlier compact stages stabilize |
| Post-compact restoration | `src/services/compact/compact.ts` restores key file/plan/skill/agent context after compaction | compacted continuation retains enough working context to keep coding | add bounded post-compact restoration using current payload/recovery seams | align | Implement now |
| Reactive prompt-too-long fallback | `src/query.ts` also has prompt-too-long recovery paths beyond proactive auto-compact | hard failure fallback if proactive pressure handling misses | add a focused reactive fallback stage after proactive compact is in place | align | Implement in the same task family, but after proactive compact |

### Non-goals

* Do not clone `cc-haha`'s full attachment union, query loop, or analytics stack.
* Do not reopen Stage 12 payload foundation or Stage 12 recovery brief unless a direct runtime dependency appears.
* Do not add tutorial-shell parity features whose only value is naming similarity.
* Do not treat the full family as a single uncheckpointed implementation blob.
* Do not widen into unrelated prompt, permissions, task, or extension work while implementing the selected compact/runtime family.

### State Boundary

* Short-term dynamic context remains request-scoped / invocation-scoped.
* Session transcript and compact records remain durable session evidence.
* Session memory remains a separate durable artifact and assist source, not the first-line pressure mechanism in this task.
* Todo/task/recovery state must stay distinct from live compact bookkeeping.

### Model-visible Boundary

The model may see:

* preview references for oversized tool results
* bounded compact/microcompact boundary markers where needed
* restored high-value working context after compaction

The model should not see:

* internal bookkeeping that exists only to coordinate compaction
* arbitrary local metadata dumps
* tutorial-only wrapper instructions

## Research Notes

### Constraints from our repo/project

* Existing Stage 12 work already delivered:
  * typed `ContextPayload` rendering
  * deterministic message projection
  * recovery brief continuation context
  * memory quality policy
* Current live tool/middleware path already has a clean cross-cutting seam:
  * `ToolGuardMiddleware.wrap_tool_call()` for post-tool interception
  * `AgentMiddleware.wrap_model_call()` for pre-model pressure handling
* `RuntimeContext` already carries `session_context`, which can anchor session-scoped persisted artifacts.
* Current session store already has compact records and load-time compacted history, which can be reused for post-compact continuity rather than reinvented.
* Current runtime does not maintain a custom query loop; solution should stay inside LangChain middleware/services unless a later blocker proves otherwise.

### Feasible approaches here

**Approach A: Middleware-first live pressure loop** (Recommended)

How it works:

* Add one tool-result pressure seam that can persist large tool outputs and replace them with preview references.
* Add one model-call pressure seam that can microcompact older tool results and trigger proactive compact when thresholds are crossed.
* Reuse current context payloads/recovery helpers for post-compact restoration.

Pros:

* smallest LangChain-native path
* directly targets the highest-value runtime effects
* builds on current Stage 12 foundations instead of replacing them

Cons:

* requires careful tests around intermediate model-call history, not just final transcript behavior
* proactive compact is still non-trivial without a custom query loop

**Approach B: Resume-first compact hardening**

How it works:

* keep live invocation behavior mostly as-is
* deepen resume-time compact helpers, compact records, and recovery brief continuity

Pros:

* lower implementation risk
* reuses current session architecture directly

Cons:

* misses the user-requested "highlight" behavior
* does not solve live context pressure
* continues to invest in edge behavior over runtime differentiators

**Approach C: Full compact family now**

How it works:

* implement tool result storage, microcompact, auto-compact, post-compact restoration, reactive compact, and session-memory compact in one task family

Pros:

* broader parity pass

Cons:

* too wide for a first next-cycle slice
* harder checkpointing
* much higher risk of architecture drift or accidental custom-runtime creep

## Decision (ADR-lite)

**Context**: The product already has compact/recovery foundations, but it still lacks the cc-haha-style live runtime pressure loop that makes long sessions sustainable. The user explicitly wants high-value highlight alignment rather than more edge feature accumulation.

**Decision**: User-selected direction is Approach C in scope, executed with Approach A's implementation posture.

**Consequences**:

* current Stage 12 foundations are treated as prerequisites, not reopened work
* the work remains one task family, but must be executed as checkpointed sub-stages
* reactive compact and session-memory compact are in scope, but should come after tool-result storage, microcompact, proactive auto-compact, and post-compact restoration
* if checkpoint evidence shows the broader family is unsafe as one run, the task family may split into prerequisites rather than forcing scope through

## Technical Approach

Recommended implementation boundary:

* Tool-result pressure:
  * add a dedicated middleware/service layer after tool execution
  * keep tool-specific result-shape knowledge small and driven by capability metadata or a narrow compactable-tool allowlist
* Model-call pressure:
  * add a model-call middleware or runtime helper that can inspect the current invocation message history
  * apply deterministic microcompact first
  * evaluate proactive compact threshold second
* Post-compact restoration:
  * reuse `ContextPayload` and session/recovery seams for bounded restoration
  * do not copy the full cc attachment catalog

Proposed local modules:

* `coding_deepgent/compact/tool_results.py` or equivalent service seam
* `coding_deepgent/compact/microcompact.py`
* `coding_deepgent/compact/runtime_pressure.py`
* `coding_deepgent/compact/reactive.py` or equivalent fallback seam
* targeted extensions in:
  * `tool_system/capabilities.py`
  * `tool_system/middleware.py` or a sibling middleware
  * `sessions/*` only where compact record or restoration continuity requires it

## Test Plan

Focused tests by sub-stage:

* tool result storage
  * persists oversized result to a session-scoped location
  * returns preview reference content instead of full content
  * does not affect small results
* microcompact
  * preserves tool-use/tool-result invariants
  * clears only older eligible results
  * emits boundary/marker behavior if adopted
* live auto-compact
  * threshold crossing triggers compact once
  * low-pressure paths remain unchanged
  * compacted invocation remains valid for continuation
* post-compact restoration
  * restored payloads remain bounded and deduped
  * compacted continuation retains active work context
* reactive compact
  * prompt-too-long path can recover without corrupting session/tool invariants
  * proactive compact paths do not regress when reactive fallback is enabled
* session-memory compact
  * current valid session-memory artifact can participate in compaction
  * stale or missing artifacts follow explicit update rules
  * compact result remains bounded and continuation-safe

Likely test files:

* new:
  * `coding-deepgent/tests/test_tool_result_storage.py`
  * `coding-deepgent/tests/test_microcompact.py`
  * `coding-deepgent/tests/test_runtime_pressure.py`
* updates:
  * `coding-deepgent/tests/test_tool_system_middleware.py`
  * `coding-deepgent/tests/test_compact_artifacts.py`
  * `coding-deepgent/tests/test_sessions.py`
  * `coding-deepgent/tests/test_cli.py` only if continuation records/selection change

## Implementation Plan (small PRs / sub-stages)

* Sub-stage 1: Tool Result Storage
  * add session-scoped large-result persistence
  * return preview references
  * verify middleware/capability boundary holds
* Sub-stage 2: Microcompact
  * add deterministic live microcompact over invocation message history
  * preserve tool invariants
  * checkpoint whether proactive compact still holds unchanged
* Sub-stage 3: Live Auto-Compact
  * add threshold-triggered compact in live runtime path
  * keep validation focused on deterministic triggers and compact result shape
* Sub-stage 4: Post-Compact Restoration
  * restore minimal working context through bounded payloads
  * verify compacted continuation usability
* Sub-stage 5: Reactive Compact
  * add prompt-too-long fallback path
  * preserve compact/session invariants and avoid retry loops
* Sub-stage 6: Session-Memory Compact
  * add session-memory-guided compact path
  * preserve bounded continuation and session-memory freshness rules

## Checkpoint Protocol

Lean mode checkpoint after every sub-stage:

* State machine:
  * `planning`
  * `implementing`
  * `verifying`
  * `checkpoint`
  * `terminal`
* Checkpoint summary must record:
  * implemented behavior
  * focused tests run and result
  * files changed
  * cc-haha alignment evidence
  * LangChain-native architecture evidence
  * new boundary issues discovered
  * whether the next sub-stage still holds
* Decision mapping:
  * `APPROVE` -> `continue`
  * `ITERATE` -> `adjust` or `split`
  * `REJECT` -> `stop`

Checkpoint stop conditions:

* missing cc-haha evidence for a claimed aligned behavior
* implementation pressure toward a custom query runtime
* a prerequisite discovered that should be pulled into an earlier sub-stage
* focused tests show the current boundary is wrong

## Infrastructure Unlock

This work should unlock a more valuable next-cycle runtime baseline:

* live long-session survivability
* less prompt bloat from tool output
* a stronger foundation for later session-memory compact and subagent/fork cache-aware context work

## Checkpoint: Sub-stage 1 Tool Result Storage

State:

* checkpoint

Verdict:

* APPROVE

Implemented:

* Added `coding_deepgent.compact.tool_results` with:
  * session-scoped persisted tool-result path resolution under the active workspace
  * deterministic content serialization
  * persisted-output preview reference rendering
  * fail-open live rewrite helper for oversized successful tool results
* Exported the new seam from `coding_deepgent.compact`.
* Extended `ToolCapability` metadata with:
  * `persist_large_output`
  * `max_inline_result_chars`
  * `microcompact_eligible`
* Marked `bash`, `read_file`, `glob`, and `grep` as large-output persistence candidates.
* Updated `ToolGuardMiddleware` to post-process successful `ToolMessage` results through the new storage seam for eligible tools.
* Updated `.trellis/spec/backend/runtime-context-compaction-contracts.md` with a new live tool-result storage scenario.

Verification:

* `pytest -q coding-deepgent/tests/test_tool_result_storage.py coding-deepgent/tests/test_tool_system_middleware.py`
* `ruff check coding-deepgent/src/coding_deepgent/compact/tool_results.py coding-deepgent/src/coding_deepgent/compact/__init__.py coding-deepgent/src/coding_deepgent/tool_system/capabilities.py coding-deepgent/src/coding_deepgent/tool_system/middleware.py coding-deepgent/tests/test_tool_result_storage.py coding-deepgent/tests/test_tool_system_middleware.py`
* `mypy coding-deepgent/src/coding_deepgent/compact/tool_results.py coding-deepgent/src/coding_deepgent/tool_system/capabilities.py coding-deepgent/src/coding_deepgent/tool_system/middleware.py`

cc-haha alignment:

* Source files inspected:
  * `/root/claude-code-haha/src/utils/toolResultStorage.ts`
  * `/root/claude-code-haha/src/query.ts`
* Aligned now:
  * oversized tool results can be replaced by preview references while preserving full output on disk
  * storage is tool-boundary behavior, not a resume-only helper
* Deferred:
  * microcompact
  * auto-compact
  * reactive compact
  * session-memory compact
* Do-not-copy:
  * full cc analytics/feature-flag threshold machinery
  * provider-specific persistence behavior outside the local workspace model

LangChain architecture:

* Primitive used:
  * `ToolGuardMiddleware.wrap_tool_call`
  * `ToolMessage` content/artifact preservation
  * capability metadata for eligible tool selection
* Why this stays LangChain-native:
  * no custom query loop was introduced
  * the seam operates on standard LangChain tool results after allowed tool execution

Boundary findings:

* Important local boundary:
  * persisted output must stay inside the active workspace so existing `read_file` can reopen it later
* Important defer:
  * this stage does not yet reduce older tool results already present in the live invocation history; that remains Sub-stage 2

Decision:

* continue

Reason:

* focused tests, ruff, and mypy passed
* cc-haha alignment for the selected behavior is sufficient
* the next sub-stage still holds and now has a clearer large-output boundary to build on

## Checkpoint: Sub-stage 2 Microcompact

State:

* checkpoint

Verdict:

* APPROVE

Implemented:

* Added `coding_deepgent.compact.runtime_pressure` with:
  * deterministic `microcompact_messages(...)`
  * `RuntimePressureMiddleware`
  * constants for kept recent tool results and cleared-content markers
* Wired `RuntimePressureMiddleware` into the main app middleware chain between
  dynamic context middleware and `ToolGuardMiddleware`.
* Added focused tests for:
  * compacting only older eligible tool results
  * preserving recent eligible tool results
  * skipping ineligible tool results
  * middleware integration into the live model-call path
* Updated the runtime compact contract with a new live microcompact scenario.

Verification:

* `pytest -q coding-deepgent/tests/test_runtime_pressure.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_memory_integration.py coding-deepgent/tests/test_tool_result_storage.py coding-deepgent/tests/test_tool_system_middleware.py`
* `ruff check coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/src/coding_deepgent/compact/__init__.py coding-deepgent/src/coding_deepgent/containers/app.py coding-deepgent/tests/test_runtime_pressure.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_memory_integration.py`
* `mypy coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/src/coding_deepgent/containers/app.py`

cc-haha alignment:

* Source files inspected:
  * `/root/claude-code-haha/src/services/compact/microCompact.ts`
  * `/root/claude-code-haha/src/query.ts`
* Aligned now:
  * older eligible tool results can be cleared before a model call
  * large-output pressure is relieved before full compact
  * tool-call/tool-result linkage stays intact because results are rewritten in place rather than removed
* Deferred:
  * proactive auto-compact thresholding
  * reactive compact
  * session-memory compact
* Do-not-copy:
  * cached microcompact/provider-specific cache edit behavior
  * full cc token-estimation and analytics machinery

LangChain architecture:

* Primitive used:
  * `AgentMiddleware.wrap_model_call`
  * standard LangChain `BaseMessage` / `ToolMessage` rewriting
  * capability metadata to decide compact eligibility
* Why this stays LangChain-native:
  * no custom query runtime or graph node was introduced
  * message rewriting happens at the normal model-call interception seam

Boundary findings:

* Important local boundary:
  * `RuntimePressureMiddleware` should stay responsible only for live pressure handling, not permission or business tool semantics
* Important defer:
  * without a thresholded compact stage, microcompact alone only trims older tool-result cost; it does not yet solve full-window overflow

Decision:

* continue

Reason:

* focused tests, ruff, and mypy passed
* cc-haha alignment for microcompact is sufficient for the scoped behavior
* the next sub-stage still holds and should now build on the established runtime pressure seam instead of inventing a new one

## Checkpoint: Sub-stage 3 Live Auto-Compact

State:

* checkpoint

Verdict:

* APPROVE

Implemented:

* Extended `RuntimePressureMiddleware` to:
  * estimate live message tokens deterministically
  * call the existing compact summarizer seam through the model `.invoke()` path
  * proactively compact live invocation history when a configured local threshold is crossed
* Added `compact_live_messages_with_summary(...)`, `estimate_message_tokens(...)`,
  and `maybe_auto_compact_messages(...)`.
* Kept proactive compact fail-open on summarizer failure so later fallback paths
  remain possible.

Verification:

* `pytest -q coding-deepgent/tests/test_runtime_pressure.py coding-deepgent/tests/test_compact_summarizer.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_memory_integration.py coding-deepgent/tests/test_tool_result_storage.py coding-deepgent/tests/test_tool_system_middleware.py`
* `ruff check coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/src/coding_deepgent/compact/__init__.py coding-deepgent/src/coding_deepgent/containers/app.py coding-deepgent/tests/test_runtime_pressure.py coding-deepgent/tests/test_compact_summarizer.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_memory_integration.py`
* `mypy coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/src/coding_deepgent/containers/app.py`

cc-haha alignment:

* Source files inspected:
  * `/root/claude-code-haha/src/query.ts`
  * `/root/claude-code-haha/src/services/compact/autoCompact.ts`
  * `/root/claude-code-haha/src/services/compact/compact.ts`
* Aligned now:
  * proactive compact can happen in the live runtime path before a model call
  * compact uses a dedicated summary step rather than a fake fixed string
  * tool-pair tail preservation remains intact
* Deferred:
  * reactive compact
  * session-memory compact
* Do-not-copy:
  * full provider-specific context-window logic and analytics
  * custom query loop state machine

LangChain architecture:

* Primitive used:
  * `AgentMiddleware.wrap_model_call`
  * model `.invoke()` as the summarizer seam
  * request message rewriting only
* Why this stays LangChain-native:
  * no alternate loop was introduced
  * the middleware uses existing model and message abstractions only

Boundary findings:

* Important local boundary:
  * local token estimation is intentionally deterministic and approximate; it is a trigger heuristic, not a billing/tokenizer truth source
* Important defer:
  * prompt-too-long recovery is still needed because proactive estimates can miss provider-side limits

Decision:

* continue

Reason:

* focused tests, ruff, and mypy passed
* proactive compact is now present without breaking LangChain boundaries
* the next sub-stage should now restore compacted-away high-value context rather than widening threshold logic further

## Checkpoint: Sub-stage 4 Post-Compact Restoration

State:

* checkpoint

Verdict:

* APPROVE

Implemented:

* Extended live compact output to include a bounded restoration `SystemMessage`
  for persisted-output paths that were compacted away.
* Restoration dedupes paths and excludes paths already visible in the preserved
  tail.

Verification:

* `pytest -q coding-deepgent/tests/test_runtime_pressure.py coding-deepgent/tests/test_tool_result_storage.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_memory_integration.py`
* `ruff check coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/src/coding_deepgent/compact/__init__.py coding-deepgent/tests/test_runtime_pressure.py`
* `mypy coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`

cc-haha alignment:

* Source files inspected:
  * `/root/claude-code-haha/src/services/compact/compact.ts`
  * `/root/claude-code-haha/src/utils/attachments.ts`
* Aligned now:
  * post-compact output can restore high-value file references rather than relying on the summary alone
* Deferred:
  * richer file/task/skill/agent restoration
  * reactive compact
  * session-memory compact
* Do-not-copy:
  * full attachment catalog and restoration breadth

LangChain architecture:

* Primitive used:
  * additional `SystemMessage` in the compacted live message list
* Why this stays LangChain-native:
  * restoration remains bounded message context, not a new runtime object model

Boundary findings:

* Important local boundary:
  * current restoration is intentionally limited to persisted-output file paths, because those are the most concrete recoverable artifacts already present in the product
* Important defer:
  * broader plan/skill/agent restoration should wait until there is source-backed evidence it is needed locally

Decision:

* continue

Reason:

* focused tests, ruff, and mypy passed
* the next sub-stage now has a stable proactive compact path to fall back from when prompt-too-long still occurs

## Checkpoint: Sub-stage 5 Reactive Compact

State:

* checkpoint

Verdict:

* APPROVE

Implemented:

* Extended `RuntimePressureMiddleware.wrap_model_call()` to:
  * detect prompt-too-long style failures
  * perform one reactive compact retry using the same summarizer seam
  * re-raise non prompt-too-long failures unchanged
* Added `reactive_compact_messages(...)` and prompt-too-long detection helper.

Verification:

* `pytest -q coding-deepgent/tests/test_runtime_pressure.py coding-deepgent/tests/test_compact_summarizer.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_memory_integration.py coding-deepgent/tests/test_tool_result_storage.py coding-deepgent/tests/test_tool_system_middleware.py`
* `ruff check coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/src/coding_deepgent/compact/__init__.py coding-deepgent/tests/test_runtime_pressure.py`
* `mypy coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`

cc-haha alignment:

* Source files inspected:
  * `/root/claude-code-haha/src/query.ts`
  * reactive compact references in the cc compact/query flow
* Aligned now:
  * proactive compact has a bounded prompt-too-long fallback path
  * fallback remains compact-based rather than introducing unrelated retry behavior
* Deferred:
  * provider-specific error typing
* Do-not-copy:
  * full cc runtime transition machine and provider-specialized branching

LangChain architecture:

* Primitive used:
  * one retry within `wrap_model_call`
* Why this stays LangChain-native:
  * fallback is still expressed as request-message rewriting and re-invocation of the same handler

Boundary findings:

* Important local boundary:
  * only prompt-too-long style failures get fallback retry treatment
* Important defer:
  * richer provider-specific error typing can wait until a concrete mismatch appears

Decision:

* continue

Reason:

* focused tests, ruff, and mypy passed
* the next sub-stage can now safely add session-memory assist on top of an already stable proactive/reactive compact chain

## Checkpoint: Sub-stage 6 Session-Memory Compact

State:

* checkpoint

Verdict:

* APPROVE

Implemented:

* Updated `agent_runtime_service.session_payload()` so existing `session_memory`
  state flows into live runtime state.
* Extended proactive and reactive live compact to pass bounded session-memory
  assist text into `generate_compact_summary(...)` when a current artifact is
  available in runtime state.
* Added focused tests proving:
  * `session_memory` survives into runtime payload
  * live auto-compact can pass assist text to the summarizer

Verification:

* `pytest -q coding-deepgent/tests/test_agent_runtime_service.py coding-deepgent/tests/test_runtime_pressure.py coding-deepgent/tests/test_compact_summarizer.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_memory_integration.py coding-deepgent/tests/test_tool_result_storage.py coding-deepgent/tests/test_tool_system_middleware.py`
* `ruff check coding-deepgent/src/coding_deepgent/agent_runtime_service.py coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/tests/test_agent_runtime_service.py coding-deepgent/tests/test_runtime_pressure.py`
* `mypy coding-deepgent/src/coding_deepgent/agent_runtime_service.py coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py`

cc-haha alignment:

* Source files inspected:
  * `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
  * existing local session memory contribution/update seams
* Aligned now:
  * live compact can consume current session-memory artifact as bounded continuity aid
* Deferred:
  * session-memory-driven compact boundary selection
  * live session-memory refresh/promotion workflow
* Do-not-copy:
  * full cc session-memory compact heuristics and remote config machinery

LangChain architecture:

* Primitive used:
  * existing runtime state payload
  * existing summarizer assist-context seam
* Why this stays LangChain-native:
  * no new store/runtime layer was introduced; current state and helper seams were reused

Boundary findings:

* Important local boundary:
  * this stage uses current session-memory artifacts when present; it does not yet refresh them automatically from live compaction
* Residual risk:
  * deeper session-memory compact parity would require explicit state-refresh semantics in the live runtime path

Decision:

* continue

Terminal note:

* All planned sub-stages in the current task family are now complete. This `continue` maps to staged-run completion rather than starting a speculative Sub-stage 7.

Reason:

* focused tests, ruff, and mypy passed
* the six selected compact/runtime behaviors now exist in a LangChain-native local form

## Follow-on Checkpoint: Live Pressure Observability And Evidence

State:

* checkpoint

Verdict:

* APPROVE

Implemented:

* Extended `RuntimePressureMiddleware` to emit structured runtime events for:
  * `microcompact`
  * `auto_compact`
  * `reactive_compact`
* Routed those events through the existing `event_sink` path and the existing
  `append_runtime_event_evidence(...)` seam.
* Expanded runtime-event evidence support so compact/runtime-pressure events can
  be recorded as bounded `runtime_event` session evidence.
* Added focused tests proving:
  * runtime pressure events reach `event_sink`
  * session evidence is appended when `session_context` is active
  * existing hook/tool runtime-event paths still pass
* Updated the backend compact/runtime contract with a live runtime pressure
  observability scenario.

Verification:

* `pytest -q coding-deepgent/tests/test_runtime_pressure.py coding-deepgent/tests/test_hooks.py coding-deepgent/tests/test_tool_system_middleware.py coding-deepgent/tests/test_sessions.py`
* `ruff check coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/src/coding_deepgent/sessions/evidence_events.py coding-deepgent/tests/test_runtime_pressure.py`
* `mypy coding-deepgent/src/coding_deepgent/compact/runtime_pressure.py coding-deepgent/src/coding_deepgent/sessions/evidence_events.py`

cc-haha alignment:

* Source references:
  * runtime compact path in `/root/claude-code-haha/src/query.ts`
  * compact flow observability references in the cc compact stack and docs
* Aligned now:
  * compact/runtime-pressure transitions are observable as explicit runtime events
  * compact evidence uses a bounded ledger path rather than raw transcript dumps
* Do-not-copy:
  * full cc analytics/telemetry surface
  * provider-specific cost/cache analytics

LangChain architecture:

* Primitive used:
  * middleware-side event emission
  * existing `RuntimeEvent` and `event_sink`
  * existing session evidence seam
* Why this stays LangChain-native:
  * no second observability stack or compact-specific persistence system was added

Decision:

* APPROVE

Reason:

* the requested observability/evidence follow-on is now implemented with focused verification and no new architecture drift

## Final Confirmation

Here's my understanding of the complete requirements:

**Goal**: add the cc-haha high-value runtime context pressure loop to `coding-deepgent`, covering both proactive and fallback compact behavior, without drifting into tutorial-shell parity or unrelated edge work.

**Requirements**:

* build on existing Stage 12 foundations rather than reopening them
* implement the following task family in order:
  * tool result storage
  * microcompact
  * live auto-compact
  * post-compact restoration
  * reactive compact
  * session-memory compact
* keep LangChain/LangGraph as the runtime boundary
* use staged checkpoints after every sub-stage
* update contracts/tests where cross-layer behavior changes

**Acceptance Criteria**:

* [ ] cc-haha alignment is source-backed for each sub-stage
* [ ] the runtime pressure loop is implemented through focused, checkpointed sub-stages
* [ ] the model context no longer carries giant low-value tool outputs unnecessarily
* [ ] live compact behavior survives pressure without breaking protocol invariants
* [ ] fallback reactive compact and session-memory compact are integrated without forcing a custom runtime

**Definition of Done**:

* focused tests per sub-stage pass
* lint/typecheck stay green at the scoped level
* contracts/docs are updated when behavior changes
* checkpoint verdicts are recorded after each sub-stage

**Out of Scope**:

* tutorial-shell parity work
* unrelated recovery brief/UI polish
* broad prompt redesign
* unrelated permission/task/extension work

**Technical Approach**:

* middleware-first live pressure loop
* tool-result pressure seam + model-call pressure seam
* bounded restoration via current payload/recovery foundations
* reactive compact and session-memory compact added only after proactive path is stable

**Implementation Plan (small PRs / sub-stages)**:

* PR1 / Sub-stage 1: Tool Result Storage
* PR2 / Sub-stage 2: Microcompact
* PR3 / Sub-stage 3: Live Auto-Compact
* PR4 / Sub-stage 4: Post-Compact Restoration
* PR5 / Sub-stage 5: Reactive Compact
* PR6 / Sub-stage 6: Session-Memory Compact
