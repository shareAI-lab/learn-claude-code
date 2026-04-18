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
    agent_type: str = "general",
    plan_id: str | None = None,
    max_turns: int = 25,
) -> str: ...

def run_fork(
    intent: str,
    runtime: ToolRuntime,
    background: bool = False,
    max_turns: int = 25,
) -> str: ...

def run_subagent_background(
    task: str,
    runtime: ToolRuntime,
    agent_type: str = "general",
    plan_id: str | None = None,
    max_turns: int = 25,
) -> str: ...

def subagent_status(
    run_id: str,
    runtime: ToolRuntime,
) -> str: ...

def subagent_send_input(
    run_id: str,
    message: str,
    runtime: ToolRuntime,
) -> str: ...

def subagent_stop(
    run_id: str,
    runtime: ToolRuntime,
) -> str: ...

def resume_subagent(
    subagent_thread_id: str,
    runtime: ToolRuntime,
    follow_up: str | None = None,
) -> str: ...

def resume_fork(
    child_thread_id: str,
    runtime: ToolRuntime,
    follow_up: str | None = None,
) -> str: ...

class AgentDefinition(BaseModel):
    agent_type: str
    description: str
    when_to_use: str
    instructions: str | None = None
    tool_allowlist: tuple[str, ...]
    disallowed_tools: tuple[str, ...]
    max_turns: int
    model_profile: str | None = None

class SubagentResultEnvelope(BaseModel):
    agent_type: str
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

class BackgroundSubagentRun(BaseModel):
    run_id: str
    mode: Literal["background_subagent", "background_fork"]
    agent_type: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    title: str
    parent_thread_id: str
    child_thread_id: str
    workdir: str
    requested_max_turns: int | None = None
    effective_max_turns: int
    model_profile: str | None = None
    plan_id: str | None = None
    pending_inputs: list[str]
    progress_summary: str
    summary_text: str | None = None
    recent_activities: list[str]
    latest_result: str | None = None
    error: str | None = None
    stop_requested: bool
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_duration_ms: int
    total_tool_use_count: int
    total_invocations: int
    notified: bool

def record_verifier_evidence(
    *,
    result: SubagentResult,
    runtime: ToolRuntime,
) -> bool: ...

def resume_subagent_task(
    *,
    subagent_thread_id: str,
    runtime: ToolRuntime,
    follow_up: str | None = None,
) -> SubagentResult: ...

def resume_fork_task(
    *,
    child_thread_id: str,
    runtime: ToolRuntime,
    follow_up: str | None = None,
) -> ForkResult: ...
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
- `run_subagent` and `run_fork` remain on the initial main tool surface.
- Advanced subagent lifecycle controls:
  `run_subagent_background`, `subagent_status`, `subagent_send_input`,
  `subagent_stop`, `resume_subagent`, and `resume_fork`
  are public local tools, but they live on the deferred-discovery surface and
  should be reached through `ToolSearch` plus `invoke_deferred_tool`.
- `run_subagent` must expose a built-in `AgentDefinition` catalog that includes
  `general`, `verifier`, `explore`, and `plan`.
- Repo-local custom subagent definitions may extend the catalog from
  `.coding-deepgent/SUBAGENTS.json`.
- Local plugins may extend the catalog by declaring `agents` in `plugin.json`
  and providing matching definitions in `<plugin-root>/subagents.json`.
- Built-in agent definitions must declare `description`, `when_to_use`,
  `instructions`, `tool_allowlist`, `disallowed_tools`, `max_turns`, and
  optional `model_profile`.
- `general.max_turns == 25` and `verifier.max_turns == 5` must come from
  definitions, not hard-coded branches; `explore` and `plan` must also declare
  their own non-default ceilings.
- `general`, `verifier`, `explore`, and `plan` child tool surfaces must remain
  read-only:
  `read_file`, `glob`, `grep`, `task_get`, `task_list`, and `plan_get`.
- `explore` may narrow to read-only file tools only.
- Built-in and repo-local custom child agents must execute through a real bounded
  child `create_agent` path rather than returning a hard-coded acceptance
  string.
- `run_subagent` with `agent_type="verifier"` requires `plan_id`.
- Verifier subagent execution requires a configured task store.
- Verifier subagent execution must resolve the durable plan artifact before child execution begins.
- `run_subagent(max_turns=...)` and `run_fork(max_turns=...)` must forward the
  effective turn ceiling into the child/fork runtime instead of silently
  ignoring it.
- `AgentDefinition.model_profile` must affect child model selection when set.
- `run_subagent_background(...)` must persist a bounded background run record in
  the runtime store and return immediately with a stable `run_id`.
- Background subagent runs must expose at least `status`,
  `progress_summary`, `recent_activities`, `pending_inputs`,
  `latest_result`, and bounded cumulative usage counters.
- Background fork runs may reuse the same background run record shape with
  `mode == "background_fork"` and continue on the same fork child thread.
- `subagent_send_input(...)` must queue follow-up input for an existing
  background run and preserve the same `run_id`.
- Background runs may continue through repeated queued inputs, but they must not
  claim mailbox/coordinator/team-runtime semantics.
- `subagent_stop(...)` must request stop for queued or active background runs
  and persist terminal `cancelled` once the current invoke boundary is safe to
  stop.
- Finished background workers must release in-memory worker handles after the
  terminal status is persisted.
- Background run completion or failure must append one bounded
  `subagent_notification` evidence record when recording context exists.
- General subagent output must be structured JSON including `agent_type`,
  `content`, `tool_allowlist`, `input_tokens`, `output_tokens`, `total_tokens`,
  `total_duration_ms`, and `total_tool_use_count`.
- `run_fork` is a separate explicit tool surface. It must not be modeled as a
  `general` or `verifier` `AgentDefinition` variant.
- `run_fork(background=True)` may enter the shared background-run manager, but
  it still counts as the same explicit fork surface rather than a second fork
  entrypoint.
- `run_fork` must operate as a same-config sibling branch:
  - use the parent invocation's rendered system prompt directly
  - use the parent invocation's visible main tool projection directly
  - append one thin fixed fork directive carrying only branch intent
- Fork runtime context must preserve a stable rendered prompt fingerprint and a
  stable visible tool-pool identity snapshot.
- Fork tool-pool identity must be stronger than a name-only list. It must be a
  stable ordered model-visible tool snapshot.
- Fork payload assembly must drop incomplete assistant tool-call turns that lack
  paired tool results instead of inheriting an invalid prefix.
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
  resume exists. It must define a version, replacement-state hook contract, and
  deterministic placeholder messages for paired tool results.
- Real child subagent executions with an active parent `SessionContext` must
  append bounded sidechain transcript entries into the parent session ledger
  using the existing transcript-event seam rather than a separate agent
  directory.
- Sidechain transcript entries must carry `subagent_thread_id` plus optional
  `parent_message_id` / `parent_thread_id` linkage when available.
- Sidechain child transcript entries may persist bounded structured metadata
  needed for subagent/fork resume, such as tool-call ids, content blocks,
  prompt/tool fingerprints, and effective execution ceilings.
- `resume_subagent_task(...)` must reconstruct a child thread from recorded
  sidechain transcript + metadata and continue on the same child thread id.
- `resume_subagent(...)` must return the same structured JSON envelope shape as
  the synchronous general `run_subagent(...)` tool surface.
- `resume_fork_task(...)` must reconstruct a fork child thread from recorded
  sidechain transcript + metadata, and must fail if the current rendered prompt
  fingerprint or visible tool projection fingerprint no longer matches the
  recorded fork contract.
- `resume_fork(...)` must return the same structured JSON envelope shape as the
  explicit `run_fork(...)` tool surface.
- Subagent and fork resume must also fail when the current runtime workdir no
  longer matches the recorded workdir stored in sidechain metadata.
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
| child tool allowlist | built-in child agents keep read-only tool surfaces and exclude mutating tools |
| general subagent execution | invokes a real child agent with the read-only allowlist |
| recorded child execution | parent session ledger receives sidechain transcript entries with child thread linkage |
| custom local subagent definition | repo-local definition is loaded and validated before execution |
| plugin subagent definition | plugin-declared definition is loaded and validated before execution |
| final child assistant message is tool-only | result extraction falls back to the last non-empty assistant text |
| verifier subagent without `plan_id` | Pydantic validation error |
| verifier subagent without runtime store | `RuntimeError("Verifier subagent requires task store")` |
| verifier subagent with missing plan | `KeyError("Unknown plan...")` |
| general subagent output | structured JSON parseable as general result envelope |
| fork output | structured JSON parseable as fork result envelope |
| background subagent start | structured JSON parseable as background run record with stable `run_id` |
| background fork start through `run_fork(background=true)` | structured JSON parseable as background run record with `mode == "background_fork"` |
| background run status lookup | returns the persisted background run record |
| background run follow-up input | queues input and preserves the same background `run_id` |
| background run stop | records stop request and eventually reaches terminal `cancelled` |
| fork runtime invocation lacks rendered prompt or visible tool projection | explicit runtime error; no fallback reconstruction |
| fork prefix contains incomplete tool call without paired result | fork payload drops that incomplete assistant tool-call turn |
| nested fork attempts | explicit recursion guard failure before child execution |
| background run with missing store | explicit runtime error |
| background run completion with recording context | one `subagent_notification` evidence record is appended |
| subagent resume with unknown thread id | explicit runtime error |
| subagent resume with mismatched workdir | explicit runtime error |
| fork resume with mismatched prompt/tool fingerprint | explicit runtime error |
| fork resume with mismatched workdir | explicit runtime error |
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
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_task_passes_effective_max_turns_via_recursion_limit`
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_task_routes_custom_model_profile`
- `coding-deepgent/tests/test_subagents.py::test_resolve_agent_definition_loads_repo_local_custom_agents`
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_executes_repo_local_custom_agent`
- `coding-deepgent/tests/test_subagents.py::test_resolve_agent_definition_loads_plugin_provided_agents`
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_tool_returns_structured_general_result`
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_records_sidechain_messages_in_parent_session`
- `coding-deepgent/tests/test_subagents.py::test_subagent_result_falls_back_to_last_text_when_final_message_is_tool_only`
- `coding-deepgent/tests/test_subagents.py::test_run_fork_tool_schema_rejects_runtime_creep_fields`
- `coding-deepgent/tests/test_subagents.py::test_run_fork_task_executes_same_config_sibling_branch`
- `coding-deepgent/tests/test_subagents.py::test_run_fork_filters_incomplete_tool_calls_and_exposes_placeholder_messages`
- `coding-deepgent/tests/test_subagents.py::test_run_fork_tool_returns_structured_result`
- `coding-deepgent/tests/test_subagents.py::test_run_fork_records_sidechain_messages_with_contract_metadata`
- `coding-deepgent/tests/test_subagents.py::test_run_fork_rejects_recursive_fork_marker`
- `coding-deepgent/tests/test_subagents.py::test_resume_subagent_task_reuses_recorded_thread`
- `coding-deepgent/tests/test_subagents.py::test_resume_fork_task_reuses_recorded_thread`
- `coding-deepgent/tests/test_subagents.py::test_resume_subagent_tool_returns_structured_result`
- `coding-deepgent/tests/test_subagents.py::test_resume_fork_tool_returns_structured_result`
- `coding-deepgent/tests/test_subagents.py::test_resume_fork_task_requires_matching_prompt_fingerprint`
- `coding-deepgent/tests/test_subagents.py::test_run_subagent_background_and_status`
- `coding-deepgent/tests/test_subagents.py::test_run_fork_background_and_status`
- `coding-deepgent/tests/test_subagents.py::test_background_subagent_send_input_reactivates_finished_run`
- `coding-deepgent/tests/test_subagents.py::test_subagent_stop_cancels_running_background_run`
- `coding-deepgent/tests/test_subagents.py::test_resume_subagent_task_requires_matching_workdir`
- `coding-deepgent/tests/test_subagents.py::test_resume_fork_task_requires_matching_workdir`
- `coding-deepgent/tests/test_tool_search.py::test_tool_search_returns_deferred_builtin_subagent_controls`
- `coding-deepgent/tests/test_plugins.py::test_app_container_validates_plugin_provided_subagent_definitions`
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
