# Stage 17C: Explicit Plan Artifact Boundary

## Goal

Add a durable explicit plan artifact boundary that can serve as stable input for later verification workflows, without adding plan-mode UI, coordinator runtime, mailbox, or multi-agent communication.

## Upgraded Function

The workflow system is upgraded from task completion nudges to a store-backed implementation plan artifact.

## Expected Benefit

* Recoverability: plans can be saved and retrieved outside chat history.
* Testability: verification criteria become required structured data.
* Maintainability: future verifier subagents can consume a stable artifact instead of parsing arbitrary prose.

## Out of Scope

* EnterPlanMode / ExitPlanMode tools
* approval UI
* coordinator runtime
* mailbox / SendMessage
* verifier subagent execution

## Requirements

* Add `PlanArtifact`.
* Add `plan_save` and `plan_get`.
* Require non-empty verification criteria.
* Validate referenced `task_ids` exist.
* Store plans in a namespace separate from tasks.
* Register plan tools in the main tool surface and capability registry.

## Acceptance Criteria

* [ ] Plan artifacts roundtrip through store.
* [ ] Plan artifacts reject missing verification criteria.
* [ ] Plan artifacts reject unknown task IDs.
* [ ] `plan_save` / `plan_get` are exposed as main tools.
* [ ] Existing task tools still pass.
* [ ] Focused tests, full tests, ruff, and mypy pass.

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve workflow discipline, testability, and future verifier readiness.

The local runtime effect is: implementation plans become explicit artifacts with verification criteria, matching cc-haha's plan-file / ExitPlanMode principle without copying its UI or approval runtime.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Plan file | `plans.ts`, plan-mode attachments, and `ExitPlanModeV2Tool` use a persisted plan file as workflow artifact | local workflow has a stable plan artifact | `PlanArtifact` | partial | Implement store-backed artifact now |
| Verification criteria | plan instructions require a verification section | plan artifact must define how to verify | required `verification` field | align | Implement now |
| Approval UI | ExitPlanMode asks/coordinates approval | user approval flow | none | defer | Out of scope |

## LangChain Architecture

Use:

* strict Pydantic schemas
* LangGraph store namespace
* normal LangChain tools

Avoid:

* prompt-only plan parsing
* UI approval
* coordinator/mailbox runtime

## Checkpoint: Stage 17C

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added `PlanArtifact`, `PlanSaveInput`, and `PlanGetInput`.
- Added plan store helpers:
  - `PLAN_ROOT_NAMESPACE`
  - `plan_namespace()`
  - `create_plan()`
  - `get_plan()`
- Added model-visible tools:
  - `plan_save`
  - `plan_get`
- Registered plan tools in `ToolSystemContainer`.
- Added plan capabilities to `tool_system.capabilities`.
- Added `plan_get` to verifier subagent allowlist and kept `plan_save` forbidden.
- Updated task workflow executable spec.

Verification:
- `pytest -q tests/test_tasks.py tests/test_tool_system_registry.py tests/test_tool_system_middleware.py tests/test_app.py tests/test_subagents.py`
- `pytest -q`
- `ruff check src/coding_deepgent/tasks/schemas.py src/coding_deepgent/tasks/store.py src/coding_deepgent/tasks/tools.py src/coding_deepgent/tasks/__init__.py src/coding_deepgent/containers/tool_system.py src/coding_deepgent/tool_system/capabilities.py tests/test_tasks.py tests/test_tool_system_registry.py tests/test_tool_system_middleware.py tests/test_app.py`
- `mypy src/coding_deepgent/tasks/schemas.py src/coding_deepgent/tasks/store.py src/coding_deepgent/tasks/tools.py src/coding_deepgent/tasks/__init__.py src/coding_deepgent/containers/tool_system.py src/coding_deepgent/tool_system/capabilities.py`

cc-haha alignment:
- Source files inspected:
  - `/root/claude-code-haha/src/utils/plans.ts`
  - `/root/claude-code-haha/src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts`
  - `/root/claude-code-haha/src/utils/attachments.ts`
  - `/root/claude-code-haha/src/utils/messages.ts`
- Aligned:
  - plan artifact is now explicit and requires verification.
- Deferred:
  - plan-mode UI
  - approval flow
  - coordinator/mailbox runtime

LangChain architecture:
- Primitive used:
  - LangChain tools + Pydantic schemas
  - LangGraph store
- Why no heavier abstraction:
  - 17C only establishes the artifact boundary; runtime approval and verifier execution are separate stages.

Boundary findings:
- New issue handled:
  - storing plans under the task namespace caused `list_tasks()` to read plan artifacts as tasks because LangGraph store search is prefix-like. Plan artifacts now use a separate `coding_deepgent_plans` root namespace.
- Residual risk:
- plan artifacts are saved/retrieved but not yet consumed by verifier execution.

Decision:
- continue

Reason:
- Tests, ruff, and mypy passed.
- Scope stayed non-UI and LangChain-native.
- No coordinator, mailbox, or multi-agent communication was introduced.
