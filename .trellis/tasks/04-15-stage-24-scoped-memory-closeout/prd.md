# Stage 24: Scoped Memory Closeout

## Goal

Close the highest-value remaining H07 MVP gaps by tightening the scoped cross-session memory contract around namespace isolation, durable write quality, and bounded recall/surfacing.

## Function Summary

This stage closes H07 by treating local memory as scope-aware cross-session memory rather than a generic note dump. The MVP closeout focuses on namespace isolation, write quality gates, and middleware recall scope.

## Expected Benefit

* Cross-session continuity: durable memory survives across sessions without collapsing all memory scopes together.
* Reliability: duplicates and transient state stay out of long-term memory.
* Maintainability: memory behavior is pinned by scope/namespace contracts instead of ad hoc usage.

## Corresponding Highlights

* `H07 Scoped cross-session memory`

## Corresponding Modules

* `coding_deepgent.memory`
* `coding_deepgent.runtime`
* `coding_deepgent.sessions`

## Out Of Scope

* rich session-memory extraction side agents
* agent-memory snapshots and sync
* remote memory transport
* memory editing UI
* new memory intelligence layers outside current store/quality/recall seams

## Acceptance Criteria

* [x] cc-haha source mapping for H07 is recorded in this stage PRD.
* [x] local H07 MVP closeout slices are explicit.
* [x] focused tests, targeted ruff, and targeted mypy pass for changed files.
* [x] checkpoint records whether H07 becomes implemented or remains partial with an explicit minimal residual.

## cc-haha Alignment

### Expected Effect

Aligning this behavior should improve cross-session continuity, reliability, and maintainability. The local runtime effect is: durable memory stays scope-aware and bounded, while write quality and recall stay explicit instead of turning into an unstructured global note store.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Scoped memory model | session memory, agent memory, and memory-file scope are separate concerns | prevent local memory from collapsing into one global blob | namespace-isolated durable memory contract | partial | Align local namespace/scope contract now |
| Write quality and extraction gate | memory capture is gated and not every transient state becomes memory | keep local long-term memory clean | quality policy + duplicate/transient rejection | align | Close out with current local gate |
| Bounded surfacing and recall | surfaced memory is deduped and scope-aware | prevent cross-namespace leakage and noisy prompt injection | scoped recall + middleware namespace contract | partial | Align current local bounded recall path |
| Richer session/agent memory runtime | upstream includes session-memory extraction, compaction, snapshots, and memory file access hooks | valid future work but broader than current MVP | none | defer | Keep out of Stage 24 |

### Source files inspected

Explorer A inspected:

* `/root/claude-code-haha/src/services/SessionMemory/sessionMemory.ts`
* `/root/claude-code-haha/src/services/SessionMemory/sessionMemoryUtils.ts`
* `/root/claude-code-haha/src/services/SessionMemory/prompts.ts`
* `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
* `/root/claude-code-haha/src/tools/AgentTool/agentMemory.ts`
* `/root/claude-code-haha/src/tools/AgentTool/agentMemorySnapshot.ts`
* `/root/claude-code-haha/src/tools/AgentTool/loadAgentsDir.ts`
* `/root/claude-code-haha/src/utils/memoryFileDetection.ts`
* `/root/claude-code-haha/src/utils/sessionFileAccessHooks.ts`
* `/root/claude-code-haha/src/utils/permissions/filesystem.ts`
* `/root/claude-code-haha/src/utils/attachments.ts`
* `/root/claude-code-haha/src/utils/sessionStorage.ts`

## Technical Approach

* Close H07 with contract hardening rather than a new memory subsystem.
* Pin namespace isolation and duplicate behavior in `test_memory.py`.
* Pin middleware recall scope in `test_memory_integration.py`.
* Explicitly define the MVP H07 boundary as:
  * included: durable namespace-scoped store-backed memory, quality gate, scoped recall, bounded middleware injection
  * deferred: session-memory extraction runtime, agent-memory snapshot lifecycle, memory file hooks, and remote sync

## Checkpoint: Stage 24

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added namespace isolation and duplicate-scope regression coverage for durable memory records.
- Added a middleware namespace-scope regression proving memory injection only surfaces the configured namespace.
- Fixed the H07 MVP boundary as local namespace-scoped memory with bounded recall and quality gating.

Corresponding highlights:
- `H07 Scoped cross-session memory`

Corresponding modules:
- `coding_deepgent.memory.policy`
- `coding_deepgent.memory.store`
- `coding_deepgent.memory.recall`
- `coding_deepgent.memory.middleware`
- `coding_deepgent.memory.tools`

Tradeoff / complexity:
- Chosen: close H07 with namespace/scope contracts on the existing store-backed seam.
- Deferred: richer session-memory extraction, agent-memory snapshots, memory file access hooks, and remote memory sync.
- Why this complexity is worth it now: the MVP needs durable cross-session memory, but not the full upstream memory runtime breadth.

Verification:
- `pytest -q coding-deepgent/tests/test_memory.py coding-deepgent/tests/test_memory_integration.py coding-deepgent/tests/test_memory_context.py`
- `ruff check coding-deepgent/tests/test_memory.py coding-deepgent/tests/test_memory_integration.py`
- `mypy coding-deepgent/src/coding_deepgent/memory/policy.py coding-deepgent/src/coding_deepgent/memory/recall.py coding-deepgent/src/coding_deepgent/memory/tools.py coding-deepgent/tests/test_memory.py coding-deepgent/tests/test_memory_integration.py`

Boundary findings:
- H07 should not imply upstream-style session-memory extraction or agent-memory snapshots in the current MVP.
- Namespace isolation is currently guaranteed by the calling seam (`list_memory_records(namespace)`), so that contract must remain explicit in tests.

Decision:
- continue

Reason:
- Stage 24 is complete and Stage 25 (H08/H09/H10 todo/task/plan/verify closeout) remains the next direct milestone from the canonical dashboard.
