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
    max_turns: int = 25,
) -> str: ...

def run_fork(
    intent: str,
    runtime: ToolRuntime,
    max_turns: int = 25,
) -> str: ...

class AgentDefinition(BaseModel):
    agent_type: Literal["general", "verifier"]
    description: str
    when_to_use: str
    tool_allowlist: tuple[str, ...]
    disallowed_tools: tuple[str, ...]
    max_turns: int
    model_profile: str | None = None

class SubagentResultEnvelope(BaseModel):
    agent_type: Literal["general", "verifier"]
    content: str
    tool_allowlist: list[str]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_duration_ms: int
    total_tool_use_count: int

class ForkResultEnvelope(BaseModel):
    mode: Literal["fork"]
    content: str
    fork_run_id: str
    parent_thread_id: str
    child_thread_id: str
    rendered_prompt_fingerprint: str
    tool_pool_identity: ToolPoolIdentitySnapshot
    placeholder_layout: ForkPlaceholderLayout
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_duration_ms: int
    total_tool_use_count: int

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
- `run_subagent` must use a built-in `AgentDefinition` catalog for MVP
  `general` and `verifier` agent types.
- Built-in agent definitions must declare `description`, `when_to_use`,
  `tool_allowlist`, `disallowed_tools`, `max_turns`, and optional
  `model_profile`.
- `general.max_turns == 25` and `verifier.max_turns == 5` must come from
  definitions, not hard-coded branches.
- `general` and `verifier` child tool surfaces must remain read-only:
  `read_file`, `glob`, `grep`, `task_get`, `task_list`, and `plan_get`.
- `general` must execute through a real bounded child `create_agent` path rather
  than returning a hard-coded acceptance string.
- `run_subagent` with `agent_type="verifier"` requires `plan_id`.
- Verifier subagent execution requires a configured task store.
- Verifier subagent execution must resolve the durable plan artifact before child execution begins.
- General subagent output must be structured JSON including `agent_type`,
  `content`, `tool_allowlist`, `input_tokens`, `output_tokens`, `total_tokens`,
  `total_duration_ms`, and `total_tool_use_count`.
- `run_fork` is a separate explicit tool surface. It must not be modeled as a
  `general` or `verifier` `AgentDefinition` variant.
- `run_fork` must operate as a same-config sibling branch:
  - use the parent invocation's rendered system prompt directly
  - use the parent invocation's visible main tool projection directly
  - append one thin fixed fork directive carrying only branch intent
- Fork runtime context must preserve a stable rendered prompt fingerprint and a
  stable visible tool-pool identity snapshot.
- Fork tool-pool identity must be stronger than a name-only list. It must be a
  stable ordered model-visible tool snapshot.
- Fork recursion must be blocked by a dedicated guard marker and runtime-entry
  guard before nested fork execution begins.
- Fork result output must be structured JSON including:
  - `mode == "fork"`
  - `content`
  - `fork_run_id`
  - `parent_thread_id`
  - `child_thread_id`
  - `rendered_prompt_fingerprint`
  - `tool_pool_identity`
  - `placeholder_layout`
  - `input_tokens`
  - `output_tokens`
  - `total_tokens`
  - `total_duration_ms`
  - `total_tool_use_count`
- Fork placeholder layout is part of the continuity seam even before full fork
  resume exists. It must define a version and replacement-state hook contract.
- Real child subagent executions with an active parent `SessionContext` must
  append bounded sidechain transcript entries into the parent session ledger
  using the existing transcript-event seam rather than a separate agent
  directory.
- Sidechain transcript entries must carry `subagent_thread_id` plus optional
  `parent_message_id` / `parent_thread_id` linkage when available.
- Verifier subagent output must expose the durable plan boundary as structured JSON including:
  - `plan_id`
  - `plan_title`
  - `verification`
  - `task_ids`
  - `tool_allowlist`
  - `content`
  - `input_tokens`
  - `output_tokens`
  - `total_tokens`
  - `total_duration_ms`
  - `total_tool_use_count`
- Subagent token counts are deterministic local estimates, not provider billing
  or tokenizer truth.
- If the final assistant message lacks direct text, subagent result extraction
  must scan backward for the last non-empty text before failing.
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
| child tool allowlist | `general` and `verifier` include read-only file/task/plan tools and exclude mutating tools |
| general subagent execution | invokes a real child agent with the read-only allowlist |
| recorded child execution | parent session ledger receives sidechain transcript entries with child thread linkage |
| final child assistant message is tool-only | result extraction falls back to the last non-empty assistant text |
| verifier subagent without `plan_id` | Pydantic validation error |
| verifier subagent without runtime store | `RuntimeError("Verifier subagent requires task store")` |
| verifier subagent with missing plan | `KeyError("Unknown plan...")` |
| general subagent output | structured JSON parseable as general result envelope |
| fork output | structured JSON parseable as fork result envelope |
| fork runtime invocation lacks rendered prompt or visible tool projection | explicit runtime error; no fallback reconstruction |
| nested fork attempts | explicit recursion guard failure before child execution |
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
    verification="Run pytest coding-deepgent/tests/test_tasks.py",
    task_ids=[task.id],
)
```

Expected:
- plan has stable id
- verification criteria are non-empty
- referenced task IDs exist

### 6. Tests Required

- `coding-deepgent/tests/test_tasks.py::test_task_store_transitions_dependencies_and_ready_rule`
- `coding-deepgent/tests/test_tasks.py::test_task_graph_rejects_missing_self_and_cycle_dependencies`
- `coding-deepgent/tests/test_tasks.py::test_task_update_requires_blocked_reason_or_dependency`
- `coding-deepgent/tests/test_tasks.py::test_task_graph_needs_verification_after_closing_three_tasks`
- `coding-deepgent/tests/test_tasks.py::test_task_graph_with_verification_task_does_not_need_nudge`
- `coding-deepgent/tests/test_tasks.py::test_task_update_tool_marks_verification_nudge_in_output_metadata`
- `coding-deepgent/tests/test_tasks.py::test_plan_artifact_roundtrip_requires_verification_and_known_tasks`
- `coding-deepgent/tests/test_tasks.py::test_plan_tools_save_and_get_artifacts`
- `coding-deepgent/tests/test_tool_system_registry.py::test_main_projection_preserves_current_product_tool_surface`
- `coding-deepgent/tests/test_subagents.py::test_subagent_allowlists_are_exact_and_exclude_mutating_tools`
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_task_general_executes_real_read_only_child_agent`
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_tool_returns_structured_general_result`
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_records_sidechain_messages_in_parent_session`
- `coding-deepgent/tests/test_subagents.py::test_subagent_result_falls_back_to_last_text_when_final_message_is_tool_only`
- `coding-deepgent/tests/test_subagents.py::test_run_fork_tool_schema_rejects_runtime_creep_fields`
- `coding-deepgent/tests/test_subagents.py::test_run_fork_task_executes_same_config_sibling_branch`
- `coding-deepgent/tests/test_subagents.py::test_run_fork_tool_returns_structured_result`
- `coding-deepgent/tests/test_subagents.py::test_run_fork_records_sidechain_messages_with_contract_metadata`
- `coding-deepgent/tests/test_subagents.py::test_run_fork_rejects_recursive_fork_marker`
- `coding-deepgent/tests/test_subagents.py::test_verifier_subagent_requires_plan_id`
- `coding-deepgent/tests/test_subagents.py::test_verifier_subagent_requires_task_store`
- `coding-deepgent/tests/test_subagents.py::test_verifier_subagent_rejects_unknown_plan`
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_task_verifier_uses_durable_plan_payload`
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_tool_returns_structured_verifier_result`
- `coding-deepgent/tests/test_subagents.py::test_verifier_verdict_helpers_map_status_and_summary`
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_tool_persists_verifier_evidence_roundtrip`
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_tool_skips_verifier_evidence_without_recording_context`

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
