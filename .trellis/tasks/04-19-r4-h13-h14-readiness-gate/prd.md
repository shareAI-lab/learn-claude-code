# R4: H13 H14 Readiness Gate

## Goal

在进入 H13 mailbox / H14 coordinator 前建立硬性 readiness gate，确保 `run_subagent` / `run_fork` 不被污染成 team runtime，并为 future `coordinator` / `worker` role projection、Scratchpad、task notification、SendMessage surfaces 留出明确合同。

## Dependencies

* Depends on R1.
* Prefer after R2 and R3, so readiness gate reflects stabilized runtime surfaces.

## Requirements

* 增加 spec/test gate，禁止 `run_subagent` / `run_fork` 接收 mailbox/coordinator/team lifecycle 字段或语义。
* 定义 future H13/H14 required surfaces，但不实现完整 behavior。
* 明确 coordinator/worker tool projection 的目标边界：
  * Coordinator: orchestration tools only.
  * Worker: execution tools only, no team management tools.
* 明确 H13/H14 进入条件。

## Acceptance Targets

* [ ] Regression tests prove `run_subagent` / `run_fork` schemas remain clean.
* [ ] Trellis backend contracts state H13/H14 readiness criteria.
* [ ] Future coordinator/worker role projection boundary is documented.
* [ ] No H13/H14 behavior is implemented in this task.

## Planned Features

* Update Trellis backend contracts.
* Add tests or review checks around runtime role projection and schema non-contamination.
* Define H13/H14 stage entry checklist.

## Detailed Implementation Plan

### Readiness Criteria To Encode

H13/H14 planning may begin only when these are true:

* Runtime roles can express `coordinator` and `worker` without overloading `subagent` or `fork`.
* Public `run_subagent` and `run_fork` schemas remain free of mailbox/coordinator/team lifecycle fields.
* There is a clear place for future coordinator/worker tool projection that is not prompt-only enforcement.
* Background run service has an explicit boundary for future message delivery.
* A future `teams/` or `orchestration/` domain can own team state and scratchpad without hiding it in `sessions/`, `tool_system/`, or `subagents/tools.py`.

### Required Code/Spec Changes

* Update `.trellis/spec/backend/project-infrastructure-foundation-contracts.md` with runtime reshape completion facts and H13/H14 entry criteria.
* Update `.trellis/spec/backend/task-workflow-contracts.md` if subagent/fork/background contracts changed during R1-R3.
* Add or update tests proving schema non-contamination:
  * `run_subagent` must not expose `background`, `mailbox`, `coordinator`, `team`, `worker`, or similar runtime-creep fields.
  * `run_fork` must not expose mailbox/coordinator/team fields.
  * Background controls must not claim mailbox/coordinator semantics.
* Add role projection readiness tests if R1 introduced role metadata/projection helpers.

### H13/H14 Future Planning Handoff

After R4, the next integrated delivery planning task should define:

* H13 acceptance target: local mailbox + SendMessage + Scratchpad foundation.
* H14 acceptance target: Coordinator mode with restricted orchestration tool projection and worker execution projection.
* Explicit non-goal: no prompt-only fake multi-agent conversation.
* Source references:
  * local claude-code-book Chapter 10.
  * `/root/claude-code-haha/src/tools/SendMessageTool/*`
  * `/root/claude-code-haha/src/tools/shared/spawnMultiAgent.ts`
  * `/root/claude-code-haha/src/utils/swarm/*`

### Focused Verification

* `pytest -q coding-deepgent/tests/subagents/test_subagents.py::test_run_subagent_tool_schema_rejects_runtime_creep_fields`
* `pytest -q coding-deepgent/tests/subagents/test_subagents.py::test_run_fork_tool_schema_rejects_runtime_creep_fields`
* `pytest -q coding-deepgent/tests/tool_system/test_tool_system_registry.py coding-deepgent/tests/tool_system/test_tool_search.py`
* Trellis spec review against changed runtime contracts.

### Checkpoint Requirements

At R4 checkpoint, record:

* Final H13/H14 readiness verdict.
* Exact specs updated.
* Tests proving current surfaces remain clean.
* Whether the next task should be H13 mailbox foundation or an additional runtime cleanup split.

## Planned Extensions

* H13 mailbox + Scratchpad foundation.
* H14 coordinator mode and coordinator-worker workflow.

## Definition of Done

* Focused tests pass.
* Trellis spec updates are source-backed and concise.
* Checkpoint records whether H13 planning can begin.

## Out of Scope

* 不实现 SendMessage。
* 不实现 Scratchpad.
* 不实现 Coordinator mode.
* 不 add prompt-only fake coordinator workflow.
* 不 create team state storage.
* 不 add remote/UDS/bridge addressing.

## Technical Notes

* Parent: `.trellis/tasks/04-19-runtime-architecture-refactor-plan/prd.md`
* Key files likely touched:
  * `.trellis/spec/backend/project-infrastructure-foundation-contracts.md`
  * `.trellis/spec/backend/task-workflow-contracts.md`
  * `coding-deepgent/tests/subagents/test_subagents.py`
  * possibly `coding-deepgent/tests/tool_system/test_tool_system_registry.py`

## Checkpoint: R4

State:
* verifying

Verdict:
* APPROVE

Implemented:
* Added schema regression coverage that forbids mailbox/coordinator/team/Scratchpad fields on `run_subagent` and `run_fork`.
* Added schema readiness coverage that background controls do not claim mailbox/team runtime fields.
* Updated project infrastructure contracts with H13/H14 readiness criteria.
* Updated task workflow contracts to clarify `subagent_send_input` is not `SendMessage` and background snapshots are durable metadata, not process-local handles.

Verification:
* `pytest -q coding-deepgent/tests/subagents/test_subagents.py::test_run_subagent_tool_schema_rejects_runtime_creep_fields coding-deepgent/tests/subagents/test_subagents.py::test_run_fork_tool_schema_rejects_runtime_creep_fields coding-deepgent/tests/subagents/test_subagents.py::test_background_tools_do_not_claim_mailbox_or_team_runtime_schema coding-deepgent/tests/tool_system/test_tool_system_registry.py coding-deepgent/tests/tool_system/test_tool_search.py`
* Result: `17 passed`

Architecture:
* primitive used: schema regression tests plus Trellis executable contracts.
* why no heavier abstraction: R4 is a readiness gate, not the H13/H14 implementation.

Boundary findings:
* H13/H14 can be planned next only as separate mailbox/coordinator surfaces.
* No SendMessage, Scratchpad, Coordinator, team state, or remote addressing behavior was implemented.

Decision:
* continue

Reason:
* Runtime reshape gate is now encoded in tests/specs; final broader focused validation can run.
