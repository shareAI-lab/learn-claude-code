<!-- Created on 2026-04-14 as a reconstructed master plan after partial OMX plan loss. -->
# Reconstructed Master Plan — coding-deepgent

Status: reconstructed working plan
Scope: `coding-deepgent/` only
Intent: consolidate the surviving planning artifacts and current product status into one practical source of truth

## 1. Provenance and Confidence

This document is not claimed to be the original master plan. It is a reconstruction derived from the strongest surviving artifacts.

Some evidence originally came from removed `.omx/...` locations. The paths
listed below are the surviving `.trellis/plans/...` copies that future work
should actually read.

Primary evidence:
- `.trellis/plans/prd-coding-deepgent-runtime-foundation.md`
- `.trellis/plans/test-spec-coding-deepgent-runtime-foundation.md`
- `.trellis/plans/coding-deepgent-runtime-foundation-20260412T213209Z.md`
- `.trellis/plans/runtime-foundation-recovery-notes-2026-04-14.md`
- `coding-deepgent/README.md`
- `coding-deepgent/PROJECT_PROGRESS.md`
- `coding-deepgent/project_status.json`

Confidence levels:
- High confidence: current product stage, stage roadmap count, Stage 3 architecture principles, Stage 3 verification intent
- Medium-high confidence: the architectural continuity from Stage 3 into later stages
- Medium confidence: the exact original wording and sequencing of the lost post-Stage-3 plans

## 2. Product Identity

`coding-deepgent` is an independent cumulative LangChain-native cc-style product surface.

Confirmed product metadata:
- `shape`: `staged_langchain_cc_product`
- `public_shape`: `single cumulative app`
- `current_product_stage`: `stage-11-mcp-plugin-real-loading`
- `compatibility_anchor`: `mcp-plugin-real-loading`
- `architecture_reshape_status`: `s1-skeleton-complete`
- upgrade policy: advance by explicit product-stage plan approval, not tutorial chapter completion

## 3. Core Planning Principles

These principles are directly supported by the restored runtime-foundation PRD and remain the most reliable long-term planning rules.

1. Domain-first, LangChain-inside
   LangChain and LangGraph remain the runtime boundary, while product capabilities are organized into explicit domains.
2. Explicit dependency graph
   Use dependency-injector containers for composition, overrides, and backend selection; do not hide business logic in containers.
3. High cohesion, low coupling
   Each domain owns one product concept and communicates through explicit seams rather than ad hoc imports.
4. Functional skeleton over empty architecture
   New stages must land as working product slices, not placeholder module trees.
5. No clone drift
   Preserve cc-aligned behavior where needed, but do not mirror source layout mechanically and do not bypass LangChain runtime seams.

## 4. Architectural Baseline

The recovered Stage 3 PRD defined the baseline professional runtime skeleton. Current code and status files indicate that this baseline still governs the product.

Stable architecture expectations:
- `runtime` owns invocation, context, state, and runtime seams
- `containers` owns composition only
- `tool_system` owns capability registry, policy, and guard behavior
- `filesystem`, `todo`, and `sessions` are first-class product domains
- later domains grow explicitly rather than being folded into `runtime` or `sessions`
- CLI remains a professional shell over product services rather than the product core itself

Boundary rules that should still be treated as active:
- domain modules do not import `containers`
- `containers/*` does not own business rules
- `tool_system` must not become a god module
- `sessions` must remain transcript/resume scoped, not absorb unrelated durable product state
- LangChain-native seams stay intact: `create_agent`, `context=`, LangGraph `thread_id`, middleware-driven control

## 5. Stage Model

Confirmed total stage count: 11

The surviving roadmap establishes the following cumulative product stages:

1. Stage 1: TodoWrite / todos / activeForm product contract
2. Stage 2: architecture gate for filesystem / tool-system / session seams
3. Stage 3: professional domain runtime foundation
4. Stage 4: control-plane foundation
5. Stage 5: memory / context / compact foundation
6. Stage 6: skills / subagents / durable task graph
7. Stage 7: local MCP / plugin extension foundation
8. Stage 8: recovery / evidence / runtime-continuation foundation
9. Stage 9: permission / trust-boundary hardening
10. Stage 10: hooks / lifecycle expansion
11. Stage 11: MCP / plugin real loading

## 6. Stage Intent Summary

### Stage 1

Establish the public planning contract around `TodoWrite(todos=[...])` and required `activeForm`.

### Stage 2

Separate the early runtime into clearer seams for filesystem, tool system, and session behavior.

### Stage 3

Establish the professional runtime skeleton:
- typed settings
- dependency-injector composition
- Typer and Rich CLI surface
- runtime context and state seams
- domain packages for filesystem, todo, sessions, tool system
- local events and guard infrastructure

This is the strongest historically recovered stage because both PRD and test spec survive.

### Stage 4

Add deterministic control-plane behavior:
- permissions
- hooks
- structured prompt/context assembly

### Stage 5

Add bounded long-term memory and context-control foundations:
- store-backed memory seam
- model-visible memory save path
- deterministic tool-result budget helpers

### Stage 6

Add local skill loading, durable task graph, and minimal synchronous subagent capability.

### Stage 7

Add local MCP/plugin extension seams:
- MCP tool descriptor adaptation
- separate MCP resource read surfaces
- strict local plugin manifest declarations

### Stage 8

Add recovery and evidence:
- session evidence records
- recovery brief generation
- default CLI runtime wired to real local session storage

### Stage 9

Harden permissions and trust boundaries:
- typed settings-backed permission rules
- explicit trusted extra workspaces
- capability trust metadata for builtin vs extension tools

### Stage 10

Promote hooks from passive registry to actual lifecycle integration:
- `SessionStart`
- `UserPromptSubmit`
- `PreToolUse`
- `PostToolUse`
- `PermissionDenied`

### Stage 11

Upgrade MCP/plugin from declaration-level support to real loading:
- typed root `.mcp.json`
- adapter-backed MCP tool loading when available
- plugin declaration validation against known local capabilities and skills

## 7. What Is Confirmed Implemented Now

Based on current status documents, these claims are currently asserted by the project itself:

- product stage is at Stage 11
- the Stage 3 skeleton has been reshaped into an `s1-skeleton-complete` baseline
- current architecture includes explicit domains for:
  - runtime
  - permissions
  - hooks
  - prompting/context
  - memory
  - compact helpers
  - local skills
  - durable tasks
  - bounded subagents
  - local MCP tool registration/loading
  - local plugin manifests

These are project-state claims, not yet independently re-audited in this document.

## 8. Open Gaps in the Recovered Planning Record

The following are still missing or only weakly supported:

- original detailed PRDs for Stages 4 through 11
- stage-by-stage test specs after Stage 3
- ADR-style records for major deviations taken during later implementation
- explicit “done / partial / deferred” matrices for each post-Stage-3 stage
- any original prioritization notes for future stages beyond the current Stage 11 anchor

## 9. Practical Working Rules Going Forward

Until stronger historical plan files are recovered, future planning should treat this document as the operational master index and use the following rules:

1. Treat the restored Stage 3 PRD and test spec as the strongest architectural authority.
2. Treat `coding-deepgent/PROJECT_PROGRESS.md` and `coding-deepgent/README.md` as the authoritative current stage ledger.
3. Do not infer missing post-Stage-3 details as if they were historical facts; label them explicitly as reconstruction or new planning.
4. Before any new stage work, re-check it against the Stage 3 boundary rules:
   - domain ownership
   - container purity
   - LangChain-native runtime seams
   - no central god modules
5. When new plans are written, attach test/verification expectations at the same time so the planning record does not again split into architecture without acceptance criteria.

## 10. Recommended Next Planning Actions

1. Create a stage audit document for Stages 4 through 11 with columns:
   - intended capability
   - current implementation evidence
   - gaps
   - deferred items
2. Reconstruct or newly author post-Stage-3 PRDs one stage at a time, starting with the current Stage 11 anchor and the next intended stage after it.
3. Add a single index file in `.omx/plans/` that lists all authoritative planning artifacts and their confidence levels.
4. When a stage is materially complete, update both:
   - `coding-deepgent/PROJECT_PROGRESS.md`
   - `coding-deepgent/project_status.json`

## 11. Source Map

Use these files together:

- [Runtime Foundation PRD](/root/learn-claude-code/.trellis/plans/prd-coding-deepgent-runtime-foundation.md)
- [Runtime Foundation Test Spec](/root/learn-claude-code/.trellis/plans/test-spec-coding-deepgent-runtime-foundation.md)
- [Recovery Notes](/root/learn-claude-code/.trellis/plans/runtime-foundation-recovery-notes-2026-04-14.md)
- [Current Product README](/root/learn-claude-code/coding-deepgent/README.md)
- [Current Progress Ledger](/root/learn-claude-code/coding-deepgent/PROJECT_PROGRESS.md)
- [Current Status JSON](/root/learn-claude-code/coding-deepgent/project_status.json)
