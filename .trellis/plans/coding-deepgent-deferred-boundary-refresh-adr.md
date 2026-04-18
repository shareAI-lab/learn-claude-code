# coding-deepgent Deferred Boundary Refresh ADR

Status: active
Updated: 2026-04-18
Supersedes: Stage 29 deferred-boundary checkpoint in
`.trellis/tasks/archive/2026-04/04-15-stage-29-deferred-boundary-adr-mvp-release-checklist/prd.md`
Scope: `coding-deepgent/` Approach A MVP boundary after 2026-04-17/18 H01, H11/H12, and H19 closeout work

## Purpose

This ADR refreshes the old Stage 29 deferred-boundary note with the concrete
boundaries established by the recent closeout tasks:

- H19 vertical closeout
- H01 capability/projection/pairing/result-pressure closeout
- H11/H12 `AgentDefinition`, real general runtime, sidechain transcript, and
  result-envelope closeout

The goal is to make future reopen requests source-backed and to distinguish:

- intentionally deferred
- implemented-minimal
- do-not-copy

## Source Anchors

Primary source-backed inputs:

- `.trellis/tasks/archive/2026-04/04-15-stage-29-deferred-boundary-adr-mvp-release-checklist/prd.md`
- `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md`
- `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h19-observability-alignment-research.md`
- `.trellis/plans/coding-deepgent-h01-tool-module-alignment-plan.md`
- `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
- `.trellis/spec/backend/tool-capability-contracts.md`
- `.trellis/spec/backend/task-workflow-contracts.md`
- `.trellis/spec/backend/session-compact-contracts.md`
- `.trellis/spec/backend/runtime-pressure-contracts.md`

## Decision

The current Approach A MVP boundary remains:

- keep the local LangChain-native agent harness core strong
- keep the runtime bounded and synchronous where possible
- defer richer agent-team orchestration, background lifecycle, remote control
  plane, and provider-specific observability/caching unless a new source-backed
  PRD demonstrates concrete local benefit

## Deferred Boundaries

### 1. H13 / H14 Agent-Team Runtime

Deferred:

- mailbox / `SendMessage`
- coordinator synthesis runtime
- background worker orchestration
- pending-message drains and cross-agent task inboxes

Why deferred:

- current product has durable task/plan/verify and bounded `run_subagent`
  already; mailbox/coordinator would add a new runtime tier rather than close a
  missing MVP invariant
- no current product surface needs asynchronous team coordination to satisfy
  the MVP boundary
- adding these now would widen the runtime far beyond current local benefit

Reopen only when:

- a new source-backed PRD shows concrete workflow benefit that cannot be met by
  the current task/plan/verifier/subagent path

### 2. H11 / H12 Rich Subagent Lifecycle

Deferred:

- background/async agents
- parent/child abort cascade parity
- per-agent cleanup inventory parity
- task notifications / summary agents
- subagent resume
- per-agent transcript directories
- full fork/cache parity
- implicit fork mode
- exact-tool-inheritance cache-safe fork path

Implemented-minimal and therefore not deferred:

- `AgentDefinition` for `general` and `verifier`
- real read-only `general` child runtime
- plan-bound `verifier`
- structured result envelopes
- sidechain transcript in parent ledger

Why deferred:

- current synchronous child runtime plus sidechain audit already covers the MVP
  correctness boundary
- rich fork/cache/background lifecycle is a second-order optimization/runtime
  broadening, not a missing core behavior
- the current local transcript/session architecture is cleaner with parent-ledger
  sidechain records than with copied cc per-agent directories

Reopen only when:

- a source-backed PRD shows a concrete need for background execution,
  resumable forks, or cache-safe sibling execution beyond today's bounded child
  runtime

### 3. H19 Deferred Observability

Deferred:

- external analytics backend
- Datadog / first-party telemetry exporters
- Perfetto hierarchical tracing
- SDK progress stream / TTFT forwarding
- provider-specific cache / cost / billing instrumentation
- analytics sampling / internal env enrichment
- CLI dump flag (env-gated dumps already exist)

Implemented and therefore not deferred:

- queued runtime event sink
- agent-scoped logger helper
- compact attempted/succeeded split
- `post_autocompact_turn` canary
- `orphan_tombstoned`
- structured `query_error`
- per-turn `token_budget`
- env-gated `CODING_DEEPGENT_DUMP_PROMPTS=1`

Why deferred:

- current local evidence/runtime-event seam already satisfies the MVP debugging
  and recovery boundary
- richer telemetry would add infra/provider coupling without changing local core
  runtime correctness

Reopen only when:

- a new product goal requires latency tracing, external reporting, or provider
  cost/cache decisions in-product

### 4. H01 Deferred Tool Runtime Breadth

Deferred:

- ToolSearch / deferred schema discovery runtime
- streaming tool execution
- non-streaming partition adapter unless proven necessary
- dynamic hot-swap tool pool runtime
- provider-specific shell/permission parity beyond current local policy

Implemented and therefore not deferred:

- five-factor capability contract
- explicit projection/result seams
- dynamic tool-pool projection foundation
- pairing/failure tests
- result persistence / microcompact audit

Special `L5-a` decision:

- `L4-a` research found that LangChain `ToolNode` already gives non-streaming
  parallel execution with stable output order
- therefore `L5-a` remains conditional/spec-only unless `L4-b` / `L4-c` or a
  future runtime failure proves capability-aware partitioning is required

Why deferred:

- current LangChain-native surfaces already satisfy the baseline
- adapter/runtime widening is not justified without a concrete local failure

Reopen only when:

- a source-backed PRD plus local failing tests show that capability-aware
  concurrency partitioning is necessary

### 5. H21 / H22 Remote And Proactive Runtime

Deferred:

- bridge / remote / IDE control plane
- daemon / cron / proactive automation

Why deferred:

- these are explicit next-cycle product bands, not missing local harness
  invariants
- they introduce remote/process/scheduling boundaries that do not belong in the
  current local MVP

Reopen only when:

- a new source-backed product goal explicitly targets remote/IDE or proactive
  automation behavior

## Do-Not-Copy Boundaries

The following cc-haha details remain intentionally not copied into the local
product:

- React/TUI render surfaces
- internal analytics export conventions
- ant-specific support/debug affordances
- provider-specific cache internals where no local product effect exists

## Consequences

- future agents should treat missing mailbox/coordinator/background/fork-cache
  parity as intentional, not accidental
- future implementation should favor the current local abstractions instead of
  reintroducing cc-shaped runtime objects or bridge layers
- if a future reopen happens, it must name the concrete local benefit and the
  exact source evidence, not only "closer to cc"

## Current Fastest Remaining Path

Given the current state, the next remaining topology items are:

- `L5-c` dashboard refresh
- optional `L5-a` only if a new concrete failure appears

Everything else in the current parent topology that was about H01/H11/H12/H19
implementation is now closed.
