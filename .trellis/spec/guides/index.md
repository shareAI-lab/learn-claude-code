# Thinking Guides

> **Purpose**: Expand your thinking to catch things you might not have considered.

---

## Why Thinking Guides?

**Most bugs and tech debt come from "didn't think of that"**, not from lack of skill:

- Didn't think about what happens at layer boundaries → cross-layer bugs
- Didn't think about code patterns repeating → duplicated code everywhere
- Didn't think about edge cases → runtime errors
- Didn't think about future maintainers → unreadable code

These guides help you **ask the right questions before coding**.

---

## Available Guides

| Guide | Purpose | When to Use |
|-------|---------|-------------|
| [Architecture Posture Guide](./architecture-posture-guide.md) | Keep architecture choices biased toward high-value long-term boundaries instead of smallest-diff compatibility patches | When refactors, runtime foundations, or contract changes present a "clean structure vs minimal patch" choice |
| [CC Alignment Guide](./cc-alignment-guide.md) | Keep cc-haha alignment source-backed and effect-driven | When a feature should align with Claude Code / cc-haha behavior |
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) | Identify patterns and reduce duplication | When you notice repeated patterns |
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | Think through data flow across layers | Features spanning multiple layers |
| [Interview-Driven Spec Expansion Guide](./interview-driven-spec-expansion-guide.md) | Fill Trellis specs through focused maintainer interviews | When missing project knowledge depends on maintainer decisions |
| [Mainline Scope Guide](./mainline-scope-guide.md) | Keep product work focused on the real implementation target | When tutorial/reference assets might distract from `coding-deepgent` |
| [Staged Execution Guide](./staged-execution-guide.md) | Run multi-stage work with explicit checkpoints and bounded validation | When one task family should proceed across sub-stages without drift |
| [Trellis Doc Map Guide](./trellis-doc-map-guide.md) | Explain high-value Trellis document roles, reading order, and update targets | When you need to understand or extend the `.trellis/` document system |

---

## Quick Reference: Thinking Triggers

### When to Think About Cross-Layer Issues

- [ ] Feature touches 3+ layers (API, Service, Component, Database)
- [ ] Data format changes between layers
- [ ] Multiple consumers need the same data
- [ ] You're not sure where to put some logic

→ Read [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md)

### When To Run CC Alignment

- [ ] The task should align with `cc-haha` or Claude Code behavior
- [ ] A feature name or shape looks similar, but the local effect is not yet explicit
- [ ] You need to decide what to align, defer, or intentionally not copy

→ Read [CC Alignment Guide](./cc-alignment-guide.md)

### When to Think About Code Reuse

- [ ] You're writing similar code to something that exists
- [ ] You see the same pattern repeated 3+ times
- [ ] You're adding a new field to multiple places
- [ ] **You're modifying any constant or config**
- [ ] **You're creating a new utility/helper function** ← Search first!

→ Read [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md)

### When To Apply Architecture Posture

- [ ] A cleaner long-term structure conflicts with the smallest patch
- [ ] A refactor would be simpler if old local compatibility were ignored
- [ ] You are deciding whether to replace an old abstraction instead of layering on top
- [ ] A task sequence choice should be driven by architectural leverage, not easiest diff

→ Read [Architecture Posture Guide](./architecture-posture-guide.md)

### When to Check Mainline Scope

- [ ] The repo has both product code and tutorial/reference assets
- [ ] The request mentions docs, skills, tests, or web content that may not be product-critical
- [ ] You're unsure whether parity with tutorial material is actually required

→ Read [Mainline Scope Guide](./mainline-scope-guide.md)

### When To Use Staged Execution

- [ ] The work spans multiple sub-stages or checkpoints
- [ ] You want automatic progression only after an explicit checkpoint verdict
- [ ] The task needs `lean` vs `deep` validation-budget control

→ Read [Staged Execution Guide](./staged-execution-guide.md)

### When To Navigate Trellis Docs

- [ ] You are unsure which Trellis document owns a rule or decision
- [ ] You need the recommended reading order for `coding-deepgent`
- [ ] You are about to interview the user to fill missing Trellis docs

→ Read [Trellis Doc Map Guide](./trellis-doc-map-guide.md)

### When To Interview For Missing Specs

- [ ] Existing code/docs do not answer a project convention question
- [ ] The answer depends on maintainer preference or product direction
- [ ] You know which Trellis document should receive the answer

→ Read [Interview-Driven Spec Expansion Guide](./interview-driven-spec-expansion-guide.md)

---

## Pre-Modification Rule (CRITICAL)

> **Before changing ANY value, ALWAYS search first!**

```bash
# Search for the value you're about to change
grep -r "value_to_change" .
```

This single habit prevents most "forgot to update X" bugs.

---

## How to Use This Directory

1. **Before coding**: Skim the relevant thinking guide
2. **During coding**: If something feels repetitive or complex, check the guides
3. **After bugs**: Add new insights to the relevant guide (learn from mistakes)

---

## Contributing

Found a new "didn't think of that" moment? Add it to the relevant guide.

---

**Core Principle**: 30 minutes of thinking saves 3 hours of debugging.
