# Task Workflow Contracts

> Executable contracts for durable task graph and plan/verify workflow boundaries.

## Scenario: Durable Task Graph

### 1. Scope / Trigger

- Trigger: changes touching `coding_deepgent.tasks`, task tools, task graph transitions, or workflow verification behavior.
- TodoWrite remains short-term state. Durable Task is store-backed collaboration/workflow state.

### 2. Signatures

```python
def create_task(
    store: TaskStore,
    *,
    title: str,
    description: str = "",
    depends_on: list[str] | None = None,
    owner: str | None = None,
    metadata: dict[str, str] | None = None,
) -> TaskRecord: ...

def update_task(
    store: TaskStore,
    *,
    task_id: str,
    status: TaskStatus | None = None,
    depends_on: list[str] | None = None,
    owner: str | None = None,
    metadata: dict[str, str] | None = None,
) -> TaskRecord: ...

def is_task_ready(store: TaskStore, record: TaskRecord) -> bool: ...
def validate_task_graph(store: TaskStore) -> None: ...
def task_graph_needs_verification(store: TaskStore) -> bool: ...

def create_plan(
    store: TaskStore,
    *,
    title: str,
    content: str,
    verification: str,
    task_ids: list[str] | None = None,
    metadata: dict[str, str] | None = None,
) -> PlanArtifact: ...

def get_plan(store: TaskStore, plan_id: str) -> PlanArtifact: ...

def run_subagent(
    task: str,
    runtime: ToolRuntime,
    agent_type: Literal["general", "verifier"] = "general",
    plan_id: str | None = None,
    max_turns: int = 1,
) -> str: ...

def record_verifier_evidence(
    *,
    result: SubagentResult,
    runtime: ToolRuntime,
) -> bool: ...
```

### 3. Contracts

- `TaskRecord.depends_on` is the local blocked-by edge.
- Creating or updating dependencies must reject:
  - unknown task IDs
  - self-dependency
  - dependency cycles
- `is_task_ready()` is true only when:
  - task status is `pending`
  - every dependency is `completed`
- Moving a task to `blocked` requires either:
  - at least one dependency
  - or `metadata["blocked_reason"]`
- `task_list` must expose ready state in rendered JSON metadata as `"ready": "true"` or `"false"`.
- Completing a 3+ non-cancelled task graph without a verification task must expose a `verification_nudge` in the returned `task_update` JSON metadata.
- Verification nudge is output metadata only; it must not mutate the stored task record.
- `PlanArtifact` is the durable plan boundary for implementation workflow.
- `PlanArtifact.verification` is required and must be non-empty.
- `PlanArtifact.task_ids` must reference existing durable tasks.
- Plan artifacts use a separate store namespace from task records.
- `plan_save` and `plan_get` are main-surface tools, but they do not enter TodoWrite state.
- `plan_get` is allowed for verifier subagents.
- `plan_save` is forbidden for verifier subagents.
- `run_subagent` with `agent_type="verifier"` requires `plan_id`.
- Verifier subagent execution requires a configured task store.
- Verifier subagent execution must resolve the durable plan artifact before child execution begins.
- Verifier subagent output must expose the durable plan boundary as structured JSON including:
  - `plan_id`
  - `plan_title`
  - `verification`
  - `task_ids`
  - `tool_allowlist`
  - `content`
- Verifier subagent content that includes `VERDICT: PASS|FAIL|PARTIAL` must append
  one existing session evidence record when `runtime.context.session_context` is
  available.
- Verifier evidence must use:
  - `kind="verification"`
  - status mapped as `PASS -> passed`, `FAIL -> failed`, `PARTIAL -> partial`
  - `subject=<plan_id>`
  - metadata containing at least `plan_id` and `verdict`
  - bounded lineage metadata when runtime context is available:
    `parent_session_id`, `parent_thread_id`, `child_thread_id`, and
    `verifier_agent_name`
- Verifier evidence persistence is bounded to the synchronous `run_subagent`
  verifier tool call.
- Verifier evidence persistence must not mutate durable tasks or plan artifacts.
- Verifier calls without `runtime.context.session_context` skip evidence
  persistence explicitly and still preserve the verifier JSON result contract.

### 4. Validation & Error Matrix

| Case | Expected behavior |
|---|---|
| create task with missing dependency | `ValueError("Unknown task dependencies...")` |
| update task to depend on itself | `ValueError("cannot depend on itself")` |
| update task to create a cycle | `ValueError("cycle")` |
| mark blocked without dependency or reason | `ValueError("blocked tasks require...")` |
| pending task with completed dependencies | `is_task_ready(...) is True` |
| completed/cancelled/in_progress task | `is_task_ready(...) is False` |
| 3 completed non-verification tasks | `task_graph_needs_verification(...) is True` |
| graph includes verification task | `task_graph_needs_verification(...) is False` |
| `task_update` closes 3rd non-verification task | output metadata includes `verification_nudge=true` |
| save plan with missing verification | Pydantic validation error |
| save plan with unknown task id | `ValueError("Unknown task dependencies...")` |
| get missing plan | `KeyError("Unknown plan...")` |
| verifier child tool allowlist | includes `plan_get`, excludes `plan_save` |
| verifier subagent without `plan_id` | Pydantic validation error |
| verifier subagent without runtime store | `RuntimeError("Verifier subagent requires task store")` |
| verifier subagent with missing plan | `KeyError("Unknown plan...")` |
| verifier subagent output | structured JSON parseable as verifier result |
| verifier output with `VERDICT: PASS` and session context | one `verification` evidence record with `status == "passed"` |
| verifier output with `VERDICT: FAIL` and session context | one `verification` evidence record with `status == "failed"` |
| verifier output with `VERDICT: PARTIAL` and session context | one `verification` evidence record with `status == "partial"` |
| persisted verifier evidence has runtime context | metadata includes parent and child verifier lineage fields |
| verifier output without session context | verifier JSON result is returned and no evidence persistence is attempted |

### 5. Good / Base / Bad Cases

#### Good

```python
parent = create_task(store, title="Implement feature")
child = create_task(store, title="Run verification", depends_on=[parent.id])
update_task(store, task_id=parent.id, status="in_progress")
update_task(store, task_id=parent.id, status="completed")
assert is_task_ready(store, get_task(store, child.id)) is True
```

#### Base

```python
task = create_task(store, title="Investigate failure")
update_task(
    store,
    task_id=task.id,
    status="blocked",
    metadata={"blocked_reason": "Need logs"},
)
```

#### Bad

```python
update_task(store, task_id=task.id, depends_on=[task.id])
```

Expected: reject self-dependency.

#### Plan Artifact

```python
task = create_task(store, title="Implement feature")
plan = create_plan(
    store,
    title="Feature plan",
    content="Use the existing task store and tests.",
    verification="Run pytest tests/test_tasks.py",
    task_ids=[task.id],
)
```

Expected:
- plan has stable id
- verification criteria are non-empty
- referenced task IDs exist

### 6. Tests Required

- `tests/test_tasks.py::test_task_store_transitions_dependencies_and_ready_rule`
- `tests/test_tasks.py::test_task_graph_rejects_missing_self_and_cycle_dependencies`
- `tests/test_tasks.py::test_task_update_requires_blocked_reason_or_dependency`
- `tests/test_tasks.py::test_task_graph_needs_verification_after_closing_three_tasks`
- `tests/test_tasks.py::test_task_graph_with_verification_task_does_not_need_nudge`
- `tests/test_tasks.py::test_task_update_tool_marks_verification_nudge_in_output_metadata`
- `tests/test_tasks.py::test_plan_artifact_roundtrip_requires_verification_and_known_tasks`
- `tests/test_tasks.py::test_plan_tools_save_and_get_artifacts`
- `tests/test_tool_system_registry.py::test_main_projection_preserves_current_product_tool_surface`
- `tests/test_subagents.py::test_subagent_allowlists_are_exact_and_exclude_mutating_tools`
- `tests/test_subagents.py::test_verifier_subagent_requires_plan_id`
- `tests/test_subagents.py::test_verifier_subagent_requires_task_store`
- `tests/test_subagents.py::test_verifier_subagent_rejects_unknown_plan`
- `tests/test_subagents.py::test_run_subagent_task_verifier_uses_durable_plan_payload`
- `tests/test_subagents.py::test_run_subagent_tool_returns_structured_verifier_result`
- `tests/test_subagents.py::test_verifier_verdict_helpers_map_status_and_summary`
- `tests/test_subagents.py::test_run_subagent_tool_persists_verifier_evidence_roundtrip`
- `tests/test_subagents.py::test_run_subagent_tool_skips_verifier_evidence_without_recording_context`

### 7. Wrong vs Correct

#### Wrong

```python
TaskRecord(title="Child", depends_on=["maybe-existing"])
```

Why wrong:
- Durable task dependencies must reference existing task IDs.
- Loose dependencies break readiness and future multi-agent work.

#### Correct

```python
parent = create_task(store, title="Parent")
child = create_task(store, title="Child", depends_on=[parent.id])
```

Why correct:
- Dependency is validated at creation.
- Readiness can be computed deterministically.
