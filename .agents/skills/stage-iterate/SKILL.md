---
name: stage-iterate
description: Run a staged implementation plan end-to-end with Trellis, cc-haha alignment, LangChain architecture guard, tests, and an explicit checkpoint gate after each sub-stage. Use when the user wants long-running staged work, iterative implementation, or continuing a roadmap such as Stage 12A/12B without drifting.
---

# Stage Iterate

Use this skill for staged product work where implementation should proceed over one or more sub-stages without losing alignment or blindly continuing after a boundary changes.

Primary example:

```text
$stage-iterate Stage 12 Context and Recovery Hardening
```

## Cost Modes

This skill has two execution modes:

* `lean` (default)
* `deep`

If the user does not explicitly request a long-running, high-context, or all-in-one pass, default to `lean`.

Use `deep` only when the user explicitly opts in with wording like:

* `deep mode`
* `long-run`
* `do the whole chain`
* `one-shot`
* `full validation`
* `read everything again`

### `lean` mode rules

Use these by default:

* Work one sub-stage at a time.
* Do not automatically re-read large source/doc sets already captured in recent PRDs unless a real ambiguity appears.
* Prefer focused tests over broad regression.
* Do not automatically run full `pytest`, full `mypy`, or broad docs/git/PR updates.
* If the checkpoint decision is `continue`, automatically move to the next sub-stage, but keep the validation and context budget lean.

### `deep` mode rules

Use these only on explicit opt-in:

* Auto-continue after `APPROVE`.
* Broader re-orientation is allowed.
* Combined/full validation is allowed when justified.
* Git/PR/doc updates may be folded into the same run if requested.

## Core Rule

Do not move from one sub-stage to the next automatically just because tests pass.

After every sub-stage, run a checkpoint gate and choose exactly one outcome:

* `continue`: next sub-stage still holds and can start.
* `adjust`: update the next sub-stage plan before continuing.
* `split`: create a prerequisite task before continuing.
* `stop`: ask the user because scope, alignment, tests, or architecture are no longer safe.

If the checkpoint result is `continue`, immediately begin the next planned sub-stage without waiting for additional user approval.

In `lean` mode, `continue` still means continue.

The difference from `deep` is:

* narrower context reuse
* narrower validation scope
* no automatic broad docs/git/PR work

Only interrupt the long-running workflow when:

* the checkpoint result is `adjust`, `split`, or `stop`
* the user explicitly interrupts or redirects the work
* a hard blocker appears that cannot be resolved locally

Use an explicit sub-stage state machine:

* `planning`
* `implementing`
* `verifying`
* `checkpoint`
* `terminal`

When resuming the same stage workflow later, continue from the current active state instead of replaying the whole orientation process from scratch.

If recent PRDs or stage ledgers already contain the required source mapping, expected effect, and boundaries, do not re-run a large source-reading pass by default in `lean` mode.

## Workflow

### 1. Orient

Run the normal Trellis session/task checks:

```bash
python3 ./.trellis/scripts/get_context.py
python3 ./.trellis/scripts/task.py list
```

If a matching task already exists, read its `prd.md` and `task.json`.

If there is already an active stage-iterate run for the same stage family, resume it from the current sub-stage/state instead of restarting the whole workflow.

If no matching task exists, create one:

```bash
python3 ./.trellis/scripts/task.py create "<stage title>" --slug <slug>
```

In `lean` mode, prefer:

* read the latest relevant checkpoint and PRD first
* reuse prior source mapping if it is still sufficient
* only expand source reading when the current sub-stage introduces a genuinely new feature band

### 2. Confirm Scope From Existing Plans

Read the stage plan and any target design docs relevant to the request.

For this project, common inputs are:

```text
.omx/plans/coding-deepgent-cc-core-highlights-roadmap.md
.omx/plans/coding-deepgent-h01-h10-target-design.md
.trellis/tasks/<task>/prd.md
```

If the stage references cc-haha behavior, use `$cc-haha-alignment` before implementation.

If it touches LangChain/LangGraph code, use `$langchain-architecture-guard` before implementation.

If it changes backend product code, use `$before-backend-dev` before implementation.

In `lean` mode, "use" these skills by reusing their already-recorded conclusions when available, instead of always repeating the full discovery pass.

### 3. Prepare A Sub-Stage PRD

Before coding a sub-stage, the PRD must include:

* goal and concrete benefit
* cc-haha source files/symbols to inspect
* LangChain-native boundary
* requirements and acceptance criteria
* explicit out-of-scope items
* test plan

For infrastructure work, include what future stage the infrastructure unlocks.

### 4. Execute Trellis Task Workflow

After the PRD is clear:

```bash
python3 ./.trellis/scripts/task.py init-context "$TASK_DIR" backend
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" implement "<path>" "<reason>"
python3 ./.trellis/scripts/task.py add-context "$TASK_DIR" check "<path>" "<reason>"
python3 ./.trellis/scripts/task.py start "$TASK_DIR"
```

Then implement and test the sub-stage.

### 4.1 Validation Budget

Default validation by mode:

* `lean`
  - focused tests only
  - targeted lint/typecheck only on changed files
  - full-suite validation only when:
    - the user asks
    - the sub-stage changes cross-cutting contracts
    - focused validation exposes ambiguity that broader tests must resolve
* `deep`
  - focused tests plus broader regression as appropriate

When the user says they want to defer heavy validation until later, honor that unless the current change would be unsafe without minimal verification.

### 4.5 Optional Subagent Parallelization

Use subagents only when the user explicitly authorizes subagents, delegation, or parallel agent work in the current conversation.

Good delegation targets:

* independent codebase research
* cc-haha source mapping for different modules
* test coverage audit
* non-overlapping code edits with clear file ownership

Do not delegate:

* immediate blocking work needed for the next local step
* final architecture decisions
* tightly coupled edits in the same file
* work that duplicates what the main agent is already doing

For worker subagents, state:

* they are not alone in the codebase
* they must not revert others' changes
* their file ownership is limited to the assigned paths
* their final response must list changed files and verification run

For explorer subagents, ask for a concrete bounded answer and avoid broad "read everything" prompts.

### 5. Checkpoint Gate

At the end of every sub-stage, write a checkpoint summary with:

* implemented behavior
* tests run and result
* files changed
* cc-haha alignment evidence
* LangChain-native architecture evidence
* new boundary issues discovered
* architecture drift risks
* whether the next sub-stage still holds

Also assign an internal checkpoint verdict:

* `APPROVE` → maps to `continue`
* `ITERATE` → maps to `adjust` or `split`
* `REJECT` → maps to `stop`

Use this decision table:

| Condition | Decision |
|---|---|
| Tests fail | `stop` or `adjust` |
| cc-haha alignment missing for a cc-targeted behavior | `stop` |
| LangChain-native implementation would be compromised | `stop` or `split` |
| Next sub-stage depends on a newly discovered prerequisite | `split` |
| Plan is still valid but needs scope changes | `adjust` |
| No blockers and next sub-stage remains valid | `continue` |

Execution rule after the checkpoint:

* `continue` → start the next sub-stage immediately
* `adjust` → rewrite the next sub-stage plan, then continue only if the rewrite resolves the issue
* `split` → create the prerequisite task and stop the main staged run
* `stop` → stop and ask the user

Always append the checkpoint to a stage ledger in the active task notes or linked planning doc so later resumes can pick up from the latest verified state.

### 6. Improve This Skill When It Fails

If this skill did not prevent drift, ambiguity, over-scoping, missing tests, or missing alignment, update it.

Also update it when:

* a long-running run consumed unnecessary context by re-reading already-settled planning/source material
* it defaulted to broader validation than the user needed
* it auto-continued when the user actually wanted a cheaper one-sub-stage cadence

Use this lightweight improvement loop:

1. Record the failure in the active task summary.
2. Identify whether the missing guard belongs in `SKILL.md` or `references/stage-iteration-protocol.md`.
3. Patch the skill immediately if the issue is reusable.
4. Re-run the skill validator.

## Reference

For the longer protocol and checkpoint template, read:

```text
.agents/skills/stage-iterate/references/stage-iteration-protocol.md
```
