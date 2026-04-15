# brainstorm: diagnose module upgrade coupling

## Goal

Diagnose why the current `coding-deepgent` upgrade path still feels highly coupled when the desired product direction is to optimize one module directly. Clarify whether the problem is incomplete infrastructure, a mismatch in the definition of "infrastructure", or an overly coupled implementation approach.

## What I already know

* User expects that after enough infrastructure work, a module such as `memory`, `compact`, `plugins`, or `mailbox` can be optimized mostly within that module.
* The latest implemented slice, `context pressure v2 / session-memory compaction: Deterministic Assist`, touched multiple areas:
  * `sessions`
  * `runtime.state`
  * `cli`
  * `cli_service`
  * `compact.summarizer`
  * tests and compaction contracts
* The feature itself was chosen because it crosses existing product flows: session resume, state snapshots, recovery brief, generated compact summary, and memory continuity.
* Existing roadmap/docs define foundation mostly as LangChain-native runtime correctness, persistence, recovery, tool/permission safety, compact/session contracts, and local extension seams.
* Current repo has domain folders, but several orchestration seams are still centralized or hardcoded:
  * `JsonlSessionStore._coerce_state_snapshot()` knows concrete runtime state fields.
  * `render_recovery_brief()` manually owns recovery sections.
  * `generated_compacted_continuation_history()` manually wires compact assist inputs.
  * `ContextPayload` exists but is not yet a universal dynamic-context provider registry.

## Assumptions (temporary)

* There are two kinds of coupling in play:
  * Essential coupling from product flows that genuinely cross modules.
  * Accidental coupling from missing module-level extension points.
* The latest slice had both kinds.
* The term "infrastructure" may currently be overloaded between:
  * runtime correctness infrastructure
  * module-isolation / upgrade infrastructure

## Open Questions

* None for the next direction: user selected `Module Upgrade Infra Stage`.

## Requirements (evolving)

* Explain why the latest upgrade crossed modules.
* Separate expected cross-layer integration from avoidable accidental coupling.
* Identify missing infrastructure that would allow more module-local optimization.
* Recommend a next planning direction.
* Lock the next direction to module-isolated upgrade seams before continuing feature work.

## Acceptance Criteria (evolving)

* [x] Inspect current coupling points from the latest slice.
* [x] Compare them against existing roadmap/foundation definitions.
* [x] State whether this is infrastructure weakness, definition mismatch, or implementation drift.
* [x] Ask one high-value follow-up question to choose the next direction.
* [x] Capture the user's decision.

## Definition of Done

* Diagnosis is captured in this PRD.
* User receives a concise recommendation with concrete options.
* No code changes are made in this brainstorm task.

## Out of Scope

* Refactoring the current implementation immediately.
* Reverting the latest deterministic-assist slice.
* Designing a full plugin/coordinator/mailbox architecture in this diagnostic task.

## Technical Notes

### Current Coupling Evidence

The latest slice touched multiple modules because the chosen behavior was inserted into existing flow-specific seams:

* State persistence:
  * `coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py`
  * reason: state snapshot coercion is hardcoded and had to learn `session_memory`
* Runtime state typing:
  * `coding-deepgent/src/coding_deepgent/runtime/state.py`
  * reason: session memory became part of persisted runtime state
* Recovery/resume:
  * `coding-deepgent/src/coding_deepgent/sessions/resume.py`
  * reason: recovery brief rendering is centralized and manually sectioned
* CLI orchestration:
  * `coding-deepgent/src/coding_deepgent/cli.py`
  * reason: explicit update was exposed as a resume flag
* Service orchestration:
  * `coding-deepgent/src/coding_deepgent/cli_service.py`
  * reason: generated compact flow manually supplies summarizer inputs
* Compact summarizer:
  * `coding-deepgent/src/coding_deepgent/compact/summarizer.py`
  * reason: summarizer request builder had no generic assist/context provider input

### Current Infrastructure Strength

The repo has good infrastructure for:

* strict tool schemas
* permission/tool boundary
* JSONL sessions and append-only compact records
* recovery brief
* memory quality policy
* compact message invariants
* local plugin manifest validation
* targeted contracts/tests

### Current Infrastructure Gap

The repo is weaker for module-local upgrades because it lacks:

* a pluggable runtime-state serialization registry
* a dynamic context provider registry that all modules can contribute to
* a recovery brief section provider interface
* a compact assist provider interface
* module-owned CLI command registration or feature command grouping
* clear distinction between "module owns data" and "flow owns projection/rendering"

### Preliminary Diagnosis

This is both:

* incomplete module-isolation infrastructure
* and a definition mismatch

The existing foundation work mostly built "runtime correctness infrastructure": safe sessions, compact records, recovery, memory quality, tool contracts, and validation. The user's expectation points to "module upgrade infrastructure": a module should expose contribution points so future optimization happens behind that module boundary and only light integration glue changes elsewhere.

The latest slice also showed implementation drift: I optimized for the safest deterministic path and explicit testability, but I did not first create a small generic extension seam such as `SessionContextContribution` / `CompactAssistProvider`. That made the slice reliable, but not as modular as the user's target.

## Decision (ADR-lite)

**Context**: The user expects future upgrades to target one module directly. The current codebase has good runtime-correctness infrastructure, but module upgrades still require edits in orchestration files such as `cli_service`, `sessions.resume`, `sessions.store_jsonl`, and `compact.summarizer`.

**Decision**: Prioritize a `Module Upgrade Infra Stage` before continuing `Threshold-Triggered Local Updates` or other feature work.

**Consequences**:

* Future module work should add or change module-owned providers instead of editing every flow directly.
* The current `session_memory` deterministic-assist slice should be retrofitted onto the new seams rather than treated as the final architecture.
* More feature work should pause until the first module-upgrade seams exist, otherwise coupling will continue to grow.

## Recommended Next Stage

### Goal

Introduce lightweight module contribution seams so modules can participate in runtime state persistence, recovery brief rendering, compact assistance, and dynamic context assembly without each feature editing central orchestration code.

### First Slice

Start with `session_memory` as the proving case because it already exposed the coupling.

Implement only enough generic infrastructure to move the current hard wiring behind module-owned contribution functions:

* `RuntimeStateContribution`
  * owns validation/coercion/defaulting for one state key such as `session_memory`
* `RecoveryBriefContribution`
  * lets a module render one recovery section without editing `render_recovery_brief()` for every module
* `CompactAssistContribution`
  * lets a module provide optional bounded assist text for generated compact summary
* Optional later seam: `DynamicContextContribution`
  * defer unless the first slice needs it immediately

### Concrete Refactor Target

Move current `session_memory` hard wiring out of:

* `JsonlSessionStore._coerce_state_snapshot()`
* `render_recovery_brief()`
* `cli_service.generated_compacted_continuation_history()`
* `compact.summarizer` direct session-memory naming

Into module-owned contribution functions under `coding_deepgent.sessions.session_memory` or a small shared contribution module.

### Non-goals

* Do not build a broad plugin framework.
* Do not add threshold-triggered updates yet.
* Do not add background extraction.
* Do not add mailbox/coordinator/runtime lifecycle.
* Do not over-abstract every existing module at once.

### Acceptance Criteria

* `session_memory` behavior remains unchanged from the deterministic-assist slice.
* At least one generic contribution seam exists and is tested.
* Central orchestration code no longer names all `session_memory` details directly.
* Focused tests prove current/stale/invalid behavior still works.
* The contract doc distinguishes runtime-correctness infrastructure from module-upgrade infrastructure.

## Cross-Module Coupling Review Before Implementation

### Local module coupling map

| Module band | Current local coupling level | Evidence | Can optimize module alone today? | Required seam |
|---|---:|---|---|---|
| `tool_system` / MCP tools | low-to-medium | `ToolCapability`, `CapabilityRegistry`, MCP adapters already normalize extension tools into one registry | mostly yes for new tools/MCP capabilities | keep capability registry as the tool boundary |
| `memory` long-term recall | medium | `MemoryContextMiddleware` owns model injection, but recall still depends on runtime store and prompt context | yes for quality/recall policy; no for recovery/compact effects | dynamic context contribution registry |
| `todo` | medium | `TodoContextMiddleware` already contributes context, but runtime state shape is still shared | yes for tool/schema changes; no for persistence/projection changes | runtime state contribution registry |
| `sessions` / recovery | high | `render_recovery_brief()` owns sections manually; `JsonlSessionStore._coerce_state_snapshot()` knows concrete state fields | no | recovery brief + state serializer contributions |
| `compact` | high | generated summary request and continuation history are explicit service functions | no, if assist sources or recovery semantics change | compact assist provider registry |
| `plugins` | medium | local plugin registry is isolated, but startup validation and capability loading are central | partly | plugin lifecycle state + startup contribution seam |
| `subagents` / verifier | high | verifier tool allowlists, plan lookup, evidence persistence, and recovery all cross modules | no | agent lifecycle/evidence contribution seams |
| `hooks` | comparatively low | dispatcher already centralizes hook events and adapters | mostly yes | keep event-dispatch pattern; use as model |
| `CLI` | high | `cli.py` owns command flags directly | no | command grouping or service-level command seams |

### Interpretation

Some coupling is essential: model-visible flows such as "resume with compact summary" genuinely touch state, recovery, and message assembly.

But much of the friction is accidental: central code manually knows each feature's fields and render rules. The current architecture has domain folders, but not enough domain-owned contribution interfaces.

## cc-haha Coupling Analysis

### What cc-haha does well

cc-haha does not make modules fully independent. It reduces coupling by routing module behavior through a few broad protocols:

* `Tool` / `ToolUseContext`
  * Tools receive a rich context object with app state, settings, tool list, MCP clients/resources, abort control, file caches, session/task hooks, and notification plumbing.
  * This means tool implementations can evolve behind the `Tool` interface, but the context object itself is intentionally broad and central.
* `Attachment`
  * Dynamic model-visible context is represented as a tagged union of attachment types.
  * Modules add context by creating attachments; central message normalization renders attachments into API messages.
  * This reduces random prompt-string injection, but adding a new attachment type still requires updating the central union and renderer.
* Hooks
  * cc-haha has hook matchers/execution for lifecycle events, including compact hooks.
  * Plugins/skills/session hooks are merged through a central hook resolver with source context and dedup rules.
  * This is a real module-contribution pattern.
* Plugin loader
  * Plugin loading separates source/install/cache/enable concerns and returns `LoadedPlugin` results for startup consumers.
  * It still has a large central loader, but capability consumers depend on loaded plugin output, not every plugin implementation detail.
* Session memory
  * Session memory is not module-local. It registers a post-sampling hook, uses thresholds, creates isolated subagent context, updates memory files, and is consumed by compaction.
  * cc-haha solved this with lifecycle hooks plus isolated/forked context, not with "just edit the memory module".

### What cc-haha does not solve completely

cc-haha still has central switch/union points:

* `Attachment` is a large tagged union.
* `normalizeAttachmentForAPI()` is a large central renderer.
* `ToolUseContext` is a broad dependency object.
* Plugin loading is centralized and complex.
* Session memory relies on hook registration and compaction integration.

So the realistic target is not "any module can upgrade without touching anything else." The realistic target is:

* module upgrade touches mostly module-owned provider/contribution code
* central code changes only when a new contribution type/protocol is introduced
* existing contribution protocols allow new behavior without editing every flow

## Answer: Can We Independently Upgrade One Module?

Today:

* For pure tool/schema/policy changes: often yes.
* For dynamic context, recovery, compaction, persisted state, or subagent lifecycle: no.
* For plugin lifecycle and mailbox: no, because they need lifecycle/state/orchestration seams that are not present yet.

After the proposed `Module Upgrade Infra Stage`:

* We should be able to upgrade `session_memory` by changing its contribution provider instead of editing `store_jsonl`, `resume`, `cli_service`, and `summarizer` together.
* We should still expect one-time central changes when introducing a new category of contribution.
* We should not promise zero cross-module impact; instead, promise bounded impact through explicit extension seams.

## Revised Stage Direction

The module-upgrade infra stage should copy the useful cc-haha pattern, not its TS/product complexity:

* Copy the idea:
  * tagged/context contributions
  * lifecycle/event hooks
  * module-owned providers
  * central renderer/orchestrator consumes generic contribution outputs
* Do not copy directly:
  * giant `ToolUseContext`
  * giant attachment union as-is
  * broad plugin loader complexity
  * background session-memory runtime in this stage

Recommended local Python shape:

* small dataclasses/protocols:
  * `RuntimeStateContribution`
  * `RecoveryBriefContribution`
  * `CompactAssistContribution`
* one registry or static tuple of known contributions
* start with only `session_memory`
* keep plugin discovery/runtime registration for later, after the static seam proves useful
