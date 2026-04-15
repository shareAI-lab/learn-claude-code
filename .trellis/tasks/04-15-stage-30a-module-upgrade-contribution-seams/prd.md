# Stage 30A: Module Upgrade Contribution Seams

## Goal

Reduce accidental cross-module coupling by introducing lightweight module contribution seams for runtime-state persistence, recovery brief rendering, and generated compact assist text. Use the existing `session_memory` deterministic-assist slice as the proving case, preserving behavior while moving hard wiring out of central orchestration files.

## Concrete Benefit

* Modularity: future `session_memory` changes should mostly touch module-owned contribution code.
* Maintainability: central session/compact flows should consume generic contributions instead of knowing every feature's fields and render rules.
* Roadmap discipline: unblock later `Threshold-Triggered Local Updates` without adding more hard-coded coupling.

## What I already know

* The user wants module-level optimization to be possible after infrastructure work.
* The current deterministic-assist slice works and is tested, but it hard-wires `session_memory` into:
  * `JsonlSessionStore._coerce_state_snapshot()`
  * `render_recovery_brief()`
  * `cli_service.generated_compacted_continuation_history()`
  * `compact.summarizer` parameter naming
* Local coupling review found similar coupling in `sessions`, `compact`, `subagents`, and `CLI`, while `tool_system`, `hooks`, and MCP are comparatively better isolated.
* cc-haha reduces coupling through broad protocols such as `Tool` / `ToolUseContext`, `Attachment`, hooks, and plugin loading. It does not make modules completely independent.

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve maintainability and modularity. The local runtime effect is: modules contribute typed state/context/assist outputs through explicit seams, while central flows stay small consumers of generic outputs.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Dynamic context | `utils/attachments.ts` models many model-visible context items as typed `Attachment` variants consumed by a central renderer | avoid ad hoc prompt/string injection and flow-specific wiring | small local contribution dataclasses, not a giant union | partial | Align the provider/renderer split |
| Hooks | `utils/hooks.ts` merges registered/session/plugin hooks and includes compact lifecycle hooks | let modules participate in lifecycle flows through registered contributions | static contribution registry first | partial | Align the lifecycle contribution idea, not full hook runtime |
| Plugin loading | `utils/plugins/pluginLoader.ts` centralizes load/merge results for downstream consumers | central consumers depend on normalized outputs rather than plugin internals | static contribution registry with module-owned providers | partial | Keep small; no plugin lifecycle now |
| Session memory | `services/SessionMemory/sessionMemory.ts` registers post-sampling behavior and is consumed by compact flows | session memory should be a module-owned provider, not hard-coded in every central flow | `session_memory` contribution providers | align | Use as proving case |

### Source files inspected

* `/root/claude-code-haha/src/Tool.ts`
* `/root/claude-code-haha/src/utils/attachments.ts`
* `/root/claude-code-haha/src/utils/messages.ts`
* `/root/claude-code-haha/src/utils/hooks.ts`
* `/root/claude-code-haha/src/utils/plugins/pluginLoader.ts`
* `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
* `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`

## LangChain-Native Boundary

Surface:
* state, prompt/context assembly, compact-summary request construction, tests

Primary boundary:
* product code under `coding_deepgent`, not a new framework

Smallest viable change:
* add small dataclasses/helpers for contribution outputs
* add a static registry for now
* retrofit only `session_memory`
* do not add plugin runtime registration, middleware, graph nodes, or background agents

## Requirements

* Add lightweight contribution primitives:
  * runtime state contribution/coercion
  * recovery brief section contribution
  * compact assist contribution
* Add a static contribution registry containing only `session_memory` initially.
* Move `session_memory` behavior behind module-owned contribution providers.
* Remove `session_memory` knowledge from central state coercion, recovery rendering, and compact assist orchestration.
* Preserve current deterministic-assist behavior exactly.
* Keep `sessions resume --session-memory` as the explicit UX for now.

## Acceptance Criteria

* [ ] Runtime state contribution helper is tested.
* [ ] Recovery brief contribution helper is tested.
* [ ] Compact assist contribution helper is tested.
* [ ] Existing `session_memory` current/stale/invalid behavior still passes.
* [ ] `JsonlSessionStore._coerce_state_snapshot()` no longer imports or calls `session_memory` directly.
* [ ] `render_recovery_brief()` no longer has a hard-coded `session_memory` field.
* [ ] `cli_service.generated_compacted_continuation_history()` consumes generic compact assist output.
* [ ] Contract docs describe contribution seams and their limits.

## Out of Scope

* threshold-triggered session memory updates
* background session-memory extraction
* mailbox/coordinator lifecycle
* plugin install/enable/update lifecycle
* broad dynamic context provider registry for all modules
* full cc-haha `Attachment` union clone
* full hook runtime clone

## Technical Approach

### Sub-stage 1: Contribution Primitives And Registry

* Add `coding_deepgent.sessions.contributions` with:
  * `RuntimeStateContribution`
  * `RecoveryBriefSection`
  * `RecoveryBriefContribution`
  * `CompactAssistContribution`
  * helper functions to coerce state, render sections, and collect assist text
* Add a static `coding_deepgent.sessions.contribution_registry` that imports `session_memory` providers.
* Add focused tests for the generic helpers.

### Sub-stage 2: Retrofit Session Memory

* Move session-memory state coercion into a module-owned provider.
* Move recovery rendering into a module-owned provider.
* Move compact assist text into a module-owned provider.
* Rename compact summarizer's generic assist parameter away from `session_memory`.
* Preserve CLI `--session-memory`.

### Sub-stage 3: Contracts And Checkpoint

* Update runtime context/compaction contract docs.
* Run focused tests plus targeted lint/typecheck.
* Record checkpoint and stop at terminal if no new prerequisite appears.

## Test Plan

* `pytest -q coding-deepgent/tests/test_session_contributions.py`
* `pytest -q coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_compact_summarizer.py`
* targeted `ruff check` on changed files
* targeted `mypy` on changed files

## Definition of Done

* Focused tests pass.
* Targeted ruff and mypy pass.
* Stage checkpoint records cc-haha alignment, LangChain architecture, and next-stage impact.
* No threshold/background/session-memory automation is introduced.

## Checkpoint: Sub-stage 1 Contribution Primitives And Registry

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added lightweight contribution primitives for runtime state, recovery brief sections, and compact assist text.
- Added a static contribution registry seeded only with `session_memory`.
- Added focused helper tests proving contribution state coercion, recovery section filtering, and compact assist joining.

Verification:
- `pytest -q coding-deepgent/tests/test_session_contributions.py`
- `ruff check coding-deepgent/src/coding_deepgent/sessions/contributions.py coding-deepgent/src/coding_deepgent/sessions/contribution_registry.py coding-deepgent/src/coding_deepgent/sessions/session_memory.py coding-deepgent/tests/test_session_contributions.py`
- `mypy coding-deepgent/src/coding_deepgent/sessions/contributions.py coding-deepgent/src/coding_deepgent/sessions/contribution_registry.py coding-deepgent/src/coding_deepgent/sessions/session_memory.py coding-deepgent/tests/test_session_contributions.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/utils/attachments.ts`
  - `/root/claude-code-haha/src/utils/hooks.ts`
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
- Aligned:
  - module behavior now starts to flow through typed contribution outputs rather than ad hoc central wiring
- Deferred:
  - full attachment union
  - plugin/runtime contribution discovery
- Do-not-copy:
  - broad `ToolUseContext` and hook runtime

LangChain architecture:
- Primitive used:
  - dataclass contribution descriptors and pure helper functions
- Why no heavier abstraction:
  - a static tuple is enough to prove the seam before adding dynamic/plugin registration

Boundary findings:
- New issue:
  - central flows still need to consume the new registry
- Impact on next stage:
  - sub-stage 2 remains valid and should retrofit only `session_memory`

Decision:
- continue

Reason:
- The seam exists and is tested without changing runtime behavior. Next step is a behavior-preserving retrofit.

## Checkpoint: Sub-stage 2 Session Memory Retrofit

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Moved `session_memory` state coercion behind `RuntimeStateContribution`.
- Moved recovery brief rendering behind `RecoveryBriefContribution`.
- Moved generated compact assist text behind `CompactAssistContribution`.
- Renamed the compact summarizer's generic assist parameter from `session_memory` to `assist_context`.
- Kept the explicit CLI `--session-memory` UX intact.

Verification:
- `pytest -q coding-deepgent/tests/test_session_contributions.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_compact_summarizer.py`
- `ruff check ...` on changed source/test files
- `mypy ...` on changed source/test files

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/utils/attachments.ts`
  - `/root/claude-code-haha/src/utils/messages.ts`
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
- Aligned:
  - central flows now consume typed contributions rather than session-memory-specific implementation details
- Deferred:
  - dynamic plugin registration
  - threshold/background automation
- Do-not-copy:
  - giant attachment union and broad `ToolUseContext`

LangChain architecture:
- Primitive used:
  - small static provider registry and pure dataclass descriptors
- Why no heavier abstraction:
  - behavior-preserving retrofit did not require middleware, graph state, plugin discovery, or DI container changes

Boundary findings:
- New issue:
  - CLI still directly exposes `--session-memory`; module-owned CLI registration remains a later concern
- Impact on next stage:
  - sub-stage 3 should document the seam and stop

Decision:
- continue

Reason:
- Retrofit passed focused validation and fixed the immediate coupling target without expanding scope.

## Checkpoint: Sub-stage 3 Contracts And Terminal Validation

State:
- terminal

Verdict:
- APPROVE

Implemented:
- Updated the runtime context and compaction contract doc to describe contribution seams and limits.
- Verified central orchestration files no longer contain direct `session_memory` implementation details outside the explicit CLI UX.
- Preserved deterministic-assist behavior while introducing module-upgrade infrastructure.

Verification:
- `rg -n "session_memory=|compact_summary_assist_text|read_session_memory_artifact|render_session_memory_line|SessionMemoryArtifact|SESSION_MEMORY_STATE_KEY" coding-deepgent/src/coding_deepgent/cli_service.py coding-deepgent/src/coding_deepgent/compact/summarizer.py coding-deepgent/src/coding_deepgent/sessions/resume.py coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py coding-deepgent/src/coding_deepgent/runtime/state.py coding-deepgent/src/coding_deepgent/sessions/__init__.py`
- `pytest -q coding-deepgent/tests/test_session_contributions.py coding-deepgent/tests/test_sessions.py coding-deepgent/tests/test_cli.py coding-deepgent/tests/test_compact_summarizer.py`
- `ruff check ...` on changed source/test files
- `mypy ...` on changed source/test files

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/Tool.ts`
  - `/root/claude-code-haha/src/utils/attachments.ts`
  - `/root/claude-code-haha/src/utils/hooks.ts`
  - `/root/claude-code-haha/src/utils/plugins/pluginLoader.ts`
  - `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
- Aligned:
  - useful pattern of module-owned contribution outputs consumed by central flow
- Deferred:
  - dynamic plugin registration
  - broad lifecycle hooks
  - threshold/background session memory
- Do-not-copy:
  - cc-haha's giant attachment union, broad context object, and loader complexity

LangChain architecture:
- Primitive used:
  - pure dataclasses, static provider tuple, existing session/compact functions
- Why no heavier abstraction:
  - current need is module-local upgrade seams, not a framework/plugin runtime

Boundary findings:
- New issue:
  - CLI command ownership remains centralized and should be treated as a later module-upgrade seam if it starts blocking feature work
- Impact on next stage:
  - `Threshold-Triggered Local Updates` can now build primarily inside `session_memory` providers and update logic

Decision:
- terminal

Reason:
- Stage 30A met the goal: contribution seams exist, `session_memory` is retrofitted behind them, focused validation passes, and no threshold/background feature work leaked in.
