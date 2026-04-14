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
