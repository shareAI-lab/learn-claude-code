# Stage 17B: Plan Verify Workflow Boundary

## Goal

Add a deterministic verification boundary to durable task workflow before introducing plan-mode tools, coordinator runtime, mailbox, or multi-agent communication.

## Concrete Benefit

* Reliability: completing a non-trivial task graph without verification becomes visible to the model.
* Testability: plan/verify discipline starts as a deterministic task-domain rule.
* Maintainability: TodoWrite remains short-term planning; durable Task owns workflow evidence/readiness boundaries.

## Requirements

* Detect when a 3+ task graph is fully completed without a verification task.
* Surface a verification nudge in `task_update` output when the last task closes such a graph.
* Keep verifier execution out of scope.
* Keep plan-mode tools out of scope.
* Keep mailbox/coordinator out of scope.

## Acceptance Criteria

* [ ] Completing the last task in a 3+ graph without verification exposes a verification nudge.
* [ ] A graph with a verification task does not expose the nudge.
* [ ] Partial/incomplete graphs do not expose the nudge.
* [ ] Existing task APIs remain JSON-parseable as `TaskRecord`.
* [ ] Focused tests, ruff, and mypy pass.

## Out of Scope

* EnterPlanMode / ExitPlanMode tools
* verification subagent execution
* coordinator mode
* mailbox / SendMessage
* task evidence store

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve reliability and product-grade workflow discipline.

The local runtime effect is: durable task completion now nudges verification for non-trivial task graphs, matching cc-haha's principle that verification is independent work, not a summary caveat.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Verification nudge | `TaskUpdateTool` nudges a verification agent after closing 3+ tasks with no verification task | local task graph discourages unverified completion | task_update output metadata | partial | Implement now |
| Verification agent | built-in verification agent is read-only/adversarial | future independent verifier | none now | defer | Already available as bounded subagent type |
| Plan mode | Enter/ExitPlanMode enforce read-only planning and approval | future plan artifact/approval boundary | none now | defer | Out of current scope |

## LangChain Boundary

Use:

* deterministic task-domain helper
* existing `task_update` tool output path
* existing verifier subagent type only as future target

Avoid:

* prompt-only workflow claims
* new plan mode tools
* coordinator/mailbox runtime

## Technical Approach

* Add `task_graph_needs_verification()` helper.
* In `task_update`, when a status update completes a task, add `verification_nudge=true` to the returned JSON metadata if the graph needs verification.
* Add tests in `tests/test_tasks.py`.

## Checkpoint: Stage 17B

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added `task_graph_needs_verification()`.
- `task_update` now surfaces `verification_nudge=true` in returned metadata when completing the last task in a 3+ graph without a verification task.
- Verification nudge is output-only and does not mutate the stored `TaskRecord`.
- Added task workflow executable spec.

Verification:
- `pytest -q tests/test_tasks.py tests/test_tool_system_registry.py tests/test_tool_system_middleware.py tests/test_subagents.py tests/test_app.py tests/test_contract.py tests/test_structure.py`
- `pytest -q`
- `ruff check src/coding_deepgent/tasks/schemas.py src/coding_deepgent/tasks/store.py src/coding_deepgent/tasks/tools.py src/coding_deepgent/tasks/__init__.py tests/test_tasks.py`
- `mypy src/coding_deepgent/tasks/schemas.py src/coding_deepgent/tasks/store.py src/coding_deepgent/tasks/tools.py src/coding_deepgent/tasks/__init__.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/tools/TaskUpdateTool/TaskUpdateTool.ts`
  - `/root/claude-code-haha/src/tools/AgentTool/built-in/verificationAgent.ts`
  - `/root/claude-code-haha/src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts`
- Aligned:
  - non-trivial task graph completion now nudges independent verification.
  - verification remains a separate boundary, not a final-summary caveat.
- Deferred:
  - actual verifier execution
  - EnterPlanMode/ExitPlanMode local tools
  - coordinator/mailbox runtime

LangChain architecture:
- Primitive used:
  - task-domain helper
  - strict task tool schema and output JSON
- Why no heavier abstraction:
  - 17B establishes workflow boundary only; verifier runtime should build on subagent/task foundations later.

Boundary findings:
- New issue handled:
  - durable task graph could be closed without any verification signal.
- Residual risk:
  - verification nudge is currently metadata in task output, not an enforced verifier subagent run.
- Impact on next stage:
  - next work can either add explicit plan artifacts or start verifier execution integration.

Decision:
- continue

Terminal note:
- Stage 17A/17B harden task/workflow foundations enough to switch to a new sub-stage only by explicit product choice.

Reason:
- Tests, ruff, and mypy passed.
- Scope stayed inside task/workflow boundary.
- No mailbox, coordinator runtime, or multi-agent communication was introduced.
