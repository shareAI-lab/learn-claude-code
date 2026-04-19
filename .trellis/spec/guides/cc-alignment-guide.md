# CC Alignment Guide

> **Purpose**: Keep `cc-haha` / Claude Code alignment source-backed, effect-driven, and LangChain-native.

---

## Scope

Use this guide when a `coding-deepgent` feature should align with
`NanmiCoder/cc-haha` or related Claude Code runtime behavior.

This guide is for:

- implementation
- review
- planning
- documentation of feature alignment

It is not a license to copy behavior just because names look similar.

---

## Core Rule

Before code changes, state the **expected effect** first, then produce a
source-backed alignment matrix.

If you cannot explain the concrete local effect, do not align by default.
Mark the behavior as `defer` or `do-not-copy`.

For the current mainline, the default target order is:

1. real Claude Code public behavior
2. `cc-haha` source-backed implementation reference
3. high-quality analogous OSS, only when the first two are insufficient

---

## Required Pre-Code Workflow

1. **Name the feature band**
   - Example: `TodoWrite`, `Skill loading`, `Runtime pressure`, `Verifier execution`
2. **State the expected effect first**
   - What concrete user/runtime/safety/reliability/maintainability effect should appear locally?
3. **Identify cc-haha reference points**
   - List exact source files and, when practical, symbols/functions.
4. **Check real Claude Code public behavior**
   - Note the public behavior, docs, or visible runtime artifact you are
     actually trying to match.
5. **Extract functional essence**
   - What problem does the cc behavior solve?
   - What state does it own?
   - What model-visible surface does it change?
6. **Separate essence from product detail**
   - keep the essence
   - copy product detail only if it creates a concrete local benefit now
7. **Write the alignment matrix before implementation**

If `cc-haha` source is missing or incomplete for the relevant capability:

8. **Run OSS fallback research before implementation**
   - inspect 2-4 high-quality analogous OSS systems
   - summarize the implementation patterns they use
   - record why `cc-haha` evidence was insufficient
   - state which local design was chosen and what remains inferred

## Evidence Ladder

Use this evidence order explicitly:

1. **Claude Code public behavior**
   - official docs
   - public product surfaces
   - reproducible visible behavior
   - public runtime artifacts
2. **`cc-haha` source**
   - files, symbols, docs, comments, and observable behavior
3. **Analogous OSS**
   - high-quality open-source systems in the same capability family
4. **Secondary analysis**
   - books, blogs, third-party explanations

Rules:

* real Claude Code public behavior is the top-level parity target
* `cc-haha` is the default implementation reference when it matches or explains
  the target behavior
* analogous OSS is required when Claude Code public behavior and `cc-haha`
  source do not sufficiently explain how to implement the feature
* secondary analysis is useful context, but must not overrule stronger evidence

## Missing-Source Workflow

When a capability does not have enough accessible source:

1. name the exact source gap
2. state what public Claude Code behavior is still visible
3. inspect 2-4 high-quality OSS systems
4. summarize what each system contributes
5. write the local choice into the PRD before implementation

Required PRD add-on shape:

```md
## Source Gap

- target behavior:
- Claude Code public evidence:
- `cc-haha` evidence:
- why those are insufficient:

## Analogous OSS Review

- project A:
- project B:

## Local Decision

- chosen design:
- why it fits locally:
- what remains inferred:
```

---

## Required Alignment Matrix

Use this shape in the task PRD or planning note before editing code:

```md
## Expected effect

Aligning this behavior should improve: <category>. The local user/runtime effect
is: <specific outcome>. If this effect does not appear, the change is not worth
shipping.

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Tool/schema | `TodoWrite(todos=...)` | fewer model JSON mistakes | strict tool schema | align | Match model-visible contract |
| Runtime state | `appState.todos[...]` | correct isolation semantics | local state domain | defer | Requires later stage |
```

Status vocabulary:

- `align`
- `partial`
- `defer`
- `do-not-copy`
- `unknown/inferred`

---

## Decision Rules

### Align when

- the effect is specific and valuable now
- the behavior is model-visible contract or essential state semantics
- it prevents a known failure mode
- it fits naturally into official LangChain/LangGraph primitives

### Defer when

- the effect depends on a later capability or stage
- it would force speculative abstractions
- it is real cc behavior but not current mainline priority

### Do-not-copy when

- it is only UI/TUI detail
- it is provider-specific plumbing better handled by LangChain
- it conflicts with a simpler local abstraction
- it would blur current product boundaries

---

## Mandatory Boundary Checks

Before implementation, answer these explicitly:

1. What is the expected effect?
2. What is in scope?
3. What are the non-goals?
4. What state is short-term, persistent, shared, or model-visible?
5. What exact model-visible tool/prompt/schema surface changes?
6. Which LangChain/LangGraph primitive should express it?

Valid local primitives usually include:

- strict tool + Pydantic schema
- `Command(update=...)`
- middleware hook
- typed state schema / reducer
- store / memory seam
- graph node / edge

---

## Documentation Rule For This Repo

For the current `coding-deepgent` mainline:

- record cc alignment decisions in the active Trellis task PRD first
- update `.trellis/plans/` only when the decision becomes roadmap/product direction
- update `.trellis/spec/` only when the decision becomes an executable implementation constraint
- do **not** default to tutorial-track `agents_deepagents/cc_alignment/` docs
  unless the task explicitly targets tutorial/reference assets

Do not put every exploratory source note into canonical plans or specs. Promote
only stable decisions.

---

## Verification Requirements

Evidence should prove both:

1. **cc-haha mapping evidence**
   - source files/symbols cited
   - matrix decisions recorded
   - intentional gaps documented
2. **local behavior evidence**
   - tests for model-visible schema
   - tests for state/update shape
   - tests for boundary guards
   - grep or review checks for stale public names when needed

---

## Anti-Patterns

Avoid:

- using `cc-haha` as if it were automatically the highest target even when
  real Claude Code public behavior says otherwise
- implementing from memory without inspecting source
- jumping directly from a source gap to local design without OSS fallback
- copying file names without functional intent
- line-for-line cloning when LangChain has a simpler primitive
- treating secondary analysis as stronger than source behavior
- leaving alignment status implicit

---

## Final Output Checklist

Report:

- expected effect
- source files/symbols inspected
- alignment matrix summary
- what aligned now
- what was deferred or intentionally not copied
- files changed
- verification evidence
