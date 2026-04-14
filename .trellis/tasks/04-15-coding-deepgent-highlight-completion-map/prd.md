# brainstorm: coding-deepgent highlight completion map

## Goal

Design a bounded completion map for `coding-deepgent` so the remaining work has a visible end. The map should cover H01-H22, state which highlights are product-essential vs deferred/optional, estimate the remaining stage groups, and prevent the roadmap from expanding indefinitely.

## What I already know

* The user wants to pause pure implementation and design the finish line because the current stage stream feels open-ended.
* The product goal is not a line-by-line cc-haha clone; it is a LangChain-native implementation of cc-haha Agent Harness essence.
* The current highlight backlog has 22 highlights: H01-H22.
* Stage 12-19 have focused mostly on context/session/compaction, durable workflow, verifier execution, verifier evidence persistence, and evidence observability.
* Latest completed stage families:
  * Stage 12: context and recovery hardening
  * Stage 13: manual compact boundary / summary artifact
  * Stage 14A: explicit generated summary CLI wiring
  * Stage 15: compact persistence semantics
  * Stage 16: virtual transcript pruning
  * Stage 17A-D: durable task / plan / verifier boundary
  * Stage 18A-B: verifier execution and evidence persistence
  * Stage 19A-B: verifier evidence provenance and lineage
* Current task list says the parent final-goal brainstorm has 4 completed children out of 19 tracked children, but that is a Trellis task count, not a highlight completion count.
* Cross-session memory is a persistent product requirement.
* The user wants future reports to include corresponding highlights, modules, tradeoffs, benefits, and complexity.
* The user has authorized multi-agent acceleration for suitable later implementation stages.

## Assumptions (temporary)

* The completion map should be a roadmap and stop rule, not a detailed implementation spec for every future function.
* The map should define an MVP finish line plus optional/deferred bands.
* The map should preserve benefit-gated complexity: no stage proceeds on “closer to cc” alone.
* The map should keep H21 bridge/remote/IDE and H22 daemon/cron out of MVP unless the user explicitly chooses a broader product target.

## Open Questions

* None for the current completion-map decision.

## Requirements (evolving)

* Produce an H01-H22 completion map.
* Use Approach A: MVP Local Agent Harness Core as the canonical finish-line scope.
* Treat `H12` and `H20` as MVP-limited highlights:
  * `H12` gets only the smallest required local subagent context snapshot/fork semantics.
  * `H20` gets only minimal local metrics/counters that directly support runtime/context decisions.
* For each highlight, record:
  * status: implemented / partial / missing / deferred / do-not-copy
  * corresponding `coding_deepgent` modules
  * MVP completion standard
  * remaining minimal stage(s), if any
  * explicit defer/do-not-copy boundary
* Group remaining work into visible milestone bands.
* Estimate total remaining stage count under Approach A.
* Mark which work directly, indirectly, or does not advance cross-session memory.
* Keep future implementation stages source-backed against cc-haha when they claim cc alignment.

## Acceptance Criteria (evolving)

* [x] The PRD contains a table for H01-H22 with status, modules, completion standard, and remaining work.
* [x] The PRD defines a recommended finish-line scope and at least two alternatives.
* [x] The PRD defines milestone groups with estimated remaining stage count.
* [x] The PRD explicitly marks deferred / out-of-MVP highlights.
* [x] The PRD includes one decision section after the user chooses scope.
* [x] The final map is clear enough to guide later `$stage-iterate lean-batch` runs without re-litigating the finish line each time.

## Definition of Done (team quality bar)

* Docs/notes updated if behavior changes.
* No product code implementation in this brainstorm task.
* Roadmap decisions are explicit and tied to H01-H22.
* Deferred scope is documented, not left ambiguous.

## Out of Scope (explicit)

* Implementing Stage 20 code.
* Full source-level design for every future stage.
* Re-reading all cc-haha source for every highlight in this brainstorm.
* Committing to UI/TUI clone, remote bridge, daemon, marketplace, or background worker parity without explicit scope approval.

## Technical Notes

* Primary roadmap: `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
* Current handoff: `.trellis/project-handoff.md`
* Recent checkpoints:
  * `.trellis/tasks/04-15-stage-18a-verifier-execution-integration/prd.md`
  * `.trellis/tasks/04-15-stage-18b-verifier-result-persistence-evidence-integration/prd.md`
  * `.trellis/tasks/04-15-stage-19-evidence-observability-agent-lifecycle-hardening/prd.md`
* Active backend contracts:
  * `.trellis/spec/backend/runtime-context-compaction-contracts.md`
  * `.trellis/spec/backend/task-workflow-contracts.md`

## Research Notes

### Constraints from our repo/project

* The project already has domain modules for tools, permissions, sessions, memory, compact, tasks, subagents, MCP/plugins, hooks, and prompting.
* The current implementation has a working session JSONL ledger, recovery brief, compact records, durable task graph, plan artifacts, verifier child-agent path, and verifier evidence metadata.
* The project deliberately uses LangChain/LangGraph primitives rather than custom query runtime cloning.
* The current fast workflow works best when stages are small, source-backed, and checkpointed.

### Feasible finish-line approaches

**Approach A: MVP Local Agent Harness Core** (Recommended)

* How it works:
  Finish a strong local coding-agent harness: tools, permission, prompt/context, session/compact/memory, todo/task/plan/verify, bounded subagents, MCP/plugin basics, hooks, and observability. Defer remote bridge, daemon/cron, marketplace/install, full coordinator/mailbox runtime, and provider-specific cache parity unless later justified.
* Pros:
  Gives a visible finish line in the shortest credible time. Matches the current product direction and avoids speculative infrastructure.
* Cons:
  Some cc-haha team/background/runtime features remain explicitly deferred.
* Rough remaining work:
  10-16 narrow stages after Stage 19, depending on how much H11/H12/H19 is deepened.

**Approach B: Full Local Core Including Agent Team Runtime**

* How it works:
  Complete Approach A, then add task-backed agent lifecycle, mailbox / SendMessage, coordinator synthesis, richer fork/cache-aware subagent execution, and deeper runtime-event evidence.
* Pros:
  Stronger H11-H14 parity and closer to cc-haha multi-agent essence.
* Cons:
  More architecture risk and more stage count; likely requires careful new contracts for agent lifecycle and message stores.
* Rough remaining work:
  18-28 narrow stages after Stage 19.

**Approach C: Broad cc-haha Product Parity Track**

* How it works:
  Include local core plus extension marketplace/install flows, bridge/IDE/remote control plane, daemon/cron/proactive automation, and richer provider-specific cost/cache instrumentation.
* Pros:
  Broadest parity story.
* Cons:
  Highest risk of losing product focus; includes several capabilities that the current roadmap says should not be prioritized without explicit product goals.
* Rough remaining work:
  30+ stages and likely multiple roadmap cycles.

## Draft Completion Map

Status vocabulary:

* `implemented`: enough for MVP unless a later audit finds a defect.
* `partial`: useful implementation exists, but known MVP completion work remains.
* `missing`: planned for MVP but not implemented enough.
* `deferred`: valid cc-haha behavior, outside the recommended MVP.
* `do-not-copy`: not a local product goal or wrong abstraction.

| ID | Highlight | Current status | MVP target | Modules | Remaining MVP work |
|---|---|---|---|---|---|
| H01 | Tool-first capability runtime | partial | strict tool schemas + capability metadata + guarded execution for all model-facing capabilities | `tool_system`, domain `tools.py` | audit all current tools; close schema/metadata gaps |
| H02 | Permission runtime and hard safety | partial | deterministic local policy with safe defaults, trusted dirs, hook integration, and explicit denied/ask behavior | `permissions`, `tool_system`, `filesystem`, `hooks` | permission mode/rule audit; hard safety tests |
| H03 | Layered prompt contract | partial | stable base prompt + structured dynamic context surfaces, no giant tool manual | `prompting`, `runtime`, `memory`, `compact` | prompt/context audit and cache-aware stable/dynamic split |
| H04 | Dynamic context protocol | partial | typed/bounded context payload assembly for memory, recovery, compaction, skills/resources | `runtime`, `sessions`, `memory`, `compact`, `skills`, `mcp` | consolidate context assembly contracts |
| H05 | Progressive context pressure management | partial | deterministic projection, compact records, latest valid compact selection, tool-result invariants | `compact`, `sessions`, `runtime` | audit current Stage 12-16 gaps; maybe one hardening stage |
| H06 | Session transcript, evidence, and resume | partial-strong | session JSONL, evidence, compacts, recovery brief, compacted resume continuity | `sessions`, `runtime`, `cli_service` | likely one audit/CLI evidence inspection stage |
| H07 | Scoped cross-session memory | partial | controlled `save_memory`, quality policy, scoped recall, no knowledge dumping | `memory`, `runtime`, `sessions` | deepen recall/write contracts; optional auto extraction deferred |
| H08 | TodoWrite short-term planning | implemented/partial | strict TodoWrite contract with state updates and prompt guidance, separate from durable Task | `todo`, `runtime`, `prompting` | final contract audit only |
| H09 | Durable Task graph | partial-strong | validated graph, readiness, plan artifacts, verification nudge, no todo conflation | `tasks`, `tool_system` | persistence/checkpointer integration decision; maybe audit |
| H10 | Plan / Execute / Verify discipline | partial-strong | explicit plan artifact, verifier child execution, persisted verifier evidence | `tasks`, `subagents`, `sessions` | optional runtime-event evidence; no coordinator by default |
| H11 | Agent as tool/runtime object | partial | all subagents enter as tools, verifier has bounded child runtime and evidence lineage | `subagents`, `runtime`, `tasks`, `sessions` | decide whether MVP needs general subagent lifecycle beyond verifier |
| H12 | Fork/cache-aware subagent execution | deferred/partial | minimal context snapshot/fork semantics only if H11 lifecycle needs it | `subagents`, `runtime`, `compact` | likely defer provider-specific cache parity |
| H13 | Mailbox / SendMessage | deferred | out of MVP unless full agent-team scope chosen | `tasks`, `subagents` | no MVP work under Approach A |
| H14 | Coordinator keeps synthesis | deferred | principle documented; implementation out of MVP unless full agent-team scope chosen | `tasks`, `subagents`, `prompting` | no MVP work under Approach A |
| H15 | Skill system packaging | partial | local skill loader/tool, bounded context injection, no marketplace | `skills`, `tool_system`, `prompting` | source-backed skill audit; maybe one hardening stage |
| H16 | MCP external capability protocol | partial-strong | local MCP config/loading seam, tool/resource separation, capability policy | `mcp`, `plugins`, `tool_system` | Stage 11 audit; avoid broad installer |
| H17 | Plugin states | partial/deferred | local manifest validation and enable/source state only | `plugins`, `skills`, `mcp` | clarify MVP manifest state; marketplace deferred |
| H18 | Hooks as middleware | partial | lifecycle hooks through safe middleware boundaries, not backdoors | `hooks`, `tool_system`, `runtime` | hook event/evidence audit; no remote hook platform |
| H19 | Observability/evidence ledger | partial-strong | structured local events + session evidence + recovery visibility | `runtime`, `sessions`, `tool_system`, `subagents` | runtime-event evidence gate, evidence CLI inspection optional |
| H20 | Cost/cache instrumentation | deferred/partial | local metrics only, no provider-specific cache parity in MVP | `compact`, `runtime`, `sessions` | maybe minimal counters; rich cache deferred |
| H21 | Bridge / remote / IDE | deferred | out of MVP | future integration boundary | no MVP work |
| H22 | Daemon / cron / proactive automation | deferred | out of MVP | future scheduling boundary | no MVP work |

## Draft Milestone Groups

### M1: Core Audit And Closeout

Goal: mark H01-H10 as implemented / partial / deferred with no hidden gaps.

Likely stages:

* Tool/permission surface audit: H01/H02
* Prompt/context closeout: H03/H04
* Context pressure closeout: H05/H06
* Memory quality and recall closeout: H07
* Todo/task/plan final audit: H08/H09/H10

Estimate: 5-7 narrow stages.

### M2: Agent / Evidence Minimal Runtime

Goal: finish the recommended MVP version of H11/H19 without coordinator/mailbox/background runtime.

Likely stages:

* Runtime-event evidence gate: H19
* Decide general subagent lifecycle MVP boundary: H11
* Optional evidence CLI inspection: H06/H19

Estimate: 2-4 narrow stages.

### M3: Extension Platform Closeout

Goal: ensure skills, MCP, plugins, hooks are safe local extension surfaces.

Likely stages:

* Skill packaging audit/hardening: H15
* MCP/plugin loading audit/hardening: H16/H17
* Hook middleware lifecycle audit/hardening: H18

Estimate: 3-5 narrow stages.

### M4: Explicit Deferral / Product Boundary

Goal: document what is intentionally outside MVP so the project ends cleanly.

Likely stages:

* H12/H13/H14 full agent-team deferral or next-cycle spec
* H20 local metrics decision
* H21/H22 do-not-prioritize boundary

Estimate: 1-3 documentation/spec stages.

## Draft Remaining Stage Estimate

Recommended Approach A:

* Remaining implementation/audit stages after Stage 19: 10-16
* Expected final stage number: roughly Stage 30-36
* Finish means H01-H22 all have explicit statuses and MVP-relevant highlights are implemented or intentionally scoped down.

Approach B:

* Remaining stages after Stage 19: 18-28
* Expected final stage number: roughly Stage 38-48
* Finish means full local agent-team runtime is included.

Approach C:

* Remaining stages after Stage 19: 30+
* Expected final stage number: Stage 50+
* Finish means broad parity track, not recommended for the current product goal.

## Decision (ADR-lite)

**Context**: The existing stage stream was making progress, but the finish line was not visible. The user wants a concrete completion target before continuing implementation.

**Decision**: Use **Approach A: MVP Local Agent Harness Core** as the canonical completion scope for the next phase.

**Consequences**:

* The MVP finish line is a complete local LangChain-native Agent Harness, not full cc-haha product parity.
* Remaining work is estimated at **10-16 narrow stages after Stage 19**, with a rough final range of **Stage 30-36**.
* H13 mailbox, H14 coordinator runtime, H21 bridge/remote/IDE, and H22 daemon/cron are not part of MVP.
* H12 fork/cache-aware subagent behavior and H20 cost/cache instrumentation are part of MVP only in minimal local forms:
  * H12: bounded subagent context snapshot/fork semantics only when needed by the local runtime
  * H20: local counters/metrics only when they directly help context/runtime decisions
* Future `$stage-iterate` work should choose stages from the milestone groups below and update this completion map when a highlight status changes.

## Approach A MVP Completion Plan

### MVP Must Finish

These highlights must be implemented or closed out with tests/contracts:

* H01 Tool-first capability runtime
* H02 Permission runtime and hard safety
* H03 Layered prompt contract
* H04 Dynamic context protocol
* H05 Progressive context pressure management
* H06 Session transcript, evidence, and resume
* H07 Scoped cross-session memory
* H08 TodoWrite short-term planning
* H09 Durable Task graph
* H10 Plan / Execute / Verify workflow discipline
* H11 Agent as tool/runtime object, MVP-bounded
* H15 Skill system packaging, local-only
* H16 MCP external capability protocol, local-only
* H17 Plugin states, local manifest only
* H18 Hooks as middleware
* H19 Observability/evidence ledger

### MVP Limited / Minimal

These get only the smallest local slice needed by the MVP:

* H12 Fork/cache-aware subagent execution: minimal context snapshot semantics only if required by H11.
* H20 Cost/cache instrumentation: local counters/metrics only if they support context/compact decisions.

### Out Of MVP / Deferred

These are valid future roadmap items, but not part of the current finish line:

* H13 Mailbox / SendMessage multi-agent communication
* H14 Coordinator keeps synthesis
* H21 Bridge / remote / IDE control plane
* H22 Daemon / cron / proactive automation

## Final MVP Boundary

### Included In MVP

* H01-H11
* H15-H19
* H12 minimal local slice
* H20 minimal local slice

### Explicitly Not In MVP

* H13 full mailbox / SendMessage runtime
* H14 coordinator synthesis runtime
* H21 bridge / remote / IDE control plane
* H22 daemon / cron / proactive automation

### Stop Rule

The MVP is complete when:

* Every H01-H22 row has an explicit status.
* Every MVP-included row is either:
  * `implemented`, or
  * `partial` with an explicit, accepted minimal boundary that is already covered by tests/contracts.
* Every non-MVP row is explicitly `deferred` or `do-not-copy`.
* No remaining open stage exists unless it maps to an MVP-included row and has a concrete benefit statement.

## Recommended Next Stage Sequence

1. Stage 20: Highlight status audit and closeout table hardening
   * Goal: turn this draft map into the canonical progress dashboard.
   * Highlights: H01-H22 all.
   * Output: final status table with `implemented / partial / missing / deferred / do-not-copy`.

2. Stage 21: Tool and permission closeout
   * Highlights: H01/H02.
   * Modules: `tool_system`, `permissions`, `filesystem`, domain tools.

3. Stage 22: Prompt and dynamic context closeout
   * Highlights: H03/H04.
   * Modules: `prompting`, `runtime`, `memory`, `sessions`.

4. Stage 23: Context pressure and session continuity closeout
   * Highlights: H05/H06.
   * Modules: `compact`, `sessions`, `runtime`.

5. Stage 24: Scoped memory closeout
   * Highlights: H07.
   * Modules: `memory`, `runtime`, `sessions`.

6. Stage 25: Todo/task/plan/verify closeout
   * Highlights: H08/H09/H10.
   * Modules: `todo`, `tasks`, `subagents`, `sessions`.

7. Stage 26: MVP-bounded agent-as-tool closeout
   * Highlights: H11 with limited H12.
   * Modules: `subagents`, `runtime`, `tasks`, `sessions`.

8. Stage 27: Local extension platform closeout
   * Highlights: H15/H16/H17/H18.
   * Modules: `skills`, `mcp`, `plugins`, `hooks`, `tool_system`.

9. Stage 28: Observability and evidence closeout
   * Highlights: H19 with minimal H20 decision.
   * Modules: `runtime`, `sessions`, `tool_system`.

10. Stage 29: Deferred-boundary ADR and MVP release checklist
    * Highlights: H12/H13/H14/H20/H21/H22.
    * Output: explicit MVP/non-MVP boundary.

11. Stage 30-36 reserve
    * Buffer for gaps found during closeout audits.
    * Rule: every reserve stage must map to an existing H row and have a concrete benefit gate.

## Expansion Sweep

### Future evolution

* The map can become the canonical progress dashboard for H01-H22.
* Deferred agent-team, remote, and daemon capabilities can become a second roadmap instead of leaking into MVP.

### Related scenarios

* Every later `$stage-iterate` report should name the highlight row it advances.
* Checkpoints should update this map when a highlight status changes.

### Failure / edge cases

* Risk: over-classifying partial highlights as done. Mitigation: every implemented status needs tests/contracts or a source-backed audit note.
* Risk: roadmap grows as more cc-haha details are discovered. Mitigation: newly discovered behavior must map to an existing H row or become explicit next-cycle/deferred scope.

## Checkpoint: Stage 20

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Promoted `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md` from a planning backlog into the canonical MVP dashboard.
- Fixed the MVP boundary for Approach A:
  - include H01-H11, H15-H19
  - include minimal H12/H20
  - defer H13/H14/H21/H22
- Added the canonical H01-H22 status table with:
  - current status
  - MVP boundary
  - main modules
  - next / remaining stage
- Added milestone groups M1-M4 and explicit Stage 21-29 sequencing plus Stage 30-36 reserve.
- Added a stop rule so no future stage is valid unless it maps to an existing H row and has a concrete benefit statement.

Corresponding highlights:
- All H01-H22 as a planning/control surface.
- This stage does not implement product runtime behavior directly; it defines the bounded finish line for all remaining runtime work.

Corresponding modules:
- `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
- `.trellis/tasks/04-15-coding-deepgent-highlight-completion-map/prd.md`
- `.trellis/project-handoff.md`

Tradeoff / complexity:
- Chosen: a bounded completion map instead of a full low-level design for every future feature.
- Deferred: detailed function-by-function designs for later stages until they become active.
- Why this complexity is worth it now: the user needs a visible finish line, and later stage work must stop expanding arbitrarily.

Verification:
- Acceptance criteria in this PRD are now satisfied.
- Trellis task context for this task is initialized and validated as the current stage ledger.

Boundary findings:
- “Task count” and “highlight completion” are different dimensions; the canonical dashboard resolves that ambiguity.
- H12 and H20 need explicit minimal-MVP handling, otherwise they keep re-opening scope discussions.

Decision:
- continue

Reason:
- Stage 20 is complete and Stage 21 is now well-scoped: H01/H02 tool + permission closeout is the next direct milestone from the canonical dashboard.
