# coding-deepgent Full CC Parity Roadmap

Status: active canonical roadmap
Updated: 2026-04-20
Scope: `coding-deepgent/` product track only
Supersedes as default planning target:

* `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
* `.trellis/plans/coding-deepgent-deferred-boundary-refresh-adr.md`
* MVP-only closeout guidance in `.trellis/project-handoff.md`

## Purpose

This roadmap replaces the old "stop at Approach A MVP" default with a new
default direction:

* pursue full Claude Code parity over time
* keep implementation professional-grade and maintainable
* keep LangChain/LangGraph-native boundaries where they do not block important
  local product behavior
* use a documented evidence ladder when source coverage is incomplete

This is a roadmap and planning contract, not an implementation checklist.

## Top-Level Target

`coding-deepgent` should become a professional local coding agent whose:

* model-visible behavior
* runtime semantics
* CLI/TUI interaction

progressively approach real Claude Code public behavior, while:

* using `cc-haha` as the primary open-source implementation reference
* using high-quality analogous OSS systems when Claude Code behavior and
  `cc-haha` source are insufficient
* avoiding unnecessary provider-specific or closed-source cloning where it does
  not create concrete local product value

## Evidence Order

Use this evidence order for all future parity work:

1. **Real Claude Code public behavior**
   - official docs
   - public product surfaces
   - reproducible visible behavior
   - public runtime artifacts
2. **`cc-haha` source-backed implementation reference**
   - exact files, symbols, docs, comments, and observable behavior
3. **High-quality analogous OSS**
   - open-source systems implementing a similar capability family
4. **Secondary analysis**
   - books, blogs, or third-party interpretations

Rules:

* real Claude Code public behavior is the top-level parity target
* `cc-haha` is the default implementation reference when it explains or matches
  the target behavior
* use analogous OSS only after documenting why levels 1 and 2 are insufficient
* do not treat secondary analysis as stronger than available source or product
  evidence

## Missing-Source Fallback Rule

When the target capability does not have enough accessible Claude Code or
`cc-haha` source:

1. state the exact missing behavior or source gap
2. identify 2-4 high-quality OSS systems in the same capability family
3. summarize how those systems solve the problem
4. document the reusable essence vs project-specific detail
5. choose the local design explicitly in the task PRD before implementation

Required PRD note shape:

```md
## Source Gap

- what behavior is targeted
- what Claude Code evidence exists
- what `cc-haha` evidence exists
- why those are insufficient

## Analogous OSS Review

- project A: relevant implementation shape
- project B: relevant implementation shape

## Local Decision

- chosen design
- why it fits local product needs
- what remains inferred rather than source-proven
```

## Candidate OSS Pool

These are candidate fallback sources, not automatic parity targets:

* `sst/opencode`
  - terminal coding-agent runtime
  - CLI/TUI interaction
  - provider-agnostic architecture
* `Aider-AI/aider`
  - repository coding loop
  - pragmatic edit/test/commit workflow
  - codebase-map ergonomics
* `OpenHands/OpenHands`
  - agent SDK/runtime layering
  - CLI/SDK split
  - permissions and agent orchestration patterns
* `google-gemini/gemini-cli`
  - CLI agent behavior
  - checkpoint/resume/context-file conventions
  - MCP/tooling ergonomics
* `block/goose`
  - local agent architecture
  - extension seams
  - desktop/CLI/API multi-surface packaging

## Circle 1: Local Daily-Driver Parity

Circle 1 is the new default implementation target.

### Included

* single-agent local coding loop
* runtime/tool/prompt/context/session/memory/task surfaces
* local subagent and fork workflow
* local CLI/TUI interaction required to expose these capabilities
* local extension seams at "usable" depth only

### Not Included In Circle 1

* mailbox / `SendMessage`
* coordinator / team-runtime synthesis
* remote / IDE control plane
* daemon / cron / proactive automation
* full marketplace/install/enable/distribution experience for plugins

### Circle 1 Acceptance Workflows

Circle 1 is accepted primarily by workflow quality, not only by feature-band
checklists.

#### Workflow A: Repository Takeover And Sustained Coding

Success standard: **PR-level independent completion**

The agent should be able to:

* inspect a medium-to-large codebase
* form a short executable plan
* edit code
* run validation
* handle normal interruptions and continue

without requiring the user to micromanage every step.

#### Workflow B: Long Session Continuity

Success standard: **single-day long-task continuity**

The agent should be able to:

* survive multiple rounds of context pressure
* compact/collapse/resume without losing the main thread
* continue meaningful work after long local development sessions

without requiring cross-day parity in Circle 1.

#### Workflow C: Complex Task Decomposition

Success standard: **personal-efficiency amplification**

The agent should be able to use:

* todo/task/plan discipline
* bounded subagent/fork assistance

to materially improve a single developer's throughput on complex tasks, without
requiring full mailbox/coordinator/team-runtime parity.

### Circle 1 Feature-Band Priorities

#### Wave 1: Runtime-Core Parity

Priority modules/bands:

* `tool_system`
* `permissions`
* `prompting`
* `runtime`
* `compact`
* `sessions`
* `memory`
* `todo`
* `tasks`
* `subagents`
* `observability/evidence`

Why first:

* these determine whether the three acceptance workflows are stable
* broad CLI/TUI polish will drift if these are still semantically weak

#### Wave 2: Runtime-Exposing CLI/TUI Surfaces

Priority surfaces:

* resume/history/inspect/projection visibility
* compact/collapse continuity UX
* task/plan/subagent/fork interaction surfaces
* permission and recovery interaction surfaces

Why second:

* Circle 1 still includes CLI/TUI parity
* but the first CLI/TUI focus is on high-value runtime-exposing surfaces, not
  broad aesthetic cloning

Implemented checkpoint:

* `2026-04-20`: first runtime-exposing surfaces pack
  * `sessions inspect` exposes loaded-session recovery/projection/timeline/raw
    visibility/session-memory state
  * frontend protocol exposes `context_snapshot` and `subagent_snapshot`
  * React/Ink CLI renders context, task, and subagent panels from typed reducer
    state
* `2026-04-20`: control surfaces pack
  * local runtime store now has a `file` backend for process-surviving task/plan/background-run state in one workspace
  * CLI now exposes durable `tasks/*` and `plans/*` control surfaces
  * TUI bridge now exposes live background-subagent control for the active
    frontend process
* `2026-04-20`: final Wave 2/Circle 1 UX pack
  * CLI exposes session history/projection/timeline/evidence/events/permissions
    views
  * CLI exposes local skills/MCP/hooks/plugins list/inspect/validate/debug
    surfaces
  * deterministic `acceptance circle1` harness records the Circle 1 workflow
    boundary

#### Wave 3: Usable Local Extension Seams

Priority modules:

* `skills`
* `mcp`
* `hooks`
* `plugins`

Circle 1 boundary:

* local loading
* local invocation
* local debugging
* source/trust/validation clarity

Not required in Circle 1:

* full install/enable lifecycle parity
* distribution/marketplace experience

Implemented checkpoint:

* `2026-04-20`: usable local extension inspect/debug seams
  * `skills`, `mcp`, `hooks`, and `plugins` have local CLI inspect/validate/debug
    surfaces
  * no marketplace, install/enable lifecycle, daemon, or remote extension
    control was added

## Circle 2: Expanded Product Parity

Circle 2 begins only after Circle 1 is coherent enough to act as a daily-driver
local coding agent.

Canonical Circle 2 plan:

* `.trellis/plans/coding-deepgent-circle-2-expanded-parity-plan.md`

Likely Circle 2 bands:

* mailbox / `SendMessage`
* coordinator synthesis
* richer background team-runtime
* remote / IDE control plane
* daemon / cron / proactive automation
* broader extension ecosystem lifecycle
* stronger cross-day continuity and richer session-memory extraction

## Historical References

These remain useful, but they are no longer the default planning destination:

* `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
* `.trellis/plans/coding-deepgent-deferred-boundary-refresh-adr.md`
* `.trellis/tasks/archive/2026-04/04-15-stage-29-deferred-boundary-adr-mvp-release-checklist/prd.md`
* `.trellis/tasks/archive/2026-04/04-19-backend-next-step-roadmap/prd.md`

## Planning Gate

Before any new parity implementation starts, the proposal must state:

1. which Circle it belongs to
2. which acceptance workflow(s) it improves
3. the target Claude Code behavior
4. the `cc-haha` source evidence, if available
5. whether OSS fallback research was needed
6. which layers must match behavior:
   - model-visible behavior
   - runtime semantics
   - CLI/TUI interaction
7. which layers may remain LangChain-native:
   - hidden implementation
   - provider-specific plumbing
   - non-essential product detail

Do not propose work using only the phrase "closer to cc".

## Current Next Step

The next planning step after this roadmap is:

* start Circle 1 / Wave 2 runtime-exposing CLI/TUI surfaces
* keep `.trellis/plans/coding-deepgent-circle-1-wave-1-runtime-core-plan.md`
  as the completed Wave 1 runtime-core checkpoint
* do not reopen Wave 1 unless a concrete regression or daily-driver blocker
  appears
