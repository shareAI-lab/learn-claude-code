# coding-deepgent Project Handoff

Updated: 2026-04-18
Primary branch: `codex/stage-12-14-context-compact-foundation`
Primary PR: `#220` `https://github.com/shareAI-lab/learn-claude-code/pull/220`

## Product Goal

`coding-deepgent` is the product track that should implement the essential `cc-haha` / Claude Code runtime logic through LangChain/LangGraph-native primitives, while staying professional-grade, modular, maintainable, and non-demo.

Canonical goal/backlog docs:

* `.trellis/tasks/04-14-redefine-coding-deepgent-final-goal/prd.md`
* `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`

## Minimal Resume Procedure

Use this file as the canonical Trellis replacement for the old
`project-handoff` skill.

When starting a new `coding-deepgent` session, do this in order:

1. Read this file.
2. Read only these canonical docs:
   * `.trellis/tasks/04-14-redefine-coding-deepgent-final-goal/prd.md`
   * `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
   * `coding-deepgent/PROJECT_PROGRESS.md`
   * `.trellis/spec/backend/runtime-context-compaction-contracts.md`
   * `.trellis/spec/backend/task-workflow-contracts.md`
3. Refresh live state only with:
   * `git branch --show-current`
   * `git status -sb`
   * `gh pr view 220 --repo shareAI-lab/learn-claude-code --json number,title,url,isDraft,headRefName,baseRefName`
4. Read latest stage PRDs only if a real ambiguity remains.

## Update Policy

Update this handoff only when mainline resume context materially changes.

Update it when:

* current mainline stage family changes
* canonical roadmap/dashboard status changes
* latest verified state changes
* next recommended task changes
* a new cross-session product requirement becomes canonical
* the minimal resume reading order changes

Do not update it for ordinary daily progress, minor implementation notes, or
session summaries. Those belong in workspace journals via `record-session`.

This file is a compact resume entrypoint, not a full project history.

## Current Mainline

Current mainline has focused on:

* context / compact / session / recovery hardening
* durable task / workflow hardening
* cc-highlight topology closeout for H01, H11/H12, and H19

Latest completed stage families:

* Stage 12: Context and Recovery Hardening
* Stage 13: Context Compaction v1
* Stage 14A: Explicit Generated Summary CLI Wiring
* Stage 15: Compact Persistence Semantics
* Stage 16: Virtual Transcript Pruning
* Stage 17A/17B/17C/17D: Durable Task and Workflow Hardening
* Stage 18A/18B: Verifier Execution and Evidence Integration
* Stage 19A/19B: Evidence Observability and Verifier Lineage
* Stage 20: Canonical MVP Completion Dashboard
* Stage 21: Tool And Permission Closeout
* Stage 22: Prompt And Dynamic Context Closeout
* Stage 23: Context Pressure And Session Continuity Closeout
* Stage 24: Scoped Memory Closeout
* Stage 25: Todo Task Plan Verify Closeout
* Stage 26: Agent As Tool MVP Closeout
* Stage 27: Local Extension Platform Closeout
* Stage 28: Observability Evidence Closeout
* Stage 29: Deferred Boundary ADR And MVP Release Checklist
* 2026-04-17 H19 Vertical Closeout
* 2026-04-17 H01 L1-c Capability Audit

## Latest Verified State

Latest completed stages and what they changed:

* `17A`: durable task graph invariants
  * rejects missing dependencies, self-dependencies, cycles
  * exposes `ready` in `task_list`
* `17B`: verification workflow boundary
  * emits `verification_nudge` when a 3+ task graph closes without a verification task
* `17C`: explicit plan artifacts
  * `PlanArtifact`, `plan_save`, `plan_get`
  * required `verification` field
  * separate plan namespace from task namespace
* `17D`: verifier execution boundary
  * verifier subagent requires `plan_id`
  * verifier resolves durable plan artifact before execution
  * verifier returns structured JSON result
  * verifier allowlist includes `plan_get`, excludes `plan_save`
* `18A`: verifier execution integration
  * verifier executes through a real bounded child-agent path
  * verifier uses a dedicated read-only system prompt
  * verifier keeps a fixed read-only tool allowlist
  * verifier preserves structured JSON result output
* `18B`: verifier result persistence and evidence integration
  * verifier `VERDICT: PASS|FAIL|PARTIAL` results persist into session evidence
  * verifier evidence roundtrips through `JsonlSessionStore.load_session()`
  * recovery briefs expose verifier evidence through the existing evidence path
  * verifier persistence reuses the session ledger and does not mutate tasks/plans
* `19A`: verifier evidence provenance in recovery briefs
  * recovery brief renders concise `plan=...` / `verdict=...` provenance for verification evidence
  * arbitrary evidence metadata is not dumped into resume context
* `19B`: verifier evidence lineage metadata
  * verifier evidence records include parent session/thread and child verifier thread/agent lineage
  * verifier JSON result and task/plan state remain unchanged
* `20`: canonical MVP completion dashboard
  * H01-H22 now have one canonical roadmap/dashboard file
  * Approach A MVP boundary is fixed
  * Stage 21-29 sequencing and Stage 30-36 reserve are explicit
* `21`: tool and permission closeout
  * builtin tool-name collisions are now rejected before capability projection
  * H01/H02 have explicit contract tests for exposure projection, policy-code mapping, pattern safety, and container wiring
* `22`: prompt and dynamic context closeout
  * H03 has direct settings-backed prompt layering tests
  * H04 has a model-call composition test covering resume history, todo context, and memory context ordering
  * H04 MVP boundary is explicitly narrowed to resume/todo/memory/compact flows; skills/resources remain deferred
* `23`: context pressure and session continuity closeout
  * H05 has projection-chain regression coverage for mixed plain/structured/metadata messages
  * H06 has a combined resume/compact/evidence continuity regression
  * evidence CLI remains optional and is not required for MVP
* `24`: scoped memory closeout
  * H07 is fixed as local namespace-scoped durable memory with quality gating and bounded recall
  * richer session-memory extraction and agent-memory snapshot runtime remain deferred
* `25`: todo/task/plan/verify closeout
  * H08 TodoWrite is fixed as session-local bounded short-term planning
  * H09 durable task graph has terminal visibility and verification-recognition regressions
  * H10 plan/verify remains explicit and verifier-backed; coordinator/mailbox are deferred
* `26`: agent-as-tool MVP closeout
  * H11 is fixed as bounded `run_subagent` tool surface with real verifier child execution
  * H12 is fixed only as minimal context/thread propagation; rich fork/cache parity is deferred
* `27`: local extension platform closeout
  * H15 skills, H16 MCP, and H18 hooks are closed for local MVP
  * H17 is closed as local manifest/source validation only; full install/enable lifecycle is deferred
* `28`: observability evidence closeout
  * H19 persists whitelisted `hook_blocked` and `permission_denied` runtime events into session evidence
  * H20 is closed as minimal local budget/projection/compact counters; rich provider-specific cost/cache instrumentation is deferred
* `29`: deferred-boundary ADR and MVP release checklist
  * H01-H22 have explicit statuses in the canonical dashboard
  * H13/H14/H21/H22 are deferred out of Approach A MVP
  * Stage 30-36 reserve is not currently required unless later validation finds a concrete MVP gap
* `2026-04-17 H19 vertical closeout`: observability/evidence cleanup
  * `L1-b`, `L2-b`, and `L3-b` are complete under `.trellis/tasks/04-17-cc-core-topology-closeout-plan/`
  * H19 now includes queued `RuntimeEventSink`, agent-scoped logger, AutoCompact attempted/succeeded events, `post_autocompact_turn` canary metrics, `orphan_tombstoned` projection repair, structured `query_error`, per-turn `token_budget`, and env-gated `CODING_DEEPGENT_DUMP_PROMPTS=1` dumps
  * External analytics backend, Perfetto, SDK/TTFT progress, provider cache/cost, and CLI dump flag remain deferred and should be covered by `L5-b` ADR refresh
* `2026-04-17 H01 L1-c capability audit`: five-factor tool metadata cleanup
  * `ToolCapability` now carries explicit five-factor metadata, including `rendering_result`
  * capability registry validation enforces name/schema/metadata/exposure and large-output/microcompact opt-in invariants
  * downstream H01 role projection, dynamic pool, pairing, and concurrency work remain open
* `2026-04-17/18 H01/H11/H12 closeout follow-through`
  * `H11` now has `AgentDefinition`, a real read-only `general` child runtime, structured subagent result envelopes, and sidechain transcript audit in the parent session ledger
  * `H01` now has role-based projection, explicit `ToolPoolProjection`, pairing/failure regressions, and result-persistence/microcompact audit closeout
* `2026-04-18 deferred-boundary ADR refresh`
  * `.trellis/plans/coding-deepgent-deferred-boundary-refresh-adr.md` supersedes the old Stage 29 deferred note for H11/H12/H19/H01-adjacent deferred items
  * `L5-a` is now explicitly conditional/spec-only unless later tests reveal a real capability-aware partitioning gap

## Current Active Topology

Use this as the current planning entry point:

* Parent task: `.trellis/tasks/04-17-cc-core-topology-closeout-plan/`
* Done: `L1-b`, `L1-c`, `L2-a`, `L2-b`, `L2-c`, `L3-a`, `L3-b`, `L3-c`, `L4-a`, `L4-b`, `L4-c`
* Remaining: docs-only tail `L5-c` dashboard refresh
* `L5-a` remains conditional only and should stay dormant unless a concrete concurrency-partition failure is discovered

## Current Contracts

Read these before coding in the current mainline:

* `.trellis/spec/backend/runtime-context-compaction-contracts.md`
* `.trellis/spec/backend/task-workflow-contracts.md`

## Current Product Modules

Core domains:

* `runtime`
* `tool_system`
* `filesystem`
* `todo`
* `sessions`
* `memory`
* `compact`
* `permissions`
* `hooks`
* `skills`
* `tasks`
* `subagents`
* `mcp`
* `plugins`
* `prompting`

## Next Recommended Task

Next planned direction:

* complete the final `L5-c` canonical dashboard refresh for H11/H12/H19/H01 topology closeout

Intent:

* update the roadmap/dashboard to reflect the now-completed H01/H11/H12/H19 implementation items
* keep `L5-a` conditional and avoid reviving it by default
* leave H13/H14/H21/H22 deferred unless a new source-backed PRD reopens them

## Planning Gate

Before any new stage implementation begins, the proposal must state:

* the concrete function being added or changed
* the concrete user/system benefit it brings
* why the benefit is worth the added complexity now

“Closer to cc” alone is not sufficient.

## Persistent User Requirement

Cross-session memory is a product requirement.

Refactor posture is also a product requirement for current transcript/context
engineering work:

* do not prioritize compatibility with old local schema/design when that blocks
  a cleaner long-term foundation
* do not add fallback paths only to preserve legacy local data shapes
* prefer durable long-term architecture and clean domain boundaries over
  minimizing short-term blast radius
* when a transcript/runtime foundation choice is ambiguous, bias toward the
  design that better supports future compact/collapse/timeline infrastructure
  even if it requires replacing current local abstractions

Interpretation for current planning:

* durable user-relevant information must survive session resume boundaries
* future stages should prefer durable memory/evidence/session mechanisms that improve cross-session continuity
* stage proposals must say explicitly whether they advance cross-session memory directly, indirectly, or not at all
* transcript/context refactors may replace current local compact/count/index
  designs instead of preserving them as compatibility bridges
* old local data compatibility is not a default requirement unless the user
  explicitly reintroduces it later

Delivery preference for current planning:

* for high-value, strongly coupled feature families with a clear boundary,
  prefer one integrated optimization pass over artificially tiny visible
  increments
* keep internal checkpoints and evidence, but do not present work as
  "toothpaste squeezing" when the family can be completed safely in one run
* only split the family when a real safety, architecture, or verification
  blocker appears

## Resume Strategy

When starting a new session:

1. Read this handoff file first.
2. Refresh live state:
   * `git branch --show-current`
   * `git status -sb`
   * `gh pr view 220 --repo shareAI-lab/learn-claude-code --json number,title,url,isDraft,headRefName,baseRefName`
3. Read only the latest relevant PRDs if needed:
   * `.trellis/tasks/04-15-stage-17c-explicit-plan-artifact-boundary/prd.md`
   * `.trellis/tasks/04-15-stage-17d-verifier-subagent-execution-boundary/prd.md`
   * `.trellis/tasks/04-15-stage-18a-verifier-execution-integration/prd.md`
   * `.trellis/tasks/04-15-stage-18b-verifier-result-persistence-evidence-integration/prd.md`
   * `.trellis/tasks/04-15-stage-19-evidence-observability-agent-lifecycle-hardening/prd.md`
   * `.trellis/tasks/04-15-coding-deepgent-highlight-completion-map/prd.md`
   * `.trellis/tasks/04-15-stage-29-deferred-boundary-adr-mvp-release-checklist/prd.md`

## Cost Control

Default to Trellis `lean` staged-execution mode:

* auto-progress sub-stages
* avoid large re-reads unless a real ambiguity appears
* prefer focused tests
* avoid broad docs/git/PR work unless explicitly requested

For the checkpoint state machine and `continue / adjust / split / stop`
discipline, use `.trellis/spec/guides/staged-execution-guide.md`.
