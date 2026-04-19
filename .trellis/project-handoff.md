# coding-deepgent Project Handoff

Updated: 2026-04-20
Primary branch: `codex/stage-12-14-context-compact-foundation`
Primary PR: `#220` `https://github.com/shareAI-lab/learn-claude-code/pull/220`

## Product Goal

`coding-deepgent` is the product track that should progressively approach real
Claude Code public behavior in a professional local coding-agent product, while
using:

* `cc-haha` as the primary open-source implementation reference
* LangChain/LangGraph-native architecture for hidden implementation where that
  does not block important local product behavior

The old `Approach A MVP` line is now historical baseline evidence, not the
default stop condition.

Canonical goal/backlog docs:

* `.trellis/tasks/archive/2026-04/04-14-redefine-coding-deepgent-final-goal/prd.md`
* `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`
* `.trellis/plans/coding-deepgent-circle-2-expanded-parity-plan.md`
* `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md` (historical MVP dashboard)

## Minimal Resume Procedure

Use this file as the canonical Trellis replacement for the old
`project-handoff` skill.

When starting a new `coding-deepgent` session, do this in order:

1. Read this file.
2. Read only these canonical docs:
   * `.trellis/tasks/archive/2026-04/04-14-redefine-coding-deepgent-final-goal/prd.md`
   * `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`
   * `coding-deepgent/PROJECT_PROGRESS.md`
   * `.trellis/spec/guides/cc-alignment-guide.md`
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

Current mainline historical baseline has focused on:

* context / compact / session / recovery hardening
* durable task / workflow hardening
* cc-highlight topology closeout for H01, H11/H12, and H19

Current default direction has now changed:

* treat the MVP closeout line as verified baseline
* stop using MVP closeout as the default product finish line
* begin Circle 1 of the full local daily-driver parity roadmap
* prioritize runtime/core parity before broad CLI/TUI polish
* evaluate progress primarily through three representative workflows rather
  than only by highlight checklist closeout

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
  * H12 is fixed as one bounded local fork/continuity slice; rich fork/cache parity is still deferred
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
* `2026-04-19 backend-next-step Stage 1/2 closeout`
  * H01 now includes `ToolSearch` plus `invoke_deferred_tool` so deferred builtin and MCP capabilities can stay off the initial main tool list while remaining discoverable and executable through the shared policy/middleware path
  * advanced subagent lifecycle controls (`run_subagent_background`, `subagent_status`, `subagent_send_input`, `subagent_stop`, `resume_subagent`, `resume_fork`) now live on the deferred discovery surface instead of the initial main tool surface
  * MCP capabilities now default to the deferred discovery surface, while preserving source/trust metadata and registry validation
* `2026-04-20 Circle 1 Wave 2 runtime-exposing surfaces pack`
  * `coding-deepgent sessions inspect` renders loaded-session metadata, recovery brief, selected raw/compact/collapse projection mode, compression timeline, model projection rows, raw transcript visibility, and current-session memory freshness
  * frontend protocol now includes `context_snapshot` and `subagent_snapshot` events so runtime projection and sidechain activity can reach renderer-neutral consumers without exposing raw JSONL records
  * React/Ink CLI now renders context, durable task, and subagent panels from reducer state in addition to todo, permission, message, and recovery surfaces
* `2026-04-20 Circle 1 Wave 2 control surfaces pack`
  * runtime store now has a local `file` backend, making task/plan/runtime-store state survive process boundaries inside one workspace
  * `coding-deepgent tasks ...` and `coding-deepgent plans ...` now provide real user-facing control over the durable task/plan store
  * frontend bridge now supports `refresh_snapshots`, `run_background_subagent`, `subagent_send_input`, and `subagent_stop` for the active TUI process, plus `background_subagent_snapshot` visibility
* `2026-04-20 Circle 1 completion pack`
  * `coding-deepgent sessions history|projection|timeline|evidence|events|permissions` expose resume/history/projection/recovery state without raw JSONL inspection
  * `coding-deepgent skills|mcp|hooks|plugins list|inspect|validate|debug` expose usable local extension inspect/debug seams
  * `coding-deepgent acceptance circle1` records the deterministic local Circle 1 acceptance boundary for workflows A/B/C
* `2026-04-20 Circle 2 planning`
  * `.trellis/plans/coding-deepgent-circle-2-expanded-parity-plan.md` defines the substrate-first Circle 2 execution sequence
  * Circle 2 Wave 1 should start with durable daemon/worker/event substrate before mailbox/coordinator/remote features
* `2026-04-20 Circle 2 expanded parity local baseline`
  * local durable domains now exist for `event_stream`, `worker_runtime`, `mailbox`, `teams`, `remote`, `extension_lifecycle`, and `continuity`
  * CLI surfaces now cover events, workers, mailbox, teams, remote records/replay, extension lifecycle, continuity artifacts, and `acceptance circle2`
  * this is a local baseline and intentionally does not claim hosted SaaS ingress, multi-user auth, public marketplace backend, or cross-machine workers

## Current Active Topology

Use this as the current planning entry point:

* Parent task: `.trellis/tasks/04-17-cc-core-topology-closeout-plan/`
* Done: `L1-b`, `L1-c`, `L2-a`, `L2-b`, `L2-c`, `L3-a`, `L3-b`, `L3-c`, `L4-a`, `L4-b`, `L4-c`, `L5-b`, `L5-c`
* Remaining: no required topology implementation items are open
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

* Circle 1 and Circle 2 local baselines are implemented
* next work should be release/PR validation and any concrete regression fixes
  found by `coding-deepgent acceptance circle1` / `circle2`
* further parity after this baseline should explicitly target hosted remote
  ingress, true daemon supervision, or marketplace backend only if requested

Intent:

* use real Claude Code public behavior as the top-level target
* use `cc-haha` as the default open-source reference
* use OSS fallback research when both are insufficient
* keep Circle 1 focused on local daily-driver parity, not mailbox/team-runtime or remote/daemon surfaces
* do not reopen Wave 1 runtime-core scope unless a regression or concrete
  daily-driver blocker appears

## Planning Gate

Before any new stage implementation begins, the proposal must state:

* the Circle (`Circle 1` or later) it belongs to
* the representative workflow(s) it improves
* the concrete function being added or changed
* the concrete user/system benefit it brings
* the target Claude Code behavior
* the `cc-haha` source evidence when available
* whether OSS fallback research was needed
* why the benefit is worth the added complexity now

“Closer to cc” alone is not sufficient; the proposal must name the target
behavior and evidence tier.

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
