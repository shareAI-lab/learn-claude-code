# Stage 25: Todo Task Plan Verify Closeout

## Goal

Close the highest-value remaining H08/H09/H10 MVP gaps by tightening TodoWrite, durable task graph, and plan/execute/verify workflow contracts without adding coordinator runtime or mailbox features.

## Function Summary

This stage should identify and implement the smallest concrete changes that make short-term planning, durable task collaboration state, and explicit plan/verify workflow count as MVP-complete for Approach A.

## Expected Benefit

* Reliability: planning state and durable task state remain distinct and predictable.
* Testability: TodoWrite/task/plan/verifier contracts become easier to audit and lock.
* Product parity: H08/H09/H10 move from broadly working to explicit MVP closeout.

## Corresponding Highlights

* `H08 TodoWrite as short-term planning contract`
* `H09 Durable Task graph as collaboration state`
* `H10 Plan / Execute / Verify workflow discipline`

## Corresponding Modules

* `coding_deepgent.todo`
* `coding_deepgent.tasks`
* `coding_deepgent.subagents`
* `coding_deepgent.sessions`
* `coding_deepgent.tool_system`

## Out Of Scope

* coordinator runtime
* mailbox / SendMessage
* background worker execution
* task-backed general agent lifecycle beyond current verifier path
* automatic task mutation from verifier result

## Acceptance Criteria

* [x] cc-haha source mapping for H08/H09/H10 is recorded in this stage PRD.
* [x] local H08/H09/H10 MVP closeout slices are explicit.
* [x] focused tests, targeted ruff, and targeted mypy pass for changed files.
* [x] checkpoint records whether H08/H09/H10 become implemented or remain partial with an explicit minimal residual.

## cc-haha Alignment

### Expected Effect

Aligning this behavior should improve reliability, testability, and workflow discipline. The local runtime effect is: TodoWrite remains session-local short-term planning, durable Task remains a separate validated graph, and plan/verify remains explicit without introducing coordinator or mailbox runtime.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| TodoWrite short-term checklist | TodoWrite is session-scoped progress tracking, not durable task graph state | keep local planning state cheap and separate from durable tasks | TodoWrite schema/service/middleware contracts | align | Close with overlong-list regression |
| Durable task graph | task tools own durable task graph state, transitions, dependencies, and listing | keep task graph visible and deterministic | terminal visibility and verification-task detection tests | partial | Close MVP graph contracts now |
| Plan/verify discipline | plan and verify prompts/tools push independent verification after work | verifier path remains explicit/read-only and plan-bound | existing plan/verifier evidence path plus verification nudge tests | partial | Close MVP workflow; defer coordinator |
| Coordinator/mailbox/team runtime | upstream has richer multi-agent workflow surfaces | useful later but out of MVP | none | defer | Do not add in Stage 25 |

### Source files inspected

Explorer A inspected:

* `/root/claude-code-haha/src/tools/TodoWriteTool/TodoWriteTool.ts`
* `/root/claude-code-haha/src/tools/TodoWriteTool/prompt.ts`
* `/root/claude-code-haha/src/utils/tasks.ts`
* `/root/claude-code-haha/src/Task.ts`
* `/root/claude-code-haha/src/tools/TaskCreateTool/TaskCreateTool.ts`
* `/root/claude-code-haha/src/tools/TaskUpdateTool/TaskUpdateTool.ts`
* `/root/claude-code-haha/src/tools/TaskListTool/TaskListTool.ts`
* `/root/claude-code-haha/src/tools/TaskGetTool/TaskGetTool.ts`
* `/root/claude-code-haha/src/tools/EnterPlanModeTool/EnterPlanModeTool.ts`
* `/root/claude-code-haha/src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts`
* `/root/claude-code-haha/src/tools/AgentTool/built-in/verificationAgent.ts`
* `/root/claude-code-haha/src/skills/bundled/verify.ts`

## Technical Approach

* Close H08 with a TodoWrite overlong-list regression to keep short-term planning bounded.
* Close H09 with terminal task visibility regression for `task_list(include_terminal=True)`.
* Close H10 with verification task metadata recognition and cancelled-task boundary regression.
* Preserve the existing verifier result persistence/evidence path from Stages 18-19.

## Checkpoint: Stage 25

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added `task_list(include_terminal=True)` regression covering completed/cancelled task visibility and default terminal filtering.
- Added verification-task metadata recognition regression with cancelled task boundary behavior.
- Added TodoWrite overlong short-term-plan regression for the 12-item limit.

Corresponding highlights:
- `H08 TodoWrite as short-term planning contract`
- `H09 Durable Task graph as collaboration state`
- `H10 Plan / Execute / Verify workflow discipline`

Corresponding modules:
- `coding_deepgent.todo`
- `coding_deepgent.tasks`
- `coding_deepgent.subagents`
- `coding_deepgent.sessions`

Tradeoff / complexity:
- Chosen: close the local contracts with focused regressions; no new runtime layer.
- Deferred: coordinator runtime, mailbox / SendMessage, background worker execution, automatic task mutation from verifier results.
- Why this complexity is worth it now: H08/H09/H10 behavior already existed; the remaining MVP risk was silent drift in visibility and verification-trigger rules.

Verification:
- `pytest -q coding-deepgent/tests/test_tasks.py coding-deepgent/tests/test_subagents.py coding-deepgent/tests/test_todo_domain.py coding-deepgent/tests/test_planning.py`
- `ruff check coding-deepgent/tests/test_tasks.py coding-deepgent/tests/test_todo_domain.py`
- `mypy coding-deepgent/src/coding_deepgent/todo/service.py coding-deepgent/src/coding_deepgent/tasks/store.py coding-deepgent/src/coding_deepgent/tasks/tools.py coding-deepgent/src/coding_deepgent/subagents/tools.py coding-deepgent/tests/test_tasks.py coding-deepgent/tests/test_todo_domain.py`

Boundary findings:
- H08 is complete as session-local planning; it must not absorb durable task graph semantics.
- H09/H10 are complete for MVP without coordinator/mailbox/background runtime.

Decision:
- continue

Reason:
- Stage 25 is complete and Stage 26 (H11 agent-as-tool closeout with minimal H12) remains the next milestone from the canonical dashboard.
