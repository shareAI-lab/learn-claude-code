# Interview-Driven Spec Expansion Guide

> **Purpose**: Help AI agents fill Trellis docs through focused interviews without creating duplicate or unfocused documentation.

---

## Scope

Use this guide when Trellis docs need more real project knowledge, but the
missing facts depend on maintainer judgment, project preference, or tacit team
conventions.

This guide is for `coding-deepgent` mainline documentation, not tutorial or
reference-layer cleanup.

---

## Core Principle

Interviewing is not a chat transcript.

Each answer should land in the narrowest Trellis document that owns the rule,
contract, decision, or checklist.

Use [Trellis Doc Map Guide](./trellis-doc-map-guide.md) before interviewing so
the destination is clear.

---

## When To Interview

Interview when the missing information is:

- a real project preference that cannot be derived from code
- a rule the maintainer wants future agents to follow
- a decision boundary between multiple valid approaches
- a review expectation not yet captured in specs
- a recurring ambiguity that causes repeated explanations

Do not interview when the answer can be derived by reading:

- current code
- existing Trellis docs
- task PRDs
- tests
- official dependency documentation

Derive first, then ask only the remaining high-value question.

---

## Interview Workflow

### 1. Select One Topic

Pick one narrow topic, for example:

- module ownership
- testing expectations
- when to update a roadmap vs a spec
- accepted `cc-haha` alignment boundary
- how strict a LangChain schema should be

Avoid broad prompts like:

```text
Tell me all project rules.
```

### 2. Identify The Target Document

Before asking, decide where the answer will go:

| Answer type | Target |
|---|---|
| work process | `.trellis/workflow.md` |
| current mainline status | `.trellis/project-handoff.md` |
| roadmap / product direction | `.trellis/plans/*.md` |
| implementation rule | `.trellis/spec/backend/*.md` |
| thinking trigger | `.trellis/spec/guides/*.md` |
| completed-session record | `.trellis/workspace/<developer>/journal-N.md` via `record-session` |

If no target is clear, create a short proposal first instead of asking a broad
question.

Plans vs specs shortcut:

- use `plans/` for goals, roadmap, sequencing, and strategic tradeoffs
- use `spec/` for implementation contracts, boundaries, schemas, and tests
- if a plan decision becomes mandatory for implementation, extract it into the owning spec

### 3. Ask One Question

Ask exactly one high-value question at a time.

Good question shape:

```text
For <specific topic>, should future agents follow A or B?

1. A - <tradeoff>
2. B - <tradeoff>
3. Other - describe your preference
```

### 4. Update The Owning Document Immediately

After the answer:

- move the decision into the target Trellis doc
- add an example or anti-pattern if useful
- update indexes only if a new high-value doc or section was added
- do not leave the decision only in the conversation

### 5. Record The Interview Trail In The Active PRD

The active task PRD should record:

- question asked
- answer summary
- target document updated
- acceptance criteria changed, if any

This makes the interview auditable without turning the target spec into a chat
log.

Use workspace journals only after the work is completed and committed via
`record-session`. Do not put active interview decisions only in the journal.

---

## Question Gate

Before asking, check:

- Can I derive this from code/tests/docs?
- Is this a real preference or blocking decision?
- Do I know which Trellis doc will receive the answer?
- Can I ask it as one concrete question?

If any answer is "no", inspect more or narrow the topic.

---

## Good Interview Topics For This Repo

High-value topics:

- `coding-deepgent` module ownership boundaries
- LangChain/LangGraph abstraction tolerance
- when `cc-haha` behavior should be `align`, `partial`, `defer`, or `do-not-copy`
- required verification level for staged work
- when docs belong in `plans/` vs `spec/backend/`
- what should be recorded in `project-handoff.md` vs session journals

Low-value topics:

- asking for content already visible in files
- asking the user to enumerate code structure without inspection
- trying to fill every placeholder spec at once
- asking broad philosophical questions without a write target

---

## Output Format For An Interview Round

Use this compact structure in the active PRD:

```md
## Interview Note: <topic>

Question:
- <exact question or summary>

Answer:
- <maintainer decision>

Target doc:
- `<path>`

Change made:
- <section updated / rule added>
```

---

## MVP Interview Loop

For the first Trellis expansion pass, use this sequence:

1. Build the current doc map.
2. Identify top 3 gaps.
3. Pick the highest-value gap.
4. Ask one question.
5. Update the owning doc.
6. Re-check whether the next gap is still valid.

Do not run an open-ended interview marathon.

---

## Stop Conditions

Stop interviewing when:

- the next question is broad or low-confidence
- the target document is unclear
- the user gives a product decision that should become a separate PRD
- updating the target doc would conflict with existing Trellis guidance
- the interview has already produced enough changes for one reviewable slice

---

## Maintenance Rule

This guide owns the interview process.

It does not own the resulting project rules. Those must be written into the
specific Trellis docs that govern the topic.
