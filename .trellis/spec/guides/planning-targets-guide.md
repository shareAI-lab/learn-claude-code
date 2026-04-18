# Planning Targets Guide

> **Purpose**: Force feature-family plans to become concrete before implementation starts, so work can proceed in one integrated pass instead of drifting through repeated vague replanning.

---

## When To Use

Use this guide when:

- a task is bigger than a trivial fix
- a feature family spans multiple related behaviors
- the user wants one integrated implementation pass
- planning has started to drift into abstract discussion

This guide is for:

- planning
- brainstorming
- roadmap slicing
- implementation gating

---

## Core Rule

Before implementation begins for a non-trivial feature family, the plan must
explicitly contain three buckets:

1. `Acceptance Targets`
2. `Planned Features`
3. `Planned Extensions`

If any of these are missing, do not treat the feature family as ready for
implementation.

---

## Why This Exists

Without these three buckets, planning usually fails in one of three ways:

1. **Vague completion**
   - people say "memory is better" or "context handling improved"
   - nobody can tell what counts as done

2. **Scope contamination**
   - future ideas leak into the current implementation
   - current work grows until it becomes unsafe

3. **Repeated replanning churn**
   - each turn redefines the target
   - the code never gets one coherent integrated pass

This guide exists to stop those failure modes.

---

## The Three Buckets

### 1. Acceptance Targets

These define what must be true for the task to count as complete.

Write them as user-visible or system-visible outcomes, not as implementation
fragments.

Good examples:

- users can see long-term memory and current-session memory separately in recovery
- feedback rules can block commit-like actions before they run
- the system can list and delete saved memory entries

Bad examples:

- added a new model
- refactored module layout
- introduced helper functions

Question to ask:

> If this task ends, what concrete behavior should now exist that did not exist before?

### 2. Planned Features

These define what the task will implement now.

This bucket should be concrete and scoped.

Good examples:

- add one project-level rules file entrypoint
- add long-term memory listing and deletion tools
- show long-term memory and current-session memory in recovery brief

Bad examples:

- improve memory architecture
- move toward parity
- prepare for future work

Question to ask:

> Which concrete capabilities are we actually building in this task?

### 3. Planned Extensions

These define what is intentionally not implemented now, but is already known as
future work.

This bucket prevents future ideas from contaminating the current implementation
while still preserving continuity.

Good examples:

- durable memory persistence across restart
- auto-suggested memory extraction
- path-scoped rules
- agent-private memory

Bad examples:

- nothing else
- TBD
- maybe future improvements

Question to ask:

> What future capabilities are real, but intentionally deferred from this pass?

---

## Required Planning Shape

Every non-trivial feature-family PRD or planning note should include:

```md
## Acceptance Targets

- ...
- ...

## Planned Features

- ...
- ...

## Planned Extensions

- ...
- ...
```

Optional but recommended:

```md
## Why Now

- ...

## Out of Scope

- ...
```

---

## Execution Rule

Once the three buckets are explicit and approved:

- prefer one integrated implementation pass for the feature family
- do not keep reopening the same planning question every turn
- only split the work when a real blocker, dependency, or validation failure appears

This rule exists to support high-value, strongly coupled feature families that
should be completed coherently.

---

## Relationship To Staged Execution

This guide decides **what the task is**.

[Staged Execution Guide](./staged-execution-guide.md) decides **how the task
progresses once the target is already clear**.

Use both when:

- the feature family is non-trivial, and
- implementation should proceed through checkpoints after planning is locked

---

## Review Gate

Before implementation starts, reviewers or future agents should be able to
answer all three:

- What must be true when this task is done?
- What exactly is being built now?
- What is deliberately deferred?

If not, the task is not ready.

---

## Example

```md
## Acceptance Targets

- recovery shows long-term memory separately from current-session memory
- users can inspect and delete saved long-term memory
- feedback memories can block selected high-value actions

## Planned Features

- add `list_memory`
- add `delete_memory`
- add long-term memory snapshot to recovery brief

## Planned Extensions

- durable memory persistence across restart
- auto-extracted memory suggestions
- child-agent private memory
```

This is good enough to implement.
