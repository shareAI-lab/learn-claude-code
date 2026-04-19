# coding-deepgent Circle 1 Wave 1 Runtime-Core Parity Plan

Status: implemented checkpoint
Updated: 2026-04-20
Parent roadmap: `.trellis/plans/coding-deepgent-full-cc-parity-roadmap.md`
Scope: `coding-deepgent/` local daily-driver parity, Circle 1 / Wave 1 only

## Purpose

This plan turns Circle 1 / Wave 1 from a broad roadmap label into a concrete
planning slice for implementation.

Wave 1 is the runtime-core parity pass that must land before broad CLI/TUI
polish or extension-ecosystem improvement can be planned coherently.

## Acceptance Targets

* The runtime core is strong enough to support the three Circle 1 acceptance
  workflows without leaning on the old “MVP complete” label as proof.
* We can point to a prioritized set of feature families whose improvement is
  necessary for:
  - PR-level independent completion
  - single-day long-task continuity
  - personal-efficiency amplification via task/subagent/fork
* Future implementation tasks can be created from this plan without reopening
  the top-level Circle 1 scope question every turn.
* Wave 1 explicitly distinguishes:
  - high-priority parity gaps
  - currently-strong-enough baseline areas
  - intentionally deferred areas that belong to Wave 2 or Circle 2

## Planned Features

* Group Wave 1 into a small number of runtime-core feature families.
* For each family, state:
  - why it matters now
  - which acceptance workflow(s) it unlocks
  - which modules it primarily touches
  - what the current baseline already provides
  - what still blocks daily-driver parity
* Define the recommended order for implementation after this planning pass.
* Name concrete follow-up task families to create next.

## Planned Extensions

* runtime-exposing CLI/TUI parity surfaces such as history/projection inspect,
  richer resume UX, and task/subagent interaction UX
* usable local extension-seam follow-up for skills/MCP/hooks/plugins
* Circle 2 team-runtime/remote/daemon parity
* cross-day continuity, richer memory extraction, and broader automation

## Why Now

The current product has a strong MVP baseline, but Wave 1 must decide where
that baseline is still only “MVP-complete” rather than “daily-driver parity
capable.” Without this decomposition, future work will oscillate between random
feature grabbing and vague “closer to cc” ambitions.

## Out of Scope

* broad CLI/TUI polish
* mailbox/coordinator/team-runtime parity
* remote / IDE / daemon control plane
* plugin marketplace / install / distribution lifecycle
* implementation details for any one feature family

## Acceptance Workflows Served

### Workflow A: Repository Takeover And Sustained Coding

Success standard:

* PR-level independent completion on a medium-to-large codebase

Most relevant families:

* F1 tool/runtime control loop
* F2 context/session continuity
* F3 planning/task execution discipline

### Workflow B: Long Session Continuity

Success standard:

* single-day long-task continuity across multiple rounds of pressure and resume

Most relevant families:

* F2 context/session continuity
* F4 observability/evidence for recovery/debugging

### Workflow C: Complex Task Decomposition

Success standard:

* bounded task/subagent/fork assistance materially increases single-developer
  throughput

Most relevant families:

* F3 planning/task execution discipline
* F5 bounded local subagent/fork runtime

## Feature Families

### F1: Tool / Permission / Prompt / Runtime Control Loop

Primary modules:

* `tool_system`
* `permissions`
* `prompting`
* `runtime`

Why now:

* This family governs whether the agent can safely and predictably perform
  independent PR-level work.
* If this family remains only “MVP-safe” rather than “daily-driver strong,” the
  agent will still feel brittle in real repository work.

Current baseline:

* strong capability metadata and projection foundation
* strong deterministic permission runtime
* layered prompt contract exists
* deferred discovery exists

Parity pressure still likely comes from:

* how well real local workflows compose tool discovery, selection, safety, and
  prompt/control-loop behavior under sustained use
* whether the runtime exposes the same practical coding affordances and
  resilience expected from a daily-driver coding agent

Primary workflows improved:

* Workflow A
* Workflow C

Priority judgment:

* highest priority

### F2: Context / Compact / Session / Memory Continuity

Primary modules:

* `compact`
* `sessions`
* `memory`
* `runtime`

Why now:

* This family is the main blocker for long-session continuity.
* Current baseline is enough to count as MVP, but not yet proven against the
  stronger Circle 1 standard.

Current baseline:

* staged pressure pipeline exists
* session resume/evidence infrastructure exists
* scoped memory exists
* compact/collapse persistence foundations exist

Parity pressure still likely comes from:

* stronger continuity under long single-day work
* better preservation of working thread across compaction/resume
* richer but still bounded context/session/memory interaction

Primary workflows improved:

* Workflow A
* Workflow B

Priority judgment:

* highest priority

### F3: Todo / Task / Plan / Verify Workflow Discipline

Primary modules:

* `todo`
* `tasks`
* `subagents` (verifier path)
* `sessions`

Why now:

* Workflow C depends on more than “tools exist”; it depends on disciplined task
  shaping and plan/verify boundaries.

Current baseline:

* TodoWrite, task graph, plan artifact, and verifier boundaries already exist
* the product already has durable workflow structure, not just prompt-based task
  talk

Parity pressure still likely comes from:

* turning these pieces into a consistent high-throughput personal workflow
* ensuring plan/task/verify is practical during real coding work rather than
  merely contract-correct

Primary workflows improved:

* Workflow A
* Workflow C

Priority judgment:

* high priority

### F4: Observability / Evidence / Recovery Visibility

Primary modules:

* `runtime`
* `sessions`
* `compact`
* `subagents`

Why now:

* Without strong visibility, Wave 1 cannot be debugged or trusted under
  long-session conditions.
* This family is supporting infrastructure for Workflows A and B rather than a
  standalone product story.

Current baseline:

* runtime event sink exists
* evidence ledger exists
* compact/pressure events exist
* prompt dump exists behind env gate

Parity pressure still likely comes from:

* making long-task failures and recoveries understandable enough for daily use
* closing the gap between “we log it” and “the agent/user can act on it”

Primary workflows improved:

* Workflow A
* Workflow B

Priority judgment:

* supporting priority; should move alongside F1/F2 rather than after them

### F5: Bounded Local Subagent / Fork Runtime

Primary modules:

* `subagents`
* `runtime`
* `tasks`
* `sessions`

Why now:

* Workflow C explicitly requires this family to be useful, not demo-shaped.
* Circle 1 does not require team-runtime parity, but it does require strong
  personal-efficiency amplification through bounded child execution.

Current baseline:

* `run_subagent`, `run_fork`, background slices, sidechain transcript, and
  resume paths already exist

Parity pressure still likely comes from:

* stronger day-to-day usability of bounded child execution
* clearer continuation, cleanup, and handoff semantics for single-developer use

Primary workflows improved:

* Workflow C

Priority judgment:

* high priority, but after F1/F2 are directionally locked

## Recommended Order

### Pass 1: F1 + F2

Why:

* these determine whether the agent can work independently for meaningful
  periods at all
* most other families depend on stable runtime/control-loop and continuity

### Pass 2: F3 + F5

Why:

* once the core is stable, workflow-discipline and bounded child execution can
  be strengthened toward genuine personal-efficiency gains

### Pass 3: F4 closeout

Why:

* observability/evidence should evolve continuously during Pass 1 and Pass 2
* but a focused closeout pass should happen after the main runtime semantics are
  clearer

## Recommended Follow-Up Task Families

These are the next planning or implementation slices to create after this note:

1. `.trellis/tasks/04-20-circle-1-wave-1-f1-tool-permission-prompt-runtime-parity/`
2. `.trellis/tasks/04-20-circle-1-wave-1-f2-context-session-memory-continuity/`
3. `.trellis/tasks/04-20-circle-1-wave-1-f3-todo-task-plan-verify-daily-driver/`
4. `.trellis/tasks/04-20-circle-1-wave-1-f5-bounded-subagent-fork-daily-driver/`
5. `.trellis/tasks/04-20-circle-1-wave-1-f4-observability-recovery-visibility/`

## Historical Inputs

Use these as baseline evidence when decomposing the follow-up tasks:

* `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
* `.trellis/project-handoff.md`
* `.trellis/tasks/archive/2026-04/04-15-stage-23-context-pressure-and-session-continuity-closeout/prd.md`
* `.trellis/tasks/archive/2026-04/04-15-stage-25-todo-task-plan-verify-closeout/prd.md`
* `.trellis/tasks/archive/2026-04/04-15-stage-26-agent-as-tool-mvp-closeout/prd.md`
* `.trellis/tasks/archive/2026-04/04-15-stage-28-observability-evidence-closeout/prd.md`

## Implementation Checkpoint

State: terminal

Verdict: APPROVE

Scope completed:

* F1 tool/permission/prompt/runtime:
  - deferred tool execution now preserves real bounded result contracts,
    including `Command(update=...)`
* F2 context/session/memory continuity:
  - collapse preserved-tail selection now avoids splitting recent
    assistant-led work units when possible
  - session-memory freshness now accounts for token/tool-call pressure where
    metrics exist
  - compact assist remains conservative for message-count-lagged artifacts
* F3 todo/task/plan/verify workflow:
  - frontend event flow now emits durable `task_snapshot` data alongside
    `todo_snapshot`
* F4 observability/recovery visibility:
  - recovery brief now includes a dedicated `Subagent activity:` section for
    recent background child-agent notifications
* F5 bounded subagent/fork runtime:
  - added deferred `subagent_list` for active/recent background run discovery

Validation:

* `pytest -q coding-deepgent/tests` -> 415 passed
* `ruff check coding-deepgent/src/coding_deepgent coding-deepgent/tests .trellis/spec .trellis/plans` -> passed
* `python3 -m mypy coding-deepgent/src/coding_deepgent` -> passed

Residual future work:

* Circle 1 Wave 2 should focus on richer runtime-exposing CLI/TUI surfaces.
* Circle 1 Wave 3 should keep local extension seams usable without expanding
  into full plugin distribution.
* Circle 2 remains the owner for mailbox/coordinator/remote/daemon parity.
