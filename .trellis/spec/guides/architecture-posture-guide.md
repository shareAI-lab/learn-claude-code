# Architecture Posture Guide

> Project-wide decision rule for architecture, refactors, and sequencing.

---

## Purpose

Use this guide when a task involves architecture choices, refactors, runtime
foundations, contract changes, state schema changes, or any situation where a
"smallest patch" option competes with a cleaner long-term structure.

This is a **must-adhere** project rule, not an optional style preference.

---

## Core Rules

### 1. Prioritize highest-value architecture, not smallest diff

When choosing between approaches, prioritize the option with the largest
long-term product and architecture benefit, not the one with the fewest changed
lines.

Default bias:

* clearer boundaries
* stronger future extensibility
* fewer hidden coupling points
* less rework in later stages

### 2. Prefer long-term clean boundaries over transitional compatibility

If a new structure is clearly more coherent, prefer it even when it replaces a
local abstraction that already exists.

Do not preserve an inferior abstraction only because it is already present.

### 3. Do not add bridge layers or fallback paths just to protect old local designs

Avoid:

* compatibility shims whose only purpose is to preserve outdated local shapes
* duplicate abstractions kept alive "for safety"
* fallback code paths added only to avoid replacing a weaker design

Allow them only when there is a real external compatibility requirement that the
maintainer explicitly wants to preserve.

### 4. Replacing old local abstractions is allowed

If the new architecture is more correct, more durable, and easier to extend,
replace the old abstraction directly.

This applies to:

* runtime/session/transcript foundations
* task/subagent/fork boundaries
* tool capability and projection contracts
* state schema and persistence layout

### 5. Sequence by architectural leverage, not by easiest patch

When multiple tasks are possible, prefer the one that unlocks or clarifies the
rest of the system, even if it is not the smallest isolated patch.

Examples:

* define a reusable contract before adding multiple ad hoc call sites
* land a missing runtime seam before discussing deeper parity built on top of it
* separate two concepts cleanly before extending either of them

---

## How To Apply This Guide

Before choosing an approach, ask:

1. Which option creates the clearest long-term boundary?
2. Which option avoids future bridge/fallback cleanup work?
3. Which option best supports later adjacent features?
4. Which option would I choose if old local compatibility were not a concern?

If the answers point to a cleaner structure, prefer that structure.

---

## What This Guide Does Not Mean

This guide does **not** mean:

* always choose the biggest rewrite
* ignore validation/testing cost
* reopen explicitly deferred product areas
* introduce speculative abstractions without a clear future consumer

The requirement is to choose the **highest-value coherent structure**, not the
largest possible implementation.

---

## Typical Good Outcomes

* split fork semantics from normal subagent semantics instead of overloading one
  entrypoint
* replace a weak transcript shape rather than layering compatibility shims on top
* make a new contract explicit now instead of encoding it across scattered flags
* keep a feature deferred rather than introducing a low-quality partial copy that
  distorts the architecture

---

## Escalation Rule

Stop and ask the maintainer only when:

* the architecture choice implies a major product-direction change
* there is a real external compatibility requirement that conflicts with this guide
* data loss or irreversible migration is involved

Otherwise, proceed with the cleaner long-term option by default.
