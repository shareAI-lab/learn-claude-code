# Stage 17D: Verifier Subagent Execution Boundary

## Goal

Connect the explicit durable plan artifact boundary to the existing bounded verifier subagent surface, so verification can run against a stable plan input without introducing coordinator mode, mailbox, approval UI, or a long-running child-agent runtime.

## Upgraded Function

The workflow system is upgraded from a verification nudge plus retrievable plan artifact to a plan-driven verifier subagent execution boundary.

## Expected Benefit

* Reliability: verification reads a durable plan artifact instead of arbitrary chat prose.
* Maintainability: verifier invocation semantics become a typed product seam rather than an ad hoc prompt convention.
* Testability: verifier behavior can be exercised through deterministic schemas and store-backed inputs before a real child runtime is introduced.

## Out of Scope

* coordinator runtime
* mailbox / SendMessage
* approval UI
* background worker execution
* persistent verifier evidence store
* automatic task mutation after verifier completion

## Requirements

* Extend the subagent tool schema with an explicit verifier plan reference.
* Require `plan_id` when `agent_type="verifier"`.
* Reject verifier execution when the runtime store is unavailable.
* Resolve the durable plan artifact before verifier execution begins.
* Surface plan title, verification criteria, and referenced `task_ids` to verifier execution.
* Keep verifier execution read-only:
  * verifier allowlist still includes `plan_get`
  * verifier allowlist still excludes mutating task / plan / edit tools
* Return a structured verifier result that makes the plan boundary visible to callers.
* Keep the existing main tool surface unchanged except for the stricter verifier invocation contract.

## Acceptance Criteria

* [ ] `run_subagent` rejects `agent_type="verifier"` without `plan_id`.
* [ ] `run_subagent` rejects verifier execution when no task store is configured.
* [ ] verifier execution fails clearly for an unknown plan id.
* [ ] verifier execution receives durable plan content and verification criteria.
* [ ] verifier tool schema exposes `plan_id` and still hides runtime-only fields.
* [ ] verifier allowlist remains read-only and excludes mutating tools.
* [ ] Focused tests, full tests, ruff, and mypy pass.

## cc-haha Alignment

### Expected effect

Aligning this behavior should improve workflow discipline, verifier readiness, and product parity.

The local runtime effect is: a bounded verifier subagent can be invoked using a durable implementation plan and explicit verification criteria, matching cc-haha's verification-agent principle without copying its coordinator or background execution runtime.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Verification agent | built-in verification agent is adversarial and read-only | local verifier must stay bounded and non-mutating | existing `verifier` subagent type + read-only allowlist | partial | Preserve and tighten now |
| Plan boundary | plan file can be passed into verification work | local verifier reads a durable plan artifact | `plan_id` on `run_subagent` verifier path | partial | Implement now |
| Coordinator/background runtime | richer orchestration and approval flow exist upstream | local verifier can execute without heavier workflow runtime | none | defer | Keep out of scope |

## LangChain Architecture

Use:

* strict Pydantic tool schemas
* existing `run_subagent` tool surface
* LangGraph store-backed plan lookup
* small verifier prompt/render helper plus structured result model

Avoid:

* prompt-only verifier plan parsing
* new orchestration layer
* mailbox/coordinator abstractions
* speculative child runtime wrappers

## Technical Approach

* Extend `RunSubagentInput` with optional `plan_id`.
* Add schema validation requiring `plan_id` for `agent_type="verifier"`.
* Add a small verifier request/result seam in `coding_deepgent.subagents`.
* Resolve the durable plan through the existing task store helpers.
* Render a deterministic verifier work item from:
  * user task
  * plan title/content
  * verification criteria
  * referenced task IDs
* Return structured verifier output as JSON from `run_subagent`, while keeping general subagent behavior simple.
* Extend `tests/test_subagents.py` for:
  * schema validation
  * unknown plan/store failures
  * verifier plan execution payload

## Checkpoint: Stage 17D

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Extended `RunSubagentInput` with explicit `plan_id` support for verifier execution.
- Added a strict validator path so verifier execution rejects missing plan references.
- Resolved durable plans inside the verifier subagent path before child execution.
- Added deterministic verifier work-item rendering from:
  - original verifier task
  - plan id/title/content
  - verification criteria
  - referenced task ids
- Added structured verifier result output from `run_subagent` for verifier calls.
- Preserved the existing read-only verifier allowlist and mutation exclusions.
- Updated the executable workflow contract for the verifier execution boundary.
- Added focused verifier subagent tests.

Verification:
- `pytest -q coding-deepgent/tests/test_subagents.py coding-deepgent/tests/test_tasks.py`
- `pytest -q coding-deepgent/tests/test_tool_system_registry.py coding-deepgent/tests/test_tool_system_middleware.py coding-deepgent/tests/test_app.py`
- `pytest -q coding-deepgent/tests`
- `ruff check coding-deepgent/src/coding_deepgent/subagents coding-deepgent/tests/test_subagents.py .trellis/spec/backend/task-workflow-contracts.md`
- `mypy coding-deepgent/src/coding_deepgent/subagents/schemas.py coding-deepgent/src/coding_deepgent/subagents/tools.py coding-deepgent/tests/test_subagents.py`

Boundary findings:
- The smallest safe 17D change is to keep verifier execution on the existing `run_subagent` surface instead of introducing a new coordinator or mailbox abstraction.
- `run_subagent.tool_call_schema()` does not by itself enforce the custom verifier `plan_id` invariant, so the decisive safety check remains on the real execution path.
- Structured verifier output is now limited to verifier calls; general subagent behavior remains unchanged.

Decision:
- continue

Reason:
- Verifier execution now has an explicit durable plan boundary without introducing coordinator/mailbox/UI/runtime expansion.
