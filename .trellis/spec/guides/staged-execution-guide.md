# Staged Execution Guide

> **Purpose**: Run multi-stage `coding-deepgent` work with explicit checkpoints, bounded validation, and safe auto-progression.

---

## When To Use

Use this guide when a task family spans multiple sub-stages and should continue
only after each stage is explicitly reviewed.

Typical use cases:

- staged feature families
- roadmap closeout slices
- checkpointed infrastructure upgrades
- long-running implementation that should not drift

---

## Modes

Two execution modes are supported:

- `lean` (default)
- `deep`

### `lean`

- work one sub-stage at a time
- prefer focused tests
- avoid broad re-reading of settled source/doc context
- avoid full-suite validation unless clearly required
- if checkpoint result is `continue`, immediately start the next sub-stage

### `deep`

- broader re-orientation is allowed
- broader validation is allowed
- can fold larger docs/git/PR work into the same run when explicitly justified

If the user did not explicitly opt into a long-running all-in-one pass, default
to `lean`.

---

## Sub-Stage State Machine

Every staged run should use one explicit sub-stage state:

- `planning`
- `implementing`
- `verifying`
- `checkpoint`
- `terminal`

If resuming an existing stage family, resume from the current active state
instead of replaying orientation from zero.

---

## Before Implementation

- A Trellis task exists.
- A PRD exists.
- Expected benefit is concrete.
- Relevant source mapping is recorded when alignment matters.
- LangChain-native boundary is chosen when applicable.
- Out-of-scope items are explicit.
- Focused tests are named.

If the task introduces a genuinely new feature band, expand research. Otherwise,
reuse recent verified PRD/checkpoint context when safe.

---

## Validation Budget

Default validation rules:

- `lean`
  - focused tests only
  - targeted lint/typecheck on changed files
  - run broader validation only when:
    - the user asks
    - the change touches cross-cutting contracts
    - focused validation exposes ambiguity
- `deep`
  - focused plus broader regression as appropriate

Do not treat "more validation" as automatically better. Match validation cost to
change risk.

Current default for `coding-deepgent`:

- focused validation first
- broader validation only on cross-layer/contract/runtime risk, ambiguous focused failures, or explicit user request

---

## Checkpoint Gate

At the end of each sub-stage, record:

- implemented behavior
- tests run and result
- files changed
- alignment evidence when relevant
- architecture evidence when relevant
- boundary issues discovered
- whether the next sub-stage still holds

Use internal verdict vocabulary:

- `APPROVE`
- `ITERATE`
- `REJECT`

Map to execution decisions:

- `APPROVE` -> `continue`
- `ITERATE` -> `adjust` or `split`
- `REJECT` -> `stop`

Execution rule:

- `continue` -> start the next sub-stage immediately
- `adjust` -> rewrite the next sub-stage plan first
- `split` -> create a prerequisite task and stop the main run
- `stop` -> stop and ask the user

Do not stop only to summarize progress if the decision is `continue`.

---

## Checkpoint Template

```md
## Checkpoint: <sub-stage>

State:
- planning | implementing | verifying | checkpoint | terminal

Verdict:
- APPROVE | ITERATE | REJECT

Implemented:
- ...

Verification:
- ...

Alignment:
- source files inspected:
- aligned:
- deferred:
- do-not-copy:

Architecture:
- primitive used:
- why no heavier abstraction:

Boundary findings:
- ...

Decision:
- continue | adjust | split | stop

Reason:
- ...
```

---

## Stop Conditions

Stop and ask the user when:

- the next sub-stage scope is no longer valid
- tests fail and the fix is not local to the current sub-stage
- required source mapping is missing for an alignment-critical change
- the implementation would replace LangChain/LangGraph runtime seams
- the worktree contains conflicting user changes
- the next step requires a new product decision

---

## Subagent Rule

If subagents are explicitly authorized:

- give each one a bounded, non-overlapping task
- keep them off the critical path unless the main agent is blocked
- final synthesis remains with the main agent

---

## Current Repo Default

For the current `coding-deepgent` mainline:

- use Trellis tasks + PRDs as the stage ledger
- use this guide instead of the removed `stage-iterate` skill
- keep checkpoint logic in Trellis docs, not in external skill wrappers
