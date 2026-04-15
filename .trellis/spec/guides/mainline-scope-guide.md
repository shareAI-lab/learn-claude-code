# Mainline Scope Guide

> **Purpose**: Keep current work focused on the real product mainline instead of drifting into tutorial parity work.

---

## Current Mainline

The current working mainline is:

```text
coding-deepgent/
```

Trellis tasks, plans, code-spec updates, and implementation decisions should
default to serving `coding-deepgent/`.

---

## Reference-Only Layer

The following areas are reference-only by default unless a task explicitly
targets them:

- `agents/`
- `agents_deepagents/`
- `docs/`
- `web/`
- `skills/`
- tutorial/demo-oriented tests and teaching artifacts

These areas can still be useful for:

- teaching and explanation
- source mapping and parity research
- extracting reusable ideas or examples

They are **not** the default implementation target for current product work.

---

## Decision Rule

When a task is ambiguous, decide in this order:

1. Does the task explicitly target tutorial/reference assets?
   - If yes, work there deliberately.
2. If not, does the task affect the current product mainline?
   - If yes, work in `coding-deepgent/` and `.trellis/`.
3. If tutorial/reference material conflicts with product direction:
   - treat the tutorial layer as evidence or examples only
   - prefer `coding-deepgent` product boundaries and Trellis norms

---

## What To Read First

Before implementing in the current mainline, prefer these sources first:

- `AGENTS.md`
- `.trellis/workflow.md`
- `.trellis/project-handoff.md`
- `.trellis/spec/backend/*.md`
- `.trellis/spec/frontend/*.md`
- `coding-deepgent/README.md`
- `coding-deepgent/PROJECT_PROGRESS.md`

Use tutorial/reference docs only after the mainline sources are understood.

---

## Common Mistakes

- treating tutorial chapter parity as the shipping goal
- spending time fixing `web/`, tutorial `docs/`, or teaching tests that do not
  strengthen `coding-deepgent`
- copying tutorial structure into product code without source-backed product
  justification
- keeping duplicate norms outside Trellis after the product rule is already
  captured in `.trellis/`

---

## Practical Consequence For This Repo

For current collaboration:

- Trellis is the canonical coordination and norm layer.
- `coding-deepgent/` is the canonical product codebase.
- tutorial/reference assets should only be updated when explicitly requested or
  when a small change is needed to avoid misleading future work.
