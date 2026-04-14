# Stage Iteration Protocol

Use this protocol when a user asks Codex to work through a multi-stage roadmap over time.

## Stage Checklist

Before implementation:

- [ ] A Trellis task exists.
- [ ] A PRD exists.
- [ ] Relevant cc-haha source files are named.
- [ ] Expected benefit is concrete.
- [ ] LangChain-native primitive is chosen.
- [ ] Out-of-scope list is explicit.
- [ ] Tests are named.
- [ ] If subagents are used, each subagent has a concrete non-overlapping task.
- [ ] A current sub-stage state is recorded (`planning` / `implementing` / `verifying` / `checkpoint` / `terminal`).

During implementation:

- [ ] Keep each sub-stage small.
- [ ] Do not implement future sub-stages opportunistically.
- [ ] Do not add wrappers or framework layers without a real boundary.
- [ ] Preserve existing user changes in dirty worktrees.
- [ ] Keep delegated work off the immediate critical path unless the main agent is blocked.
- [ ] Assign disjoint file ownership to worker subagents.

After implementation:

- [ ] Run focused tests.
- [ ] Run lint/typecheck where appropriate.
- [ ] Update planning docs/status if architecture-visible behavior changed.
- [ ] Run the checkpoint gate before moving on.

## OMX-Derived Improvements

These patterns are adapted from prior OMX-style long-running workflows:

1. **Resume current active state**
   If a stage family is already active, continue from the current sub-stage instead of re-running orientation from zero.
2. **Terminal verdict vocabulary**
   Use an internal verdict of `APPROVE`, `ITERATE`, or `REJECT` at checkpoints.
   Map them to stage decisions:
   - `APPROVE` → `continue`
   - `ITERATE` → `adjust` or `split`
   - `REJECT` → `stop`
3. **Stage ledger**
   Keep a compact ledger of sub-stage checkpoints so long-running work can resume from verified state.
4. **Long-run continuity**
   Do not stop merely to summarize progress when the checkpoint result is `continue`.
5. **Role-shaped side work**
   Use bounded side agents for research, review, or test audit, but keep final synthesis in the main agent.

## Subagent Delegation Template

Use this shape when delegating a subtask:

```text
You are working in a shared codebase. Do not revert changes you did not make.
Task: <bounded task>
Ownership: <paths/modules the worker owns>
Do not edit: <paths/modules outside ownership>
Output: final answer must include changed files, key decisions, and verification run.
```

## Checkpoint Template

```markdown
## Checkpoint: <sub-stage>

State:
- planning | implementing | verifying | checkpoint | terminal

Verdict:
- APPROVE | ITERATE | REJECT

Implemented:
- ...

Verification:
- ...

cc-haha alignment:
- Source files inspected:
- Aligned:
- Deferred:
- Do-not-copy:

LangChain architecture:
- Primitive used:
- Why no heavier abstraction:

Boundary findings:
- New issue:
- Impact on next stage:

Decision:
- continue | adjust | split | stop

Reason:
- ...
```

## Autopilot Rule

If a checkpoint result is `continue`, do not pause for a user approval summary.

Instead:

1. record the checkpoint in the active task or planning notes
2. update the next sub-stage task/PRD if needed
3. immediately start the next sub-stage

Only stop the staged run when the checkpoint result is `adjust`, `split`, or `stop`, or when a real blocker appears.

## Stop Conditions

Stop and ask the user when:

- the next stage's scope is no longer true
- tests are failing and the fix is not local to the current sub-stage
- a cc-haha behavior needs a source mapping that has not been done
- the implementation would require replacing LangChain/LangGraph runtime seams
- the worktree contains conflicting changes that were not made by Codex
- the next step would require a new product decision

## Self-Improvement Triggers

Update this skill when:

- a checkpoint missed a real risk
- the skill allowed scope creep
- a recurring alignment step was forgotten
- a future stage required information that should have been captured earlier
- the user had to restate the same process rule
