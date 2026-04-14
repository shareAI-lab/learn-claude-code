---
name: project-handoff
description: "Load the minimal coding-deepgent handoff context for a new session without re-reading large planning trees."
---

# Project Handoff

Use this skill at the start of a new `coding-deepgent` session when you need to resume work with minimal context cost.

## Goal

Load only the compact handoff state and the few canonical project documents needed to continue safely.

## Read In This Order

1. `.trellis/project-handoff.md`
2. `.trellis/tasks/04-14-redefine-coding-deepgent-final-goal/prd.md`
3. `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
4. `coding-deepgent/PROJECT_PROGRESS.md`
5. `.trellis/spec/backend/runtime-context-compaction-contracts.md`
6. `.trellis/spec/backend/task-workflow-contracts.md`

## Then Refresh Live State

Run only these lightweight commands:

```bash
git branch --show-current
git status -sb
gh pr view 220 --repo shareAI-lab/learn-claude-code --json number,title,url,isDraft,headRefName,baseRefName
```

## If You Need The Latest Stage Details

Read only the most recent completed/active stage PRDs relevant to the requested work.

Current default shortlist:

```text
.trellis/tasks/04-15-stage-17c-explicit-plan-artifact-boundary/prd.md
.trellis/tasks/04-15-stage-17d-verifier-subagent-execution-boundary/prd.md
.trellis/tasks/04-15-stage-18a-verifier-execution-integration/prd.md
```

Do not expand beyond this shortlist unless the current task introduces a new feature band or a real ambiguity appears.

## Output

After loading context, summarize briefly:

* current branch / PR
* current mainline stage family
* latest completed stage(s)
* active next task or recommended next step
* any uncommitted changes

## Rules

* Prefer the handoff document over re-reading broad `.trellis/plans` and `.trellis/tasks` trees.
* Reuse verified stage checkpoints already written in PRDs.
* Do not start implementation until this minimal resume pass is complete.
