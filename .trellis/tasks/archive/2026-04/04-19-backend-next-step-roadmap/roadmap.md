# Backend Next-Step Roadmap

Status: implemented through Stage 2  
Scope: `coding-deepgent/` backend / runtime mainline only  
Updated: 2026-04-19

## Current Reading

The current product is no longer missing its core runtime skeleton.

What is already in place:

- `H01-H12`, `H15-H20` have local MVP coverage in canonical Trellis docs.
- core domains are already separated into `runtime`, `tool_system`, `sessions`,
  `memory`, `tasks`, `subagents`, `mcp`, and `plugins`.
- `coding-deepgent/tests` has broad regression coverage.

What is still visibly unstable:

- public tool-surface expectations are drifting from the actual subagent/fork tools
- memory extraction queue behavior is not safely isolated for all test/local paths
- hook runtime evidence metadata has contract drift
- some handoff/dashboard wording still reflects an earlier checkpoint state

Decision:

- do **not** reopen mailbox/coordinator/remote/daemon by default
- first restore one clean release baseline
- then add the next highest-leverage cc-aligned backend capabilities

## Priority Order

1. Release cleanup and contract lock
2. ToolSearch / deferred tool discovery
3. Subagent / fork contract consolidation
4. Secondary backlog only after the above are green

## Stage 0: Release Cleanup And Contract Lock

Status: completed on 2026-04-19

### Why Now

The current branch is close to a post-MVP cleanup point, but it is not yet a
clean baseline. Expanding the runtime before the existing contracts are locked
would compound drift.

### Acceptance Targets

- `pytest -q coding-deepgent/tests` is green again.
- one explicit answer exists for which subagent/fork tools belong in the main
  public tool surface today
- `agent_loop` local/test paths do not require a live Redis dependency by default
- hook evidence metadata is stable across runtime events, session evidence, and tests
- handoff/dashboard wording matches the actual completed topology state

### Planned Features

- align `app`/bootstrap tool binding expectations with the real current
  subagent/fork/background surface
- make memory queue behavior safe for test/local non-network execution
- normalize hook evidence metadata contract and update tests/docs accordingly
- refresh handoff wording so the next suggested task is not stale

### Target Modules

- `coding-deepgent/src/coding_deepgent/app.py`
- `coding-deepgent/src/coding_deepgent/bootstrap.py`
- `coding-deepgent/src/coding_deepgent/agent_loop_service.py`
- `coding-deepgent/src/coding_deepgent/memory/queue.py`
- `coding-deepgent/src/coding_deepgent/memory/service.py`
- `coding-deepgent/src/coding_deepgent/hooks/dispatcher.py`
- `coding-deepgent/tests/test_app.py`
- `coding-deepgent/tests/test_hooks.py`

### Verification

- `pytest -q coding-deepgent/tests`
- targeted review that public tool names, queue semantics, and evidence metadata
  are consistent across code, docs, and tests

### Planned Extensions

- no new user-facing runtime family should start in this stage
- do not widen into ToolSearch, mailbox, or coordinator here

## Stage 1: ToolSearch / Deferred Tool Discovery

Status: completed on 2026-04-19

### Why Now

This is the next highest-leverage backend gap. The codebase already has
five-factor capability metadata and explicit `main` / `child` / `extension` /
`deferred` projection foundations, but no real deferred discovery runtime.

This feature improves:

- prompt/context pressure
- MCP / extension scalability
- tool-surface hygiene
- future cache-safe prompt shaping

### Acceptance Targets

- the main agent can keep a smaller visible tool surface without losing access
  to deferred capabilities
- the runtime has one explicit way to discover deferred tools and reveal their
  schema/usage on demand
- extension/MCP tools can participate in the same deferred-discovery contract
  without bypassing capability registry validation
- tests prove deferred tools do not break projection, pairing, or tool-result
  contracts

### Planned Features

- add a `ToolSearch`-style runtime surface for deferred capabilities
- extend tool capability metadata only where needed to support discovery,
  rendering, and safe schema reveal
- define how deferred builtin, MCP, and plugin tools are indexed and exposed
- keep discovery explicit rather than dynamic hot-swap magic

### Target Modules

- `coding-deepgent/src/coding_deepgent/tool_system/capabilities.py`
- `coding-deepgent/src/coding_deepgent/tool_system/middleware.py`
- `coding-deepgent/src/coding_deepgent/mcp/`
- `coding-deepgent/src/coding_deepgent/plugins/`
- `coding-deepgent/src/coding_deepgent/prompting/builder.py`
- `coding-deepgent/tests/test_tool_system_registry.py`
- `coding-deepgent/tests/test_mcp.py`
- `coding-deepgent/tests/test_prompting.py`

### Verification

- projection tests covering `main`, `child`, `extension`, and `deferred`
- integration tests showing deferred tool lookup followed by real execution
- prompt/context budget checks confirming the visible tool surface can shrink

### Planned Extensions

- dynamic hot-swap tool pools
- streaming tool execution
- provider-specific prompt-cache tuning
- concurrency partition adapter unless a failing test proves it is needed

## Stage 2: Subagent / Fork Contract Consolidation

Status: completed on 2026-04-19

### Why Now

The local H11/H12 slice is already deeper than the old README language:
background runs, status polling, send-input continuation, stop/cancel, and
resume paths already exist. The missing piece is not raw capability, but one
stable product contract across code, tests, docs, and tool exposure.

### Acceptance Targets

- one canonical public contract exists for:
  - `run_subagent`
  - `run_fork`
  - background execution
  - status polling
  - follow-up input
  - stop/cancel
  - resume
- main-agent exposure and documentation match the actual supported local slice
- sidechain/background state is inspectable and resumable without contract
  ambiguity
- current local slice is clearly separated from deferred mailbox/coordinator work

### Planned Features

- freeze the intended local tool surface for subagent/fork operations
- consolidate schema naming, result-envelope wording, and background-run records
- align sidechain transcript, notification evidence, and resume metadata docs
- make the distinction between synchronous child runtime and richer agent-team
  orchestration explicit

### Target Modules

- `coding-deepgent/src/coding_deepgent/subagents/tools.py`
- `coding-deepgent/src/coding_deepgent/subagents/background.py`
- `coding-deepgent/src/coding_deepgent/subagents/schemas.py`
- `coding-deepgent/src/coding_deepgent/sessions/store_jsonl.py`
- `coding-deepgent/tests/test_subagents.py`
- `coding-deepgent/tests/test_app.py`
- `.trellis/project-handoff.md`
- `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`

### Verification

- focused `test_subagents.py` contract coverage
- `test_app.py` alignment coverage for main public tool surface
- docs review confirming H11/H12 implemented-minimal scope is explicit

### Planned Extensions

- implicit fork mode
- exact-tool-inheritance cache-safe fork parity
- mailbox / `SendMessage`
- coordinator synthesis runtime
- richer background worker orchestration

## Stage 3: Secondary Backlog After The Baseline Is Stable

These are valid candidates only after Stage 0-2 are complete:

- plugin lifecycle deepening beyond manifest/source validation
- richer permission ask / interactive approval state machine
- stronger local async job/worker contracts that support future agent-team work
- richer observability and provider-specific cost/cache telemetry

These should not start by default. Each one needs its own source-backed PRD.

## Explicitly Deferred

Still deferred unless product direction changes:

- `H13` mailbox / `SendMessage`
- `H14` coordinator synthesis runtime
- `H21` bridge / remote / IDE control plane
- `H22` daemon / cron / proactive automation
- provider-specific telemetry, billing, TTFT, and cache internals

## Recommended Next Execution Slice

If choosing only one immediate task, do this:

1. close Stage 0 and get back to a clean test baseline
2. then open a focused PRD for Stage 1 ToolSearch / deferred tool discovery

That ordering keeps the codebase reliable while still moving toward the most
valuable remaining cc-aligned backend gap.
