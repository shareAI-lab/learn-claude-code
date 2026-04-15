# Trellis Doc Map Guide

> **Purpose**: Explain the high-value `.trellis/` documents for the current `coding-deepgent` mainline: what each layer owns, what to read first, and where new knowledge should be written.

---

## Scope

This guide maps only the high-value Trellis documents used in current
`coding-deepgent` work.

It intentionally does not document every internal script, config file, archived
task, or implementation detail under `.trellis/`.

Use this as:

- a maintainer map for Trellis document responsibilities
- an AI-agent map for reading order and update targets

---

## Core Principle

Trellis should not become one giant handbook.

Use this structure instead:

- `workflow.md` explains **how work moves**
- `project-handoff.md` explains **where the current mainline stands**
- `plans/` explains **long-lived product direction**
- `spec/backend/` explains **how to implement safely**
- `spec/guides/` explains **how to think before changing things**
- `workspace/` records **what happened after work is done**

When adding new knowledge, update the narrowest document that owns it.

---

## High-Value Document Layers

| Layer | Main paths | Owns | Does not own |
|---|---|---|---|
| Workflow | `.trellis/workflow.md` | session flow, task lifecycle, staged execution protocol, finish/record expectations | product architecture details |
| Mainline handoff | `.trellis/project-handoff.md` | current `coding-deepgent` goal, latest verified state, minimal resume procedure | detailed implementation contracts |
| Long-lived plans | `.trellis/plans/index.md`, `.trellis/plans/*.md` | roadmaps, reconstructed master plans, target designs, canonical dashboards | day-to-day coding conventions |
| Backend specs | `.trellis/spec/backend/index.md`, `.trellis/spec/backend/*.md` | implementation contracts, module boundaries, quality rules, LangChain-native rules | broad brainstorming notes |
| Thinking guides | `.trellis/spec/guides/index.md`, `.trellis/spec/guides/*.md` | pre-implementation thinking, source alignment, staged work, scope checks | exact code/API contracts |
| Workspace records | `.trellis/workspace/index.md`, `.trellis/workspace/<developer>/journal-N.md` | session history, completed work summaries, commit/session records | future requirements or canonical rules |

---

## Reading Order

### For Maintainers

Use this path when you want to understand or reshape the project direction:

1. `AGENTS.md`
2. `.trellis/workflow.md`
3. `.trellis/project-handoff.md`
4. `.trellis/plans/index.md`
5. `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
6. `.trellis/spec/backend/index.md`
7. `.trellis/spec/guides/index.md`

Then open only the specific topic docs needed for the current decision.

### For AI Agents

Use this path before implementation:

1. `AGENTS.md`
2. `.trellis/workflow.md`
3. `python3 ./.trellis/scripts/get_context.py`
4. `.trellis/project-handoff.md` if the task is about current `coding-deepgent` mainline state
5. `.trellis/spec/backend/index.md` for backend/product work
6. `.trellis/spec/guides/index.md` for thinking triggers
7. active task `prd.md` and injected `implement.jsonl` / `check.jsonl`

Do not read broad `.trellis/tasks/` or `.trellis/plans/` trees unless a real
ambiguity remains.

---

## Where To Write New Knowledge

| New knowledge type | Write it here | Example |
|---|---|---|
| Work process changed | `.trellis/workflow.md` | staged validation budget changed |
| Current mainline status changed | `.trellis/project-handoff.md` | latest verified stage family updated |
| Ordinary completed session | `.trellis/workspace/<developer>/journal-N.md` via `record-session` | daily progress or minor implementation summary |
| Long-term roadmap changed | `.trellis/plans/*.md` | H-row status or MVP boundary changed |
| Module ownership or layout changed | `.trellis/spec/backend/directory-structure.md` | new domain package added |
| LangChain/LangGraph rule changed | `.trellis/spec/backend/langchain-native-guidelines.md` | tool schema rule changed |
| Review/testing rule changed | `.trellis/spec/backend/quality-guidelines.md` | new forbidden pattern |
| Runtime/session/compact contract changed | `.trellis/spec/backend/runtime-context-compaction-contracts.md` | new compact record invariant |
| Task/plan/verifier contract changed | `.trellis/spec/backend/task-workflow-contracts.md` | new verifier evidence rule |
| Thinking checklist changed | `.trellis/spec/guides/*.md` | new scope or alignment trigger |
| Work was completed and committed | `.trellis/workspace/<developer>/journal-N.md` via `record-session` | session summary |

---

## Plans Vs Specs Boundary

Use `.trellis/plans/` for direction.

Plans own:

- product goals
- roadmap rows
- stage sequencing
- strategic tradeoffs
- deferred / do-not-copy decisions
- current or future milestone boundaries

Use `.trellis/spec/` for execution.

Specs own:

- implementation contracts
- schemas and signatures
- module boundaries
- validation/error matrices
- testing requirements
- concrete do/don't rules for future code changes

If a plan decision becomes something every implementation must obey, extract
that rule into the owning spec. Do not force future agents to read broad plans
to discover executable constraints.

---

## Task PRD Vs Workspace Journal Boundary

Use the active task PRD while work is in progress.

Task PRDs own:

- requirements and acceptance criteria
- interview notes
- scope decisions
- implementation checkpoints
- verification evidence for the task
- unresolved questions and follow-up decisions

Use workspace journals after work is completed and committed.

Workspace journals own:

- completed session summaries
- commit lists
- final testing notes
- next-step handoff after a completed session

Do not require future agents to search journals to recover active task
requirements. Keep active decisions in the active task PRD until the work is
done.

---

## Task Archive Boundary

Keep active tasks focused on work still being decided, implemented, or verified.

Archive a task when:

- acceptance criteria are met
- verification is complete for the task's risk level
- the human has committed the work, or the task is docs/planning-only and
  explicitly complete

Do not keep tasks open just because task metadata still says `planning` or
`in_progress`.

Workspace journals record completed sessions; archived tasks preserve the
task-level requirements and decisions.

---

## When Specs Must Be Updated

Update `.trellis/spec/*` when a change creates or changes an executable
contract future agents must obey.

Required spec-update triggers:

- tool schema, command, or public API shape changes
- runtime state fields or payload formats change
- module ownership or boundary changes
- validation or error behavior changes
- testing requirements or verification matrix changes
- cross-layer data transformation changes
- a repeated mistake becomes a rule or anti-pattern

Do not update specs for ordinary implementation detail that does not affect
future implementation or review behavior.

When unsure, write the decision in the active task PRD first, then extract it
to the owning spec only if it becomes reusable.

---

## CC Alignment Record Placement

Record `cc-haha` alignment in this order:

1. Active task PRD:
   - expected effect
   - source files inspected
   - alignment matrix
   - `align / partial / defer / do-not-copy` decisions
2. `.trellis/plans/`:
   - only stable roadmap/product-direction outcomes
3. `.trellis/spec/`:
   - only executable implementation constraints future agents must obey

Do not let exploratory source notes become canonical specs by default.

---

## Summary Docs Vs Atomic Specs

Use summary/map docs for:

- orientation
- reading order
- responsibility boundaries
- "where should this go?" decisions

Use atomic specs for:

- concrete implementation rules
- signatures and contracts
- validation/error matrices
- examples and anti-patterns

Do not duplicate detailed rules from atomic specs into map docs. Link or point
to the owning spec instead.

---

## Interview-Driven Expansion

This map is the entrypoint for later interview-based Trellis expansion.

When interviewing the user to fill docs:

1. Identify the missing knowledge category.
2. Choose the owning Trellis document from the table above.
3. Ask one targeted question.
4. Write the answer into the owning document, not into this map.
5. Update this map only if the document structure or routing rule changes.

Good interview targets:

- unclear module ownership
- recurring review concerns
- unstated testing expectations
- accepted `cc-haha` alignment boundaries
- when to update specs vs plans vs workspace records

---

## Current Mainline Bias

This map serves `coding-deepgent`.

Tutorial/reference assets such as `agents/`, `agents_deepagents/`, `docs/`, and
`web/` are not default implementation targets. Use
`mainline-scope-guide.md` when that boundary is unclear.

---

## Maintenance Rules

- Keep this guide short enough to scan.
- Add new Trellis documents to the map only when they become high-value entrypoints.
- Prefer updating the owning atomic doc over expanding this guide.
- If two docs appear to own the same rule, clarify ownership here and remove duplication from one side.
