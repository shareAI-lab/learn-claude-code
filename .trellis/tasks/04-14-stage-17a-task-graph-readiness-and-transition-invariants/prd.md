# Stage 17A: Task Graph Readiness and Transition Invariants

## Goal

Harden durable task graph semantics before plan/verify or multi-agent work, keeping TodoWrite separate from durable Task.

## Concrete Benefit

* Reliability: durable tasks cannot reference missing dependencies or create simple cycles.
* Multi-agent readiness: `task_list` can expose which tasks are actually ready to claim.
* Maintainability: task invariants are enforced in the task domain, not prompt prose.

## Requirements

* Reject missing dependencies at task creation.
* Reject self-dependencies.
* Reject dependency cycles on create/update.
* Require a blocker signal when moving a task to `blocked`.
* Add `ready` to task list output.
* Preserve existing task statuses and public tool names.
* Keep TodoWrite separate from durable Task.

## Acceptance Criteria

* [ ] Creating a task with an unknown dependency fails.
* [ ] Creating/updating a self-dependency fails.
* [ ] Creating/updating a cycle fails.
* [ ] Moving to `blocked` without dependency or `blocked_reason` metadata fails.
* [ ] `task_list` renders ready status deterministically.
* [ ] Focused tests, ruff, and mypy pass.

## Out of Scope

* mailbox
* coordinator runtime
* multi-agent communication
* claim/lock semantics
* plan mode tools
* verification subagent workflow

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve reliability, multi-agent readiness, and product parity.

The local runtime effect is: task records become a stricter durable graph instead of a loose list, so later plan/verify and subagent workflows can build on correct readiness semantics.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Task creation | `TaskCreateTool` creates durable task records with subject/description/status and optional metadata | local durable tasks are structured records | existing `TaskRecord` | align | Preserve |
| Dependencies | `TaskUpdateTool` supports `addBlocks` / `addBlockedBy`; `TaskListTool` renders blocked tasks with open blockers | local tasks need dependency readiness semantics | validate dependencies and expose `ready` | partial | Implement now |
| Completion discipline | `TaskUpdateTool` nudges verification after closing many tasks | plan/verify should be explicit later | no verifier now | defer | Stage 17B |
| Mailbox/ownership | cc-haha can notify owners via mailbox | multi-agent coordination | no mailbox now | defer | Out of scope |

## LangChain Boundary

Use:

* strict Pydantic task tool schemas
* LangGraph store-backed task records
* deterministic task domain validation

Avoid:

* TodoWrite persistence
* mailbox/coordinator runtime
* prompt-only validation

## Technical Approach

* Extend `tasks.store` with dependency validation helpers.
* Keep `TaskRecord.depends_on` as the local blocked-by edge.
* Add `ready` to `task_list` output.
* Extend `tests/test_tasks.py`.

## Checkpoint: Stage 17A

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added dependency validation on task creation.
- Added dependency update support through `TaskUpdateInput`, `update_task()`, and `task_update`.
- Rejected:
  - unknown dependencies
  - self-dependencies
  - dependency cycles
- Added `validate_task_graph()`.
- Required a blocker signal before moving a task to `blocked`:
  - existing/new dependency
  - or `metadata["blocked_reason"]`
- Added ready status to `task_list` output via task metadata.

Verification:
- `pytest -q tests/test_tasks.py tests/test_tool_system_registry.py tests/test_tool_system_middleware.py tests/test_subagents.py tests/test_app.py tests/test_contract.py tests/test_structure.py`
- `pytest -q`
- `ruff check src/coding_deepgent/tasks/schemas.py src/coding_deepgent/tasks/store.py src/coding_deepgent/tasks/tools.py src/coding_deepgent/tasks/__init__.py tests/test_tasks.py`
- `mypy src/coding_deepgent/tasks/schemas.py src/coding_deepgent/tasks/store.py src/coding_deepgent/tasks/tools.py src/coding_deepgent/tasks/__init__.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/tools/TaskCreateTool/TaskCreateTool.ts`
  - `/root/claude-code-haha/src/tools/TaskUpdateTool/TaskUpdateTool.ts`
  - `/root/claude-code-haha/src/tools/TaskListTool/TaskListTool.ts`
  - `/root/claude-code-haha/src/tools/TaskGetTool/TaskGetTool.ts`
  - `/root/claude-code-haha/src/Task.ts`
- Aligned:
  - durable tasks remain separate from TodoWrite.
  - task graph readiness and blocked-by semantics are now explicit and testable.
- Deferred:
  - mailbox/owner notifications
  - coordinator runtime
  - task-level evidence store

LangChain architecture:
- Primitive used:
  - strict Pydantic tool schemas
  - LangGraph store-backed task records
  - task-domain validation
- Why no heavier abstraction:
  - 17A only hardens graph invariants; no agent/team lifecycle is needed yet.

Boundary findings:
- New issue handled:
  - tasks could reference missing dependencies or form cycles because dependencies were not validated as a graph.
- Residual risk:
  - `ready` is currently exposed in rendered task metadata rather than as a dedicated public task output schema.
- Impact on next stage:
  - 17B can focus on plan/verify workflow boundary without first fixing task graph correctness.

Decision:
- continue

Reason:
- Tests, ruff, and mypy passed.
- Scope stayed within durable task graph invariants.
- 17B remains valid and does not require mailbox or coordinator runtime.
