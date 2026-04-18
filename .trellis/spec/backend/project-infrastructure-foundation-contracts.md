# Project Infrastructure Foundation Contracts

> Project-level infrastructure review gate for `coding-deepgent` transcript,
> session, compact, collapse, runtime pressure, task, subagent, hooks, and
> memory changes.

This document captures the 2026-04-16 project infrastructure review. It is not a
bug list. Use it as the reusable contract for deciding whether future cc-aligned
work strengthens the LangChain/LangGraph-native foundation or revives temporary
local mental models.

## Scenario: Infrastructure Foundation Review Gate

### 1. Scope / Trigger

Read this document before changing any of:

- transcript/session JSONL records or resume behavior
- compact transcript records, generated/manual compact, live compact, or collapse
- runtime pressure middleware, projection, token budgets, or prompt-too-long retry
- durable task, plan, verification, or subagent execution boundaries
- hooks, hook evidence, or hook-provided model-visible context
- long-term memory, session memory, memory recall, or memory quality policy
- LangChain/LangGraph runtime wiring, `RuntimeContext`, `RuntimeState`,
  checkpointer, store, or `thread_id`

This gate is also required for cc highlight work touching `H05-H14`,
`H18-H20`, or any future stage that claims to improve long-session continuity,
multi-agent readiness, or cross-session memory.

### 2. Canonical Runtime Surfaces

The current product has these infrastructure surfaces:

```python
class RuntimeContext:
    session_id: str
    workdir: Path
    trusted_workdirs: tuple[Path, ...]
    entrypoint: str
    agent_name: str
    skill_dir: Path
    event_sink: RuntimeEventSink
    hook_registry: LocalHookRegistry
    session_context: SessionContext | None

class RuntimeState(AgentState):
    todos: NotRequired[list[RuntimeTodoState]]
    rounds_since_update: NotRequired[int]
    session_memory: NotRequired[dict[str, Any]]

class SessionContext:
    session_id: str
    workdir: Path
    store_dir: Path
    transcript_path: Path
    entrypoint: str | None = None
```

Current persistent/session record types:

```text
message
state_snapshot
evidence
compact
```

Current LangChain/LangGraph-native entry points:

```python
create_agent(
    model=...,
    tools=...,
    system_prompt=...,
    middleware=...,
    state_schema=RuntimeState,
    context_schema=RuntimeContext,
    checkpointer=...,
    store=...,
    name="coding-deepgent",
)

RuntimePressureMiddleware.wrap_model_call(...)
ToolGuardMiddleware.wrap_tool_call(...)
MemoryContextMiddleware.wrap_model_call(...)
```

Current store-backed collaboration/memory surfaces:

```python
save_memory(type, source, runtime, ...)
list_memory(type=None, limit=20, runtime=...)
delete_memory(type, key, runtime)
memory jobs
memory worker-run-once
task_create(...)
task_update(...)
plan_save(...)
run_subagent(task, runtime, agent_type="<builtin-or-local>", plan_id=...)
```

Long-term memory may also influence runtime behavior through existing guard
surfaces, not only through prompt recall. Current local contract:

- `feedback` memory can block high-risk tool actions through `ToolGuardMiddleware`
- keep this bounded and deterministic; do not add a second hidden query loop
- current enforced local cases are:
  - commit commands when feedback requires lint first
  - dependency edits/install commands when feedback requires confirmation
  - generated-path writes when feedback forbids direct modification

Current product memory surface is intentionally split into two visible layers:

- product-level rules
  - one project-level rules file defines long-term behavior constraints
  - this layer is user-editable
  - this layer is not long-term memory and not transcript history
- long-term memory
  - durable reusable facts, rules, references, and user profile entries
  - save/list/delete through memory tools
  - shown back to the model through bounded recall
  - shown back to the user through recovery brief visibility
- current-session memory
  - the bounded summary/artifact for the active session only
  - shown separately in recovery/resume
  - must not be treated as long-term durable memory

The product-level context and memory model is four-layer:

1. project-level rules
2. long-term memory
3. current-session memory
4. recovery context

Default assembly rule:

- earlier layers define longer-lived behavior or knowledge
- later layers restore current-session and historical context
- later layers must not silently override the prior three by default

Current tool capability protocol:

```text
name
schema
permission
execution
rendering_result
```

Detailed tool contracts live in
[Tool Capability Contracts](./tool-capability-contracts.md).

### 3. Ownership Contracts

#### Transcript And Session

- The JSONL transcript is the append-only factual ledger.
- Persisted transcript records must not be rewritten by live pressure,
  projection, collapse, auto-compact, reactive compact, hooks, or memory recall.
- `LoadedSession.history` is the raw persisted message view.
- `LoadedSession.compacted_history` is a virtual load-time continuation view.
- `LoadedSession.evidence` is bounded operational evidence, not chat history and
  not long-term memory.
- `SessionContext` is the bridge that lets runtime tools append bounded evidence
  to the current ledger.
- `RuntimeState` snapshots are recoverable runtime state, not a replacement for
  the transcript ledger.

#### Compact, Collapse, And Runtime Pressure

- Manual/generated session compact may persist `compact` records.
- Live `snip`, `microcompact`, `context_collapse`, `auto_compact`, and
  `reactive_compact` are model-facing projections only.
- `context_collapse` is a live pressure stage. It must not become a second
  persisted compact ledger.
- Runtime pressure order is:
  1. `snip_messages`
  2. `microcompact_messages`
  3. `maybe_collapse_messages`
  4. `maybe_auto_compact_messages`
  5. model call
  6. one bounded reactive compact retry only for prompt-too-long errors
- Pressure events may become session evidence only through bounded metadata.
  Raw prompt text, raw summaries, full tool output, and arbitrary hook data must
  not be written as evidence metadata.
- Live projection artifacts must preserve tool-call/tool-result pairing and
  persisted-output restoration paths when older context is hidden.

#### Task, Plan, And Subagent

- `TodoWrite` is short-term session state.
- durable `TaskRecord` and `PlanArtifact` are LangGraph-store-backed
  collaboration/workflow state.
- verifier subagents must resolve an explicit `PlanArtifact` before execution.
- verifier evidence persists to the session ledger and must not mutate durable
  tasks or plans.
- current `run_subagent` is a bounded synchronous tool surface. It must not be
  stretched into mailbox, coordinator, background daemon, or team lifecycle
  semantics without a new source-backed contract.

#### Hooks

- Hooks are deterministic local lifecycle seams.
- Hooks may block only at documented runtime/tool boundaries.
- Hook-provided model-visible context must be bounded, whitespace-normalized,
  and routed through the owning context/compact seam.
- Hooks must not call tools, mutate transcript records, or become a hidden
  plugin runtime.

#### Memory

- Long-term memory uses a durable backend distinct from the session ledger.
- PostgreSQL is the current durable source of truth for long-term memory,
  memory versions, extraction jobs, and agent memory scope metadata.
- Redis is allowed as the current queue/lock surface for memory background jobs.
- S3-compatible object storage is allowed for memory snapshot/archive payloads.
- Main agent memory remains global by default.
- Child/fork agent memory may use agent-private scope while still reading
  global long-term memory when appropriate.
- Session memory uses `RuntimeState["session_memory"]` and session
  `state_snapshot` continuity.
- Evidence records are not memory records.
- Recovery briefs are not memory records.
- A feature may claim "cross-session memory" only when it identifies which
  backend survives the relevant boundary:
  - same `agent.invoke` / same process
  - same CLI session resume
  - process restart
  - workspace or machine migration
- The current `StoreBackend` still supports `none` and `memory` for runtime
  store seams such as task/plan state and local testing. It is no longer the
  source of truth for durable long-term memory claims.

### 4. Project-Level Assessment

| Layer | Current judgment | Classification | Follow-up rule |
|---|---|---|---|
| transcript | Append-only JSONL ledger is the right foundation; count-based `message_index` and prefix-derived projection metadata are not enough for rich future timelines. | architecture + spec | Future transcript/projection work must define stable message identity and lineage before adding more projection behavior. |
| session | Resume, evidence, compacts, and state snapshots have coherent ownership. | mostly architecture-correct | Preserve separation between raw history, virtual compacted view, evidence, and runtime state. |
| compact | Manual/generated compact correctly persists records and keeps synthetic artifacts out of raw history. | architecture-correct | Persist only explicit session compact; keep live compact projection-only unless a new contract says otherwise. |
| collapse | Live collapse is useful pressure mitigation but is a temporary projection concept, not a durable session concept. | spec gap risk | Any durable collapse store must first explain why it is not just compact history with different trigger metadata. |
| runtime pressure | Middleware-level staged rewrite is LangChain-native and testable. | architecture-correct | Keep ordering, fail-open behavior, bounded evidence, and prompt-too-long retry tests as mandatory. |
| task | Durable task/plan graph is correctly separate from TodoWrite. | architecture-correct | Do not add workflow semantics to todo state or transcript evidence. |
| subagent | Built-in `general`/`verifier`/`explore`/`plan`, repo-local and plugin-provided child definitions, fork continuity, sidechain-thread resume, and bounded background subagent runs are local slices with read-only tool allowlists and structured result envelopes; they are not a team runtime. | architecture gap for future cc | Mailbox/coordinator/team execution still require new task/subagent specs, not more string payloads in `run_subagent`. |
| hooks | Local sync hooks are a safe foundation. | process/spec gap for extension lifecycle | Keep plugin/async/remote hooks deferred until a concrete lifecycle and trust contract exists. |
| memory | Scoped memory quality gate is good; durable backend depth is not yet sufficient for process-surviving cross-session claims. | architecture gap | Add durable store backend contract before expanding memory extraction or claiming richer cc memory parity. |

### 5. Architecture vs Spec vs Process Findings

#### Architecture Findings

- Stable transcript identity is still the largest foundation gap for future
  timeline, visualization, collapse-store, and projection debugging work.
- Durable memory needs a process-surviving store backend before it can carry the
  full cross-session memory product requirement.
- Subagent infrastructure supports verifier execution, but not yet cc-style
  mailbox, coordinator, lifecycle, cancellation, or background work.
- LangGraph checkpointer/store, JSONL transcript, and `RuntimeState` snapshots
  are separate mechanisms; future work must not blur them into one "session
  state" concept.

#### Spec Findings

- Existing focused specs are strong for individual compact/runtime/task
  scenarios, but they did not previously define a project-level infrastructure
  maturity gate across all core layers.
- Collapse must stay explicitly documented as live projection until a durable
  collapse-store contract exists.
- "Memory durability" must be described by boundary, not by feature name.
- Hook `additional_context` needs an owning model-visible seam for each new use;
  hooks themselves must not become prompt assembly.

#### Process Findings

- Do not close future cc gaps by matching names such as `compact`, `collapse`,
  `task`, `subagent`, or `memory`. Start from expected local effect and source
  evidence, then choose the LangChain-native primitive.
- Do not patch one bug at a time in context infrastructure without checking the
  transcript/session/projection/evidence/memory ownership matrix.
- Keep canonical rules in `.trellis/spec`; keep `coding-deepgent/README.md` and
  `PROJECT_PROGRESS.md` as product summaries only.

### 6. Prevention Mechanisms

Every infrastructure PRD or implementation touching this scope must include:

- `Layer`: one or more of `transcript`, `session`, `compact`, `collapse`,
  `runtime_pressure`, `task`, `subagent`, `hooks`, `memory`.
- `Expected effect`: concrete local benefit, not "closer to cc".
- `Owning record/state`: JSONL record, LangGraph store namespace,
  `RuntimeState` key, `RuntimeContext` field, prompt payload, or middleware
  projection.
- `Durability boundary`: none, live invocation, session resume, process restart,
  workspace migration.
- `Model-visible surface`: tool schema, system message, user message, context
  payload, or no model-visible surface.
- `Mutation rule`: append-only, projection-only, store put/update, state update,
  or read-only.
- `Evidence rule`: what bounded event/evidence is emitted, and which raw data is
  forbidden.
- `LangChain primitive`: tool, middleware, state schema, context schema,
  checkpointer, store, graph node/subgraph, or explicit non-LangChain boundary.

Required review checks:

```bash
rg -n "record_type|message_index|compact|collapse|session_memory|thread_id|checkpointer|store" coding-deepgent/src/coding_deepgent
rg -n "wrap_model_call|wrap_tool_call|create_agent|RuntimeContext|RuntimeState|ToolRuntime" coding-deepgent/src/coding_deepgent
rg -n "additional_context|append_evidence|runtime_event|VERDICT|run_subagent" coding-deepgent/src/coding_deepgent
```

Treat matches as ownership prompts, not automatic failures.

### 7. Validation & Error Matrix

| Change type | Must prove |
|---|---|
| transcript record change | raw history remains append-only; synthetic resume/compact artifacts are not persisted as messages |
| session resume change | recovery brief, compacted history selection, evidence rendering, and state restoration remain distinct |
| manual/generated compact change | one compact record may be appended; message indices for real messages remain contiguous |
| live collapse/auto-compact change | projection changes only the active model call; no transcript rewrite or compact record append occurs |
| runtime pressure threshold/order change | event order, fail-open behavior, and prompt-too-long retry behavior are covered |
| task/plan change | TodoWrite remains separate; task dependencies and plan verification remain validated |
| verifier subagent change | child runtime is read-only, plan-bound, and verifier evidence is bounded |
| hook change | hook block/additional-context behavior is bounded and emitted through existing evidence/event seams |
| memory change | quality gate rejects duplicates/transient state; durability boundary is explicit |

### 8. Good / Base / Bad Cases

#### Good

```python
# Live model-call pressure projection.
processed = maybe_auto_compact_messages(
    request.messages,
    summarizer=request.model,
    threshold_tokens=8000,
    state=request.state,
    hook_context=request.runtime.context,
)
```

Expected:

- model-facing messages may be compacted for this call
- no JSONL transcript record is rewritten
- bounded `auto_compact` evidence may be appended when a `SessionContext` exists

#### Base

```python
store.append_compact(
    session_context,
    trigger="manual",
    summary=summary,
    original_message_count=10,
    summarized_message_count=6,
    kept_message_count=4,
)
```

Expected:

- explicit compact is an append-only transcript event
- raw message history stays available
- load-time compacted history can select the latest valid compact record

#### Bad

```python
# Do not implement durable collapse by deleting old transcript messages.
transcript[:] = collapse_live_messages_with_summary(transcript, summary="...")
```

Expected:

- reject this design; collapse is live projection unless a new durable
  collapse-store contract is approved

### 9. Tests Required

Use focused tests first, then broaden only when coupling changes.

- Transcript/session/compact:
  - `coding-deepgent/tests/test_sessions.py`
  - `coding-deepgent/tests/test_cli.py`
  - `coding-deepgent/tests/test_compact_artifacts.py`
  - `coding-deepgent/tests/test_message_projection.py`
- Runtime pressure/collapse:
  - `coding-deepgent/tests/test_runtime_pressure.py`
  - `coding-deepgent/tests/test_compact_summarizer.py`
  - `coding-deepgent/tests/test_app.py`
- Task/subagent/workflow:
  - `coding-deepgent/tests/test_tasks.py`
  - `coding-deepgent/tests/test_subagents.py`
  - `coding-deepgent/tests/test_tool_system_registry.py`
- Hooks/evidence:
  - `coding-deepgent/tests/test_hooks.py`
  - `coding-deepgent/tests/test_tool_system_middleware.py`
  - `coding-deepgent/tests/test_session_contributions.py`
- Memory:
  - `coding-deepgent/tests/test_memory.py`
  - `coding-deepgent/tests/test_memory_context.py`
  - `coding-deepgent/tests/test_memory_integration.py`

### 10. Wrong vs Correct

#### Wrong

```python
# Ambiguous "session state" bucket.
loaded_session.state["collapse_summary"] = summary
loaded_session.state["task_status"] = "done"
loaded_session.state["memory"] = evidence_text
```

Why wrong:

- collapse projection, durable task state, and long-term memory have different
  owners and durability boundaries
- this makes future resume, verification, and memory extraction impossible to
  reason about

#### Correct

```python
# Use the owning surface for each concern.
store.append_compact(session_context, trigger="manual", summary=summary, ...)
update_task(runtime.store, task_id=task_id, status="completed")
save_memory(
    type="project",
    fact_or_decision=durable_fact,
    why=decision_reason,
    how_to_apply=follow_up_impact,
    runtime=runtime,
)
```

Why correct:

- each mutation goes through the domain that owns validation, persistence, and
  tests
- future cc features can compose the surfaces without reverse-engineering a
  generic state blob

#### Wrong

```python
# "Closer to cc" without a local effect.
run_subagent(task="coordinate the team and keep mailbox state")
```

Why wrong:

- current `run_subagent` is bounded and synchronous
- mailbox/coordinator/team lifecycle is explicitly deferred and needs a new
  task/subagent contract

#### Correct

```text
Expected effect: verifier checks the saved plan with read-only tools and records
bounded evidence in the parent session.
Primitive: `run_subagent(agent_type="verifier", plan_id=...)`.
```

Why correct:

- it states the concrete local effect
- it stays within the existing LangChain-native tool/runtime/evidence boundary
