# s16: Workflow Runtime — The Model Decides Each Step; a Script Decides the Orchestration

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s14 → [s15](../s15_integrated_harness/) → `s16` → [s17](../s17_goal_loop/)

> *"One tool_use runs an entire orchestration"* — The `Workflow` tool starts a recoverable script runtime that coordinates many agent calls.
>
> **Harness layer**: Orchestration — run saved multi-agent scripts above the single-agent loop.

---

From s01 through s15, the model decides which tools to call in each round. Their results enter `messages[]`, and the model decides the next step from the updated context. This works well when the path depends on what the previous step discovers.

Some tasks repeat a fixed sequence. A code review may inspect several dimensions concurrently, verify each finding, combine duplicates, and sort the result. The sequence and dependencies are known before execution. Here the host needs three things:

- **Parallelism**, rather than waiting for one item at a time;
- **A stable result structure**, even when individual agent answers vary;
- **Recoverability**, so an interruption does not rerun work that is already complete.

If this orchestration exists only in conversation history, its ordering and checkpoints also exist only in that history. A saved workflow puts the fixed sequence in code and records completed calls in a journal.

## Put the Plan in Code, Not in a Sequence of Chat Turns

Add a `Workflow` tool to the harness tool pool. The host registers trusted scripts built from `agent()`, `parallel()`, `pipeline()`, and `phase()`. The model supplies only a saved workflow name, arguments, and an optional run ID to resume; it does not send executable code or metadata.

The workflow enters the main loop as one `tool_use`. As the script runs, the runtime emits lifecycle and progress events and records every step in a journal on disk. When the script finishes, the call returns the launch envelope, result, and task state. Intermediate script results live in variables instead of taking space in conversation history. When restarted with `resume_from_run_id`, unchanged `agent()` calls hit the journal cache and reuse previous results.

![Workflow Runtime Overview](images/workflow-runtime-overview.svg)

```python
SAMPLE_META = {"name": "review-changes", "description": "Review code changes", "phases": ["Review", "Verify"]}

async def sample_workflow(ctx, args):
    ctx.phase("Review")
    results = await ctx.pipeline(DIMENSIONS, audit, verify)   # Each dimension independently runs audit → verify
    confirmed = [f for r in results if r for f in r["confirmed"]]
    ctx.log(f"Confirmed {len(confirmed)} real issues")
    return {"confirmed": confirmed}
```

## The Workflow Tool: One Call, One Complete Run

`Workflow` is added to the s15 host's existing tool pool. The user can request a saved workflow, or the model can select it when a task matches a known orchestration. The adapter resolves the name through the host-owned `WORKFLOWS` registry, then passes its trusted metadata and function to the runtime. The other s15 tools remain available in the same loop.

The model-facing schema accepts `name`, `args`, and `resume_from_run_id`. Unknown names and malformed arguments become an error tool result instead of ending the host loop. The runtime then validates the registered metadata, checks permissions, registers a local workflow task, and emits `async_launched` before running the script. Progress events follow, then the final `task_notification`; the call returns JSON-safe launch information, result, and task state.

```python
WORKFLOW_TOOL = {
    "name": "Workflow",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "args": {"type": "object"},
            "resume_from_run_id": {"type": "string"},
        },
        "required": ["name"],
        "additionalProperties": False,
    },
}

async def run_workflow(name, args=None, resume_from_run_id=None):
    meta, script_fn = WORKFLOWS[name]
    out = await WorkflowTool().call(
        meta, script_fn,
        args=args,
        resume_from_run_id=resume_from_run_id,
    )
    return {"launched": out["launched"], "result": out["result"],
            "task": serialize_task(out["task"])}
```

## Workflow Metadata: Validate Before Launch

Each saved workflow registers trusted metadata with `name`, `description`, and optional `phases`. The runtime validates it before executing workflow code. `name` and `description` identify the task in the UI, while `phases` names groups in the progress display. These fields belong to the host registry, not to model input.

Invalid registration raises `WorkflowInputError` before launch. This is the same idea as validating cron expressions in s12: do not wait until execution to discover a bad saved workflow.

Because the runtime uses `meta.name` in local artifact filenames, it also requires a 1-64 character safe slug containing letters, numbers, `.`, `_`, or `-`.

```python
def validate_meta(meta):
    if not isinstance(meta, dict):
        raise WorkflowInputError("meta must be an object literal")
    if not meta.get("name") or not meta.get("description"):
        raise WorkflowInputError("meta requires name and description")
    if not isinstance(meta["name"], str) or not WORKFLOW_NAME_RE.fullmatch(meta["name"]):
        raise WorkflowInputError("meta.name must be a safe 1-64 character slug")
    if "phases" in meta and (
        not isinstance(meta["phases"], list)
        or not all(isinstance(p, str) and p for p in meta["phases"])
    ):
        raise WorkflowInputError("meta.phases must contain non-empty strings")
    return meta
```

## Orchestration Primitives

A script receives an `ExecutionState` exposing a small set of orchestration primitives. It does not read files or run shell commands directly. The default interactive mode connects `agent()` to the same real API client as the host, and each workflow agent reads only the content supplied through workflow arguments. `demo` and unit tests use `MockAgentRunner` so events and journal replay are repeatable.

| Primitive | Purpose |
|------|------|
| `agent(prompt, {schema, label, phase})` | Dispatch one subagent |
| `parallel(thunks)` | **Barrier**: run every task concurrently and wait until all results return |
| `pipeline(items, *stages)` | Run each item through stages **without a barrier**; finished items proceed immediately |
| `phase(title)` | Mark the current progress phase and update the progress display |
| `log(message)` | Emit a progress log line |
| `workflow(name, args)` | Run a nested sub-workflow, one level only |

Use `pipeline` when each item independently crosses the same stages. Item A may reach stage three while item B is still in stage one. Use `parallel` when the next step needs every result from the preceding group.

```python
async def pipeline(self, items, *stages):
    async def run_item(item, idx):
        value = item
        for stage in stages:                       # Each item independently completes every stage
            value = await stage(value, item, idx)
        return value
    return await asyncio.gather(*[run_item(it, i) for i, it in enumerate(items)])
```

## Structured Output: Do Not Let Subagents Return Essays

`agent({schema})` asks a workflow agent to return only a JSON object matching the schema. The runtime parses and validates the result, then retries once if it does not match. Downstream code receives an object instead of extracting fields from prose.

s05 warned that tool arguments cannot be trusted completely. This is the same lesson in reverse: subagent output cannot be trusted completely either. Validate at the orchestration boundary, give one retry, and keep uncertainty out of the rest of the flow.

```python
run = await asyncio.to_thread(self.runner.run, prompt, schema, label)
result = run.value
if schema is not None:
    ok, err = SimpleJsonSchema(schema).validate(result)
    if not ok:                                       # Retry once with a reminder, then fail
        retry = await asyncio.to_thread(
            self.runner.run, prompt + "\n\nReturn valid JSON.", schema, label
        )
        result = retry.value
        ok, err = SimpleJsonSchema(schema).validate(result)
        if not ok:
            raise WorkflowInputError(f"agent({{schema}}) returned invalid output: {err}")
```

## Task State and Progress Events

`LocalWorkflowTask` maintains status and token usage and emits an SDK-style event stream: `task_started` → a sequence of `task_progress` events containing phase changes, subagent starts, and log batches → one final `task_notification` reporting completion or failure, plus the output file and agent and token counts.

The demo prints these events in order and returns the task state after the final notification.

```python
class LocalWorkflowTask:
    def progress_event(self, ptype, **data):         # Phase/subagent/log
        self.progress.append({"type": ptype, **data})
        print(f"  progress   {ptype} ...")
```

## Storage: Snapshot + Journal for Resuming after Interruptions

The runtime stores each run under `s16_workflow_runtime/.runtime/`: a `<runId>.json` snapshot, `<runId>.output.json` output, `<runId>.journal.jsonl` journal, and `<runId>.lock` coordination file. Every fresh run reserves a new `runId` with exclusive file creation before opening its journal. The run lock stays held through execution and final persistence, so another process cannot resume the same run at the same time. Its snapshot records the workflow name, arguments, and task state; resume validates the saved snapshot and journal before changing either successful artifact.

The journal is the core of checkpointed resume. It records every `agent()` result one line at a time:

```python
class WorkflowJournal:
    def record(self, key, value):
        self._f.write(json.dumps({"key": key, "value": value}) + "\n")
        self._f.flush()
        self.cache[key] = value
```

## Resume: Continue by runId and Reuse Everything Unchanged

Calling the workflow again with `resume_from_run_id` reruns the script, but every `agent()` computes a deterministic semantic key. If that key is present in the journal, it returns the cached result without executing again. Every unchanged call hits the cache; only a changed call and the downstream steps that depend on it actually rerun.

The key detail is that keys cannot depend on concurrency order. Agents in `parallel` and `pipeline` finish in nondeterministic order. If "the nth completion" became the key, cache entries would map to the wrong calls on the next run. A key therefore uses a stable hash of call content, including type, label, prompt, and schema, rather than a shared counter:

```python
def key(self, kind, label, prompt, schema):
    basis = f"{kind}|{label}|{prompt}|{json.dumps(schema, sort_keys=True)}"
    return f"{kind}-{_stable_hash(basis) % 10**10:010d}"

# Inside agent():
cached = self.journal.cached(key)
if cached is not MISS:
    self.task.progress_event("workflow_agent", label=label, status="cached")
    return cached
```

## Stable Call Keys

On resume, the runtime must match each current `agent()` call with its earlier journal record. A stable hash gives unchanged workflow code and arguments the same call key. Real model output may vary; when the call content has not changed, resume uses the result already saved in the journal.

## Workflow Topology in the Structured Trace

S16 reuses s15's session recorder rather than adding a second logging system. An interactive `Workflow` tool call appears inside the root tool span and creates a `workflow-orchestrator` child. Each `ctx.agent()` creates a `workflow-agent` child and a paired `workflow_node_start/workflow_node_end` span. The deterministic `demo` and `resume` commands also create a standalone trace, using `MockAgentRunner` as the recorded provider.

```text
tool_start: Workflow
└─ agent_create/start: workflow-orchestrator
   ├─ workflow_node_queued
   ├─ agent_create/start: audit:correctness
   │  └─ model_request/response
   ├─ workflow_dependency: audit:correctness → verify:correctness:...
   └─ agent_create/start: verify:correctness:...
      └─ model_request/response
```

Pipeline context records `item_index`, `stage_index`, and every prior node on which the next stage depends. `parallel()` gathers the completed node identities from its independent asyncio tasks, so a later stage can depend on the entire fan-out rather than whichever task happened to finish last. A journal hit emits a paired cached node span with `executed=false` and no model request. This makes an original run and a resumed run directly distinguishable.

Concurrency remains the workflow's existing mechanism: `asyncio.gather` schedules pipeline items and parallel thunks, an `asyncio.Semaphore` caps active `agent()` calls at eight, and `asyncio.to_thread` moves each blocking provider request off the event-loop thread. The trace records semaphore `queue_wait_ms`, model latency in the worker's inherited agent context, and workflow-node duration. It does not serialize or reorder the work.

The root model explicitly chooses the `Workflow` tool, but trusted workflow code deterministically decides which `ctx.agent()` calls exist and their dependency shape. A run permits at most 1,000 `agent()` calls, nested `workflow()` is limited to one level, and workflow agents receive only their prompt/schema—no harness tools—so they cannot delegate recursively. In the trace this produces Root → workflow-orchestrator → workflow-agent, with a maximum agent-tree depth of two.

Render the resulting topology and overlap with:

```sh
python s16_workflow_runtime/code.py demo
python s15_integrated_harness/trace_view.py --view tree
python s15_integrated_harness/trace_view.py --view timeline --width 120
```

The mock demo produces workflow-node timing but no `model_request`: it intentionally performs no provider call. Interactive s16 records both workflow nodes and the real LLM calls made by their `AnthropicAgentRunner`.

## See It Run

The sample `review-changes` workflow uses `pipeline` to send each review dimension independently through audit → verify. Interactive mode uses the real API and reads the material to review from `args.changes`. `demo` uses fixed runner data to show pipeline, validation, journal, and resume behavior.

```python
async def sample_workflow(ctx, args):
    ctx.phase("Review")
    changes = args.get("changes", "")

    async def audit(_v, dimension, _i):
        out = await ctx.agent(f"Inspect this change for {dimension} issues:\n{changes}",
                              schema=FINDINGS_SCHEMA, label=f"audit:{dimension}", phase="Review")
        return {"dimension": dimension, "findings": out["findings"]}

    async def verify(audited, dimension, _i):
        ctx.phase("Verify")
        verdicts = await ctx.parallel([                       # Verify every finding independently
            (lambda f=f: ctx.agent(f"Verify this finding against the change:\n{changes}\n\n{f}",
                                   schema=VERDICT_SCHEMA, label=f"verify:{dimension}:{f['title']}"))
            for f in audited["findings"]])
        return {"dimension": dimension,
                "confirmed": [f for f, v in zip(audited["findings"], verdicts) if v and v["isReal"]]}

    results = await ctx.pipeline(DIMENSIONS, audit, verify)
    ...
```

## Changes from s15

| | s15 Integrated Harness | s16 Workflow Runtime |
|--|-----------|---------------------|
| Loop | One model-driven loop | Main loop unchanged; a tool runs scripted orchestration |
| Who decides the next step | Model decides each round | Script declares the orchestration in advance |
| Multiple agents | One-shot s06 subagents | Scripted, resumable calls through an agent-runner boundary |
| New mechanisms | — | Script primitives, host registry and tool adapter, task lifecycle, progress events, journal/resume, structured output |

s16 does not replace the main loop. It exposes `Workflow` at the tool layer and starts a local workflow runtime behind it: one saved script coordinates N calls through an agent-runner boundary. An s06 subagent is dispatched once at the model's discretion; s16 turns the orchestration into resumable host code.

## Try It

```bash
python s16_workflow_runtime/code.py          # Both the main model and Workflow agents use the real API
python s16_workflow_runtime/code.py demo     # Deterministic review-changes fixture and event stream
python s16_workflow_runtime/code.py resume   # Resume by the last runId; every agent() hits the journal cache
```

In the default command, ask the model to read the changes, place that text in `args.changes`, and run the saved `review-changes` workflow. Both the main model and workflow agents use the real API. The `demo` command uses fixed runner data so lifecycle and resume behavior can be observed repeatedly. A resumed demo reports `agents=0 tokens=0` when every call hits the cache.

## Next

[s17 Goal Loop](../s17_goal_loop/) uses a smaller, independent loop to check whether a stated goal has been reached and decide whether another turn is needed.

<!-- translation-sync: zh@v11, en@v11, ja@v11 -->
