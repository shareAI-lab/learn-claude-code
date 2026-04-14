# Stage 29: Deferred Boundary ADR And MVP Release Checklist

## Goal

Close the Approach A MVP by documenting the deferred boundary for H13/H14/H21/H22, confirming H01-H22 have explicit statuses, and producing a release checklist for the MVP Local Agent Harness Core.

## Function Summary

This stage does not add product runtime behavior. It validates the canonical dashboard, records deferred/out-of-MVP decisions, and states whether any Stage 30-36 reserve work is still required.

## Expected Benefit

* Clarity: the MVP has a visible finish line and explicit non-goals.
* Maintainability: future requests cannot silently pull deferred cc-haha systems into the MVP.
* Planning: Stage 30-36 reserve can be used only if a concrete dashboard gap remains.

## Corresponding Highlights

* `H13 Mailbox / SendMessage`
* `H14 Coordinator keeps synthesis`
* `H21 Bridge / remote / IDE control plane`
* `H22 Daemon / cron / proactive automation`
* final status check for H01-H22

## Corresponding Modules

* `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
* `.trellis/project-handoff.md`
* final-goal PRD/task metadata

## Out Of Scope

* implementing mailbox
* implementing coordinator
* implementing bridge / IDE / remote control plane
* implementing daemon / cron / proactive automation
* full pytest unless release checklist finds a concrete cross-layer risk

## Acceptance Criteria

* [x] H13/H14/H21/H22 are explicitly deferred or do-not-copy in the canonical dashboard.
* [x] H01-H22 all have explicit statuses with no `missing` rows.
* [x] MVP release checklist exists and names residual risks.
* [x] checkpoint decides whether Stage 30-36 reserve work is needed.

## Deferred Boundary ADR

**Context**: Approach A defines the MVP as a local LangChain-native Agent Harness Core, not broad cc-haha product parity.

**Decision**: Keep these rows explicitly out of MVP:

* `H13 Mailbox / SendMessage`: deferred to a future agent-team roadmap.
* `H14 Coordinator keeps synthesis`: deferred to a future coordinator roadmap.
* `H21 Bridge / remote / IDE control plane`: deferred until there is an explicit remote/IDE product goal.
* `H22 Daemon / cron / proactive automation`: deferred until proactive automation is explicitly requested.

**Consequences**:

* The MVP can close without mailbox, coordinator, bridge, IDE, daemon, or cron runtime.
* H12 and H20 remain implemented only in minimal local form.
* Future work can revive H13/H14/H21/H22 only through a new source-backed PRD with concrete benefit and complexity judgment.

## MVP Release Checklist

### Dashboard Status

* [x] H01 Tool-first capability runtime: implemented
* [x] H02 Permission runtime and hard safety: implemented
* [x] H03 Layered prompt contract: implemented
* [x] H04 Dynamic context protocol: implemented
* [x] H05 Progressive context pressure management: implemented
* [x] H06 Session transcript, evidence, and resume: implemented
* [x] H07 Scoped cross-session memory: implemented
* [x] H08 TodoWrite short-term planning contract: implemented
* [x] H09 Durable Task graph: implemented
* [x] H10 Plan / Execute / Verify workflow discipline: implemented
* [x] H11 Agent as tool and runtime object: implemented
* [x] H12 Fork/cache-aware subagent execution: implemented-minimal
* [x] H13 Mailbox / SendMessage: deferred
* [x] H14 Coordinator keeps synthesis: deferred
* [x] H15 Skill system packaging: implemented
* [x] H16 MCP external capability protocol: implemented
* [x] H17 Plugin states: implemented-minimal
* [x] H18 Hooks as middleware: implemented
* [x] H19 Observability/evidence ledger: implemented
* [x] H20 Cost/cache instrumentation: implemented-minimal
* [x] H21 Bridge / remote / IDE control plane: deferred
* [x] H22 Daemon / cron / proactive automation: deferred

### Known Residual Risks

* No full-suite validation has been run in this deep run; validation stayed focused/targeted per stage.
* Current worktree includes many uncommitted stage changes and pre-existing Trellis planning changes.
* H12 is minimal only; rich provider-specific fork/cache behavior is not in MVP.
* H17 is local manifest/source validation only; install/enable lifecycle is not in MVP.
* H20 is local budget/projection/compact counters only; provider-specific cost/cache instrumentation is not in MVP.
* Evidence CLI inspection remains optional; recovery brief already exposes relevant session evidence.

### Next-cycle Backlog

* H13 mailbox / SendMessage multi-agent communication.
* H14 coordinator synthesis runtime.
* Full H12 provider/cache-aware fork parity if a concrete runtime benefit appears.
* Full H17 plugin install/enable/update lifecycle.
* H20 provider-specific cost/cache instrumentation or reporting.
* H21 bridge / IDE / remote control plane.
* H22 daemon / cron / proactive automation.

## Checkpoint: Stage 29

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Recorded the deferred-boundary ADR for H13/H14/H21/H22.
- Confirmed H01-H22 all have explicit statuses in the canonical dashboard.
- Produced the MVP release checklist and next-cycle backlog.
- Confirmed Stage 30-36 reserve is not currently required by the dashboard; it remains available only if later validation finds a concrete MVP gap.

Corresponding highlights:
- `H13`, `H14`, `H21`, `H22` as deferred rows.
- H01-H22 as final dashboard validation.

Corresponding modules:
- `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
- `.trellis/project-handoff.md`
- `.trellis/tasks/04-15-stage-29-deferred-boundary-adr-mvp-release-checklist/prd.md`

Tradeoff / complexity:
- Chosen: close Approach A MVP now with explicit next-cycle deferrals.
- Deferred: full agent-team runtime, remote control plane, daemon/proactive automation, marketplace/install lifecycle.
- Why this complexity is worth it now: the user needed a visible finish line; the dashboard now establishes one and prevents hidden scope expansion.

Verification:
- Canonical dashboard reviewed: no `missing` rows remain.
- Trellis context validation run for Stage 29.

Decision:
- terminal

Reason:
- Approach A MVP completion-map work has reached the defined Stage 29 closeout. Stage 30-36 reserve is not needed unless a later broader validation run discovers a concrete MVP gap.
