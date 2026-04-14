# coding-deepgent Project Handoff

Updated: 2026-04-15
Primary branch: `codex/stage-12-14-context-compact-foundation`
Primary PR: `#220` `https://github.com/shareAI-lab/learn-claude-code/pull/220`

## Product Goal

`coding-deepgent` is the product track that should implement the essential `cc-haha` / Claude Code runtime logic through LangChain/LangGraph-native primitives, while staying professional-grade, modular, maintainable, and non-demo.

Canonical goal/backlog docs:

* `.trellis/tasks/04-14-redefine-coding-deepgent-final-goal/prd.md`
* `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`

## Current Mainline

Current mainline has focused on:

* context / compact / session / recovery hardening
* durable task / workflow hardening

Latest completed stage families:

* Stage 12: Context and Recovery Hardening
* Stage 13: Context Compaction v1
* Stage 14A: Explicit Generated Summary CLI Wiring
* Stage 15: Compact Persistence Semantics
* Stage 16: Virtual Transcript Pruning
* Stage 17A/17B/17C/17D: Durable Task and Workflow Hardening

## Latest Verified State

Latest completed stages and what they changed:

* `17A`: durable task graph invariants
  * rejects missing dependencies, self-dependencies, cycles
  * exposes `ready` in `task_list`
* `17B`: verification workflow boundary
  * emits `verification_nudge` when a 3+ task graph closes without a verification task
* `17C`: explicit plan artifacts
  * `PlanArtifact`, `plan_save`, `plan_get`
  * required `verification` field
  * separate plan namespace from task namespace
* `17D`: verifier execution boundary
  * verifier subagent requires `plan_id`
  * verifier resolves durable plan artifact before execution
  * verifier returns structured JSON result
  * verifier allowlist includes `plan_get`, excludes `plan_save`

## Current Contracts

Read these before coding in the current mainline:

* `.trellis/spec/backend/runtime-context-compaction-contracts.md`
* `.trellis/spec/backend/task-workflow-contracts.md`

## Current Product Modules

Core domains:

* `runtime`
* `tool_system`
* `filesystem`
* `todo`
* `sessions`
* `memory`
* `compact`
* `permissions`
* `hooks`
* `skills`
* `tasks`
* `subagents`
* `mcp`
* `plugins`
* `prompting`

## Next Recommended Task

Next planned direction:

* `18A`: Verifier Execution Integration

Intent:

* connect the `17D` verifier input boundary to a real bounded verifier execution path
* keep it explicit and non-UI
* do not add coordinator runtime, mailbox, background worker execution, or automatic task mutation after verifier completion

## Resume Strategy

When starting a new session:

1. Read this handoff file first.
2. Refresh live state:
   * `git branch --show-current`
   * `git status -sb`
   * `gh pr view 220 --repo shareAI-lab/learn-claude-code --json number,title,url,isDraft,headRefName,baseRefName`
3. Read only the latest relevant PRDs if needed:
   * `.trellis/tasks/04-15-stage-17c-explicit-plan-artifact-boundary/prd.md`
   * `.trellis/tasks/04-15-stage-17d-verifier-subagent-execution-boundary/prd.md`
   * `.trellis/tasks/04-15-stage-18a-verifier-execution-integration/prd.md`

## Cost Control

Default to `stage-iterate` lean mode:

* auto-progress sub-stages
* avoid large re-reads unless a real ambiguity appears
* prefer focused tests
* avoid broad docs/git/PR work unless explicitly requested
