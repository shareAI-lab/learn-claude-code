# Understanding the Agent Harness

This document consolidates the prior architecture investigation, Qwen provider
analysis, tracing implementation, harness Q&A, and the first real trace review
for `learn-claude-code`. It describes the repository at commit `8835ae4`
(`add tracing for harness operation`) and treats current symbols as more
authoritative than line numbers, which will drift as the lessons evolve.

The short conclusion is:

- `s15_integrated_harness` is the canonical cumulative agent harness.
- `s16_workflow_runtime` extends s15 with deterministic, journaled workflows.
- The model chooses actions; deterministic code validates, schedules, executes,
  records, and stops them.
- Qwen runs without Qwen-specific branches by serving
  `Qwen/Qwen3.8-27B` behind vLLM's Anthropic-compatible `/v1/messages` API.
- Structured JSONL tracing is now implemented for s15 and s16, with a viewer
  for execution trees, timelines, and metrics.
- The recorded real-world run proves single-agent Qwen tool use and usage
  reporting, but does not yet validate teammate or s16 workflow parallelism.

---

## 1. Repository architecture

This repository is a sequence of teaching snapshots, not one conventional
package. Each lesson introduces a mechanism; s15 integrates the mechanisms,
s16 adds a workflow runtime, and s17 demonstrates goal-level persistence.

| Runtime | Role in the architecture | Use in experiments |
|---|---|---|
| `s01`–`s14` | Incremental lessons for the loop, tools, memory, tasks, teams, MCP, and related mechanisms | Read them to isolate a concept, not as the cumulative production path |
| `s15_integrated_harness` | Canonical cumulative harness and interactive CLI | Primary target for model, tool, delegation, context, and tracing experiments |
| `s16_workflow_runtime` | Loads s15 and adds a deterministic `Workflow` tool | Primary target for scripted fan-out, pipelines, dependencies, concurrency, journals, and resume |
| `s17_goal_loop` | Focused variant that evaluates whether a user goal is actually satisfied | Reference for goal-level continuation beyond s15's turn-level stop rule |
| `agents/`, `docs/` | Legacy or transitional tracks | Do not use as the primary execution path |

The important runtime components are:

| Component | File and important symbol | Responsibility | Called by / calls into | State passed |
|---|---|---|---|---|
| CLI/session owner | `s15_integrated_harness/code.py`, `if __name__ == "__main__"` near line 3671 | Loads configuration, initializes one trace, starts services and the event thread, accepts prompts, and owns shared history | User console → `traced_lead_turn()` → `agent_loop()` | `history`, `context`, `session_state`, `agent_lock` |
| Lead loop | `s15_integrated_harness/code.py:3405`, `agent_loop()` | Repeats context preparation, model invocation, tool dispatch, observation insertion, and stop/recovery checks | CLI or `async_event_loop()` → context/model/tools | `messages`, `context`, `active_request`, `RecoveryState` |
| Prompt construction | `s15_integrated_harness/code.py:921`, `assemble_system_prompt()` | Rebuilds the system prompt from policy, workspace, skills, memories, time, and MCP state | `call_llm()` after `update_context()` | Context dictionary plus host-global runtime state |
| Context management | `prepare_context()`, `update_context()`, and the s09 memory runtime | Budgets large tool results, trims history, compacts when needed, recalls memories, and later extracts memories | Lead loop before and after model calls | Mutable `messages[]`, active request, memory files |
| Model boundary | `call_llm()` plus `trace_runtime.TracedMessages.create()` | Calls the configured Messages API with the current model, prompt, messages, tools, and token limit; records latency/actions/usage | Lead, subagents, teammates, memory, and s16 workflow agents | Anthropic-style system/messages/tools and provider response blocks |
| Tool registry | `BUILTIN_TOOLS`, `BUILTIN_HANDLERS`, `assemble_tool_pool()` | Keeps model-visible schemas separate from Python handlers and merges dynamic MCP tools | Rebuilt by the lead loop each round | Tool schema list and name→handler map |
| Tool execution | `agent_loop()`, `call_tool_handler()`, hooks | Applies permissions, handles background execution, invokes handlers, summarizes results, and creates `tool_result` observations | Model `tool_use` blocks → built-in/MCP/workflow handlers | Tool ID/name/arguments, handler result, trace span |
| One-shot subagent | `spawn_subagent()` near line 2098 | Runs a fresh, synchronous child loop and returns only its final text | Lead's `task` tool | Description, private messages, restricted child tools |
| Persistent team | `spawn_teammate_thread()` and `MessageBus` | Runs persistent worker threads with private histories, task assignments, mailboxes, plan gates, and graceful shutdown | Lead's team tools and the task board | Agent/task IDs, role, prompt, task cwd, mailbox messages |
| Task graph | task helpers and `.tasks/task_*.json` | Persists tasks, owners, status, dependencies, cycles, and worktree binding | Lead and teammates | Runtime-generated task IDs and dependency edges |
| Workflow runtime | `s16_workflow_runtime/code.py`, `WorkflowContext`, `run_workflow()`, `install_workflow_tool()` | Adds trusted scripted `agent()`, `parallel()`, `pipeline()`, `phase()`, journal, resume, and budget behavior | s15 `Workflow` tool → async runtime → runner | Workflow metadata/args, node keys, schemas, results, journal |
| Trace runtime | `s15_integrated_harness/trace_runtime.py`, `TraceRecorder` | Emits thread-safe, causally linked JSONL records and wraps every Messages API call | s15 initialization; reused by s16 | Run/turn/agent/span context and event-specific data |
| Trace viewer | `s15_integrated_harness/trace_view.py` | Reconstructs a tree, timeline, and derived metrics without provider dependencies | User points it at a JSONL trace | Ordered trace records |

State is deliberately split across several substrates:

- in-memory conversation: the lead's `history` and each child's private
  `messages[]`;
- runtime context: recalled memory, skills, MCP connections, recovery state,
  todo state, queues, and active teammates;
- durable coordination: `.tasks/`, `.mailboxes/`, `.scheduled_tasks.json`,
  `.memory/`, s16 `.runtime/` journals/snapshots, and optional worktrees;
- context spill/compaction: `.transcripts/` and
  `.task_outputs/tool-results/`;
- observability: `traces/run_<timestamp>_<id>.jsonl`.

## 2. End-to-end harness execution path

The repository-derived s15 path is:

```text
console input
  ↓
CLI input_wait span
  ↓
traced_lead_turn(trigger="user")
  ↓
UserPromptSubmit hooks + history.append(user request)
  ↓
agent_loop(messages, context, active_request)
  ├─ consume cron events
  ├─ inject completed background notifications
  ├─ optionally inject todo reminder
  ├─ prepare_context()
  │    ├─ tool-result budget
  │    ├─ snip/micro compaction
  │    ├─ fit oversized tool results
  │    └─ model-generated history summary if still too large
  ├─ update_context()
  │    └─ memory recall/catalog + MCP/team runtime state
  ├─ assemble_tool_pool()
  │    └─ built-ins + currently connected MCP tools (+ Workflow in s16)
  ├─ assemble_system_prompt()
  ├─ client.messages.create()
  │    └─ traced model_request → model_response/model_error
  ├─ no tool_use?
  │    └─ Stop hooks → memory extraction/consolidation → release task → return
  └─ one or more tool_use blocks?
       ├─ harness_decision(dispatch_tools)
       ├─ for each block, in response order
       │    ├─ tool_start
       │    ├─ PreToolUse hooks / permission wait
       │    ├─ background scheduling OR handler execution
       │    ├─ PostToolUse hooks
       │    └─ tool_end + result summary
       ├─ append user-side tool_result blocks
       └─ repeat the loop
  ↓
turn_end
  ↓
render assistant text and wait for user/team/cron/background input
```

One cycle of `agent_loop()` is therefore an observation-action loop, not a
separate planning phase. The assistant response may contain text and multiple
`tool_use` blocks. The blocks are executed in their returned order; their
outputs become a user-side `tool_result` message, after which the next model
call sees the observations.

There are three ways to enter another lead turn:

1. the user enters a new prompt;
2. the event thread detects cron or completed background work;
3. a teammate sends a mailbox event, which wakes the lead for automatic
   synthesis or follow-up.

The lead stops a normal s15 turn when `has_tool_use(response.content)` is
false. It intentionally does not rely only on the provider's `stop_reason`.
Other deterministic exits include an unrecoverable model error and exhausted
`max_tokens` recovery. In s17, a separate evaluator can reject a proposed stop
and start another turn until the goal is supported by evidence.

## 3. Deterministic harness decisions vs LLM decisions

There is no standalone planner object in s15. The executed plan emerges from
model-selected actions plus deterministic enforcement.

| Decision | Owner | Meaning |
|---|---|---|
| Return final text or request tools | LLM | Determines whether the current s15 turn appears complete |
| Tool name, tool arguments, and order requested | LLM | Expresses the next intended actions |
| Create/update todos or task-DAG nodes | LLM | Makes planning externally visible through tools rather than hidden reasoning |
| Delegate with `task` or `spawn_teammate` | LLM | No numeric or complexity threshold automatically triggers delegation |
| Invoke the s16 `Workflow` tool | Root LLM | Chooses whether to enter a trusted workflow |
| Which workflow nodes exist and depend on one another | Trusted workflow code | Once invoked, `parallel()`/`pipeline()` topology is deterministic rather than improvised by the model |
| Validate schemas, names, task IDs, owners, and dependency cycles | Harness | Rejects malformed or unsafe requested actions |
| Ask permission or deny a command/tool | Harness hooks plus human | Runs before the handler and can return an error observation |
| Execute returned tool blocks sequentially | Harness | Preserves response order; background and child work can outlive dispatch |
| Run threads, asyncio tasks, semaphore waits, mailboxes, and worktree cwd binding | Harness | Implements the requested topology and isolation mechanics |
| Compact context, retry rate/server errors, switch fallback model, or recover from `max_tokens` | Harness | Maintains viability without changing the user's goal |
| End a normal s15 turn on no `tool_use` | Harness reading model output | Mechanical turn stop; not proof that the broader goal is satisfied |
| Judge a persistent goal complete in s17 | Separate evaluator model | Qualitative judgment over transcript evidence; it has no tools of its own |

Prompt policy is a third category and must not be confused with a mechanical
gate. For example, the lead prompt says to propose a small team and wait for
confirmation before spawning, and to shut teammates down when coordination is
complete. `spawn_teammate_thread()` does not independently prove that approval
was given, and no idle-reaper forces cleanup. Those behaviors depend on model
compliance unless a deterministic check is added.

The trace records externally observable actions and outcomes. It records that
thinking/reasoning content was present, but deliberately does not persist or
claim to reconstruct private chain-of-thought.

## 4. Current model/provider abstraction

The current path is direct and small rather than fully provider-neutral:

```text
.env
  ├─ MODEL_ID
  ├─ FALLBACK_MODEL_ID (optional)
  ├─ ANTHROPIC_BASE_URL (optional)
  └─ Anthropic authentication variables
       ↓
s15_integrated_harness/code.py
  ├─ load_dotenv(override=True)
  ├─ client = Anthropic(base_url=...)
  ├─ MODEL = os.environ["MODEL_ID"]
  └─ call_llm(...)
       ↓
client.messages.create(
  model, system, messages, tools, max_tokens
)
```

The interface expected everywhere is Anthropic Messages:

- assistant content blocks include `text`, optional thinking metadata, and
  `tool_use`;
- tool observations are user-side `tool_result` blocks;
- the lead checks `response.content` and `response.stop_reason`;
- this runtime is non-streaming;
- usage is read from `response.usage` when the provider supplies it.

Tracing adds a transparent wrapper, not a second model abstraction.
`initialize_tracing()` replaces the client with `TracedClient`, whose
`messages.create()` delegates to the original SDK method while recording the
boundary. The s09 memory runtime is explicitly assigned this same wrapped
client and model. S16's `install_workflow_tool()` builds
`AnthropicAgentRunner(host.client, host.MODEL)`, so workflow-agent calls use
the same provider and appear in the same trace.

This is sufficient for Anthropic-compatible servers. A future OpenAI-only,
Responses-only, or streaming backend would still require a real adapter that
normalizes requests, tool calls/results, visible reasoning metadata, errors,
stream events, and usage.

## 5. Qwen/Qwen3.8-27B integration strategy

The earlier investigation initially concluded that Qwen was documented through
OpenAI-compatible vLLM/SGLang and therefore expected an adapter. The later
implementation resolved that question using a newer vLLM capability: current
vLLM exposes an Anthropic-compatible `/v1/messages` endpoint. That endpoint can
translate the harness's system, assistant, `tool_use`, and `tool_result` blocks,
so the smallest clean integration does not alter the agent loop.

The implemented path is:

```text
.env MODEL_ID=Qwen/Qwen3.8-27B
  → s15 MODEL
  → Anthropic SDK messages.create
  → ANTHROPIC_BASE_URL/v1/messages
  → vLLM translation/tool parser
  → Qwen/Qwen3.8-27B
```

The repository's current serving recipe is:

```bash
vllm serve Qwen/Qwen3.8-27B \
  --host 0.0.0.0 --port 8000 \
  --served-model-name Qwen/Qwen3.8-27B \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --max-num-seqs 512
```

The harness-side configuration is:

```dotenv
ANTHROPIC_API_KEY=EMPTY
ANTHROPIC_BASE_URL=http://your-vllm-host:8000
MODEL_ID=Qwen/Qwen3.8-27B
```

If vLLM is started with `--api-key YOUR_TOKEN`, leave
`ANTHROPIC_API_KEY` empty and use `ANTHROPIC_AUTH_TOKEN=YOUR_TOKEN`, so the SDK
sends bearer authentication. `EMPTY` is appropriate only on a trusted private
network.

Compatibility conclusions:

- `Qwen/Qwen3.8-27B` is the exact model identifier used by the implemented
  configuration and real trace.
- The reasoning parser is required because Qwen3.8 thinks by default.
- Automatic tool choice and the Qwen tool parser are required; otherwise tool
  syntax may arrive as ordinary text, causing s15 to stop on “no tool use.”
- No streaming adapter is needed because s15/s16 currently make non-streaming
  requests.
- S16 JSON is prompt-requested, parsed locally, schema-checked, and retried
  once; it is not provider-enforced structured output and needs empirical
  Qwen testing.
- The real trace at `traces/run_20260901T200234_810844Z_717f03f3.jsonl`
  demonstrates Qwen text, thinking-block metadata, tool calls, tool results,
  stop reasons, and token usage through `http://localhost:8000`.
- That trace validates the s15 single-agent path only. A harmless s16 workflow
  probe and team/concurrency probes remain necessary.

Repository references: the
[Qwen model card](https://huggingface.co/Qwen/Qwen3.8-27B), the
[vLLM Qwen recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B), and the
[vLLM serving interfaces](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/).

## 6. Tool execution architecture

S15 currently defines 26 built-in model-visible tools. S16 adds `Workflow`,
and connected MCP servers add a dynamic number of `mcp__server__tool` entries.

| Family | Tools | Count in s15 |
|---|---|---:|
| Filesystem | `read_file`, `write_file`, `edit_file`, `glob` | 4 |
| Execution | `bash` | 1 |
| Session planning | `todo_write` | 1 |
| One-shot delegation | `task` | 1 |
| Context/knowledge | `load_skill`, `compact` | 2 |
| Task DAG | `create_task`, `update_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task` | 6 |
| Scheduling | `schedule_cron`, `list_crons`, `cancel_cron` | 3 |
| Persistent team | `spawn_teammate`, `list_teammates`, `send_message`, `request_shutdown`, `request_plan`, `review_plan` | 6 |
| Isolation | `create_worktree` | 1 |
| External extension | `connect_mcp` | 1 |

Execution follows these boundaries:

1. `assemble_tool_pool()` returns model-visible JSON schemas and Python
   handlers. It merges MCP tools and rejects normalized name collisions.
2. The model returns one or more `tool_use` blocks.
3. The lead emits `harness_decision: dispatch_tools` and iterates those blocks
   in response order.
4. `PreToolUse` hooks see the raw request. The permission hook can deny it or
   record a human wait.
5. A foreground handler runs inside both a wrapper `tool_start/tool_end` span
   and a nested `tool_execution_start/tool_execution_end` span.
6. `bash(run_in_background=true)` instead creates a daemon worker and returns
   a placeholder; the eventual notification enters a later model turn.
7. `PostToolUse` hooks can log or persist oversized output.
8. Every result becomes a `tool_result` observation matched by tool-use ID.

MCP policy remains host-owned. A connected server can describe capabilities,
but the host's allowlist and permission hook decide whether a call is allowed.
Worktree creation changes the default cwd for a task assignment; it does not
create a security sandbox. Worktree removal stays host/user-owned rather than
being exposed as a model tool.

Multiple tool calls returned in one response are not automatically parallel.
They are dispatched sequentially unless a particular tool starts background,
teammate, or workflow work that continues concurrently.

## 7. Subagent architecture

S15 has two child-agent mechanisms, and s16 adds a third topology.

| Child kind | Created by | Execution | Context/result | Limit/depth |
|---|---|---|---|---|
| One-shot subagent | Root model calls `task` | Synchronous inside the root tool call | Fresh private `messages[]`; final text returns as the `task` tool result | 30 model rounds; cannot spawn children; s15 depth 1 |
| Persistent teammate | Root model calls `spawn_teammate` | Daemon `threading.Thread`; overlaps root and other teammates | Private `messages[]`; task board and mailbox are shared; results arrive through `MessageBus` | No hard numeric teammate cap; cannot spawn children; s15 depth 1 |
| Workflow agent | Trusted s16 workflow code calls `ctx.agent()` after root selects `Workflow` | `asyncio.to_thread` under an 8-slot semaphore | Receives only the supplied prompt/schema and returns a value to the workflow | 1,000 calls/run; one nested workflow level; Root → orchestrator → agent depth 2 |

### One-shot subagents

`spawn_subagent()` blocks the root's tool dispatch until the child returns. The
child has a restricted tool set and no `task`/`spawn_teammate`, which prevents
recursive delegation. Only the final textual summary enters the lead's
history; the child's private intermediate conversation does not.

### Persistent teammates

One `spawn_teammate` call creates one named worker. The lead may request more
workers in later tool blocks or rounds. The runtime validates name syntax,
case-insensitive uniqueness, reserved names, and any supplied task claim before
starting the thread. If task claiming fails, spawn rolls back.

A teammate:

- starts with its role, assignment prompt, optional claimed task, and optional
  plan gate;
- cannot use filesystem or shell tools until it has a claimed task;
- resolves filesystem tools against the task's root or task-bound worktree;
- holds at most one assignment at a time;
- can list, claim, and complete tasks and send intermediate messages;
- sends final text to the lead, releases completed work, enters `idle`, and
  polls its mailbox before atomically auto-claiming another ready task;
- exits only after validated graceful shutdown, an error, or process exit.

There is no TTL or idle reaper. Idle workers sleep and scan every two seconds.
Daemon threads die ungracefully with the process. Graceful shutdown is
cooperative: an in-flight model or tool call completes before the inbox request
is handled.

### Shared versus private state

| State | Shared? |
|---|---|
| Conversation history | No. Lead, one-shot agents, and teammates have separate `messages[]` |
| Persistent s09 memory injection/extraction | Lead only; teammate prompts do not load or write `.memory` |
| Provider client | Yes |
| Task board and dependency state | Yes, through locked `.tasks/*.json` records |
| Mailboxes | Yes, through `MessageBus` and `.mailboxes/*.jsonl` |
| Workspace | Shared by default; a claimed task may bind a different worktree cwd |
| Skills/MCP catalog | Available to the lead; not part of teammate tool/prompt context |
| Trace | Yes; agent/parent IDs and restored context keep each thread attributable |

`update_context()` currently collects active teammate names, but
`assemble_system_prompt()` does not render that field. The lead therefore uses
`list_teammates` for authoritative current status.

## 8. Concurrency/scheduling architecture

Concurrency is mechanism-specific:

| Mechanism | Scheduler | Parallel behavior | Join/result path |
|---|---|---|---|
| Multiple ordinary tool calls in one response | Lead Python loop | Sequential | All results are appended together for the next model round |
| Background bash | Daemon thread | Overlaps the lead and other background work | Completion queue → later `task_notification` |
| Persistent teammates | One daemon thread per teammate | Teammates, lead, and background workers can overlap | `.mailboxes`/`MessageBus` → event thread wakes lead |
| One-shot `task` | Root call stack | No overlap with root; child tools are sequential | Final summary is the tool result |
| s16 workflow nodes | `asyncio.gather`, semaphore, `asyncio.to_thread` | Up to 8 simultaneous agent calls | `parallel()` fan-in or pipeline stage dependency |
| Cron/team/background lead wake-up | `async_event_loop` plus `agent_lock` | Event detection is concurrent; only one lead turn mutates shared history at once | Automatic traced lead turn |

S15 task dependencies persist in `.tasks/task_*.json`. The lead alone edits
dependency edges; the runtime rejects missing IDs and cycles. Teammates race to
claim ready tasks, but the locked claim operation prevents duplicate ownership.
One worker processes only one assignment at a time.

S16 uses a different, script-owned dependency model. `pipeline()` makes each
stage depend on the previous stage for the same item; `parallel()` gathers all
fan-out node identities so later work can depend on the entire fan-out.
`CONCURRENCY = 8` bounds active `agent()` calls and `AGENT_CAP = 1000` bounds a
run. Journals use stable semantic call keys, allowing resume to replay unchanged
results without a new model request.

An illustrative s15 temporal shape is:

```text
time ───────────────────────────────────────────────────────────────▶

Lead       [LLM][spawn A][spawn B][end turn]         [LLM synthesis]
Agent A                    [LLM][tool][LLM]──result───┐
Agent B                             [LLM][tool][LLM]──┤
Event loop                                                wake Lead
```

The two spawn handler calls are sequential, but the threads overlap after they
start. A trace proves actual concurrency only when agent/model/tool intervals
overlap in monotonic time; a tree alone proves parentage, not overlap.

## 9. Existing observability/logging

Before structured tracing, useful but fragmented evidence already existed:

- lifecycle hooks: `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop`;
- console diagnostics for tool names, permissions, hooks, cron, teammates,
  retries, and compaction;
- lead transcripts in `.transcripts/transcript_<namespace>.jsonl`;
- oversized tool payloads in `.task_outputs/tool-results/`;
- task state in `.tasks/`, mailboxes in `.mailboxes/`, and durable cron state;
- s16 append-only journals and snapshots in `s16_workflow_runtime/.runtime/`.

Those artifacts answered “what persisted?” but not reliably “what called what,
on whose behalf, in what order, for how long, with which causal dependency?”
Console output also could not safely reconstruct concurrent execution.

Commit `8835ae4` closes that gap with one shared trace layer. CLI execution of
s15 or s16 creates one trace per interactive process. Importing either lesson
uses `NullTraceRecorder` and has no trace-file side effect, which preserves
library/test behavior. The trace is complementary to transcripts, task files,
mailboxes, and workflow journals rather than a replacement for them.

## 10. Proposed tracing instrumentation

The earlier proposal is now implemented. Its design stays at existing runtime
boundaries and does not ask the model to narrate its reasoning.

### Implemented pieces

- `trace_runtime.py` owns a thread-safe `TraceRecorder`, a no-op recorder,
  context scopes, paired spans, redaction/summarization, and a transparent
  Messages client wrapper.
- s15 initializes one recorder in the CLI, wraps the shared client, and
  propagates the wrapper into the memory runtime.
- turn, active-agent, model, context, decision, tool, handler, permission,
  background, mailbox, subagent, teammate, retry, and run boundaries emit
  structured events.
- trace context uses `contextvars`; explicit capture/restore carries run/turn/
  agent/span identity into worker threads.
- s16 reuses the host observer and adds workflow orchestrator, node, dependency,
  cache, queue-wait, and workflow-agent boundaries without serializing work.
- `trace_view.py` consumes the JSONL with only the standard library.

Configuration:

```dotenv
HARNESS_TRACE=1
HARNESS_TRACE_DIR=traces
HARNESS_TRACE_OUTPUT=summary
HARNESS_TRACE_PREVIEW_CHARS=500
```

`summary` is the safe default. Tool arguments are recursively secret-redacted;
prompts, messages, tasks, and results are represented by bounded previews,
character counts, and SHA-256 hashes. `full` adds full redacted payloads and
should be used only in a controlled experiment. Files are created with mode
`0600`.

The principal event sequence is:

```text
run_start
input_wait_start → input_wait_end
turn_start
agent_active_start
context_prepare → context_prepared
model_request → model_response | model_error
harness_decision: dispatch_tools | continue | stop
tool_start
  → permission_wait_start → permission_wait_end        (when required)
  → tool_execution_start → tool_execution_end          (leaf handler)
tool_end
agent_create → agent_start ... agent_end                (when delegated)
background_queued → background_start ... background_end
workflow_node_queued → workflow_node_start → workflow_node_end
agent_active_end
turn_end
run_end
```

One important semantic detail: a trace file represents an interactive CLI
process, which may contain several user and automatic turns. `turn_id` is the
unit for task/turn latency; `run_id` includes time waiting for all console
inputs. Analyses must not equate process lifetime with one task's latency.

## 11. Proposed trace schema

The schema proposal is implemented as version `1.0`. Every line is one JSON
object with stable envelope fields and event-specific `data`:

```json
{
  "schema_version": "1.0",
  "timestamp": "2026-09-01T20:02:34.813Z",
  "monotonic_ns": 123456789,
  "elapsed_ms": 3040.808,
  "run_id": "run_717f03f3",
  "turn_id": "turn_000001",
  "event_id": "evt_000010",
  "event": "model_response",
  "agent_id": "agent-root",
  "parent_agent_id": null,
  "agent_kind": "lead",
  "span_id": "span_000004",
  "parent_span_id": "span_000002",
  "caused_by_event_id": "evt_000009",
  "depends_on_event_ids": [],
  "thread": {"id": 1234, "name": "MainThread"},
  "data": {
    "status": "ok",
    "purpose": "lead",
    "model": "Qwen/Qwen3.8-27B",
    "stop_reason": "tool_use",
    "requested_actions": [{"type": "tool_use", "tool": "glob"}],
    "usage": {"input_tokens": 2855, "output_tokens": 171},
    "duration_ms": 3040.808
  }
}
```

Paired start/end events share a `span_id`. End events point back through
`caused_by_event_id`; workflow stages can list multiple
`depends_on_event_ids`. Monotonic time is used for duration/overlap analysis,
while the UTC timestamp is for human correlation.

Derived metrics are defined as follows:

| Metric | Derivation and interpretation |
|---|---|
| `total_model_calls` | Count completed `model_request` spans, including lead, teammate, memory, compaction, and workflow purposes |
| `total_tool_calls` / by type | Count `tool_start/tool_end` spans by tool name |
| `total_subagents` / `total_agents` | Count child `agent_create` events and distinct agents including root |
| `maximum_agent_depth` | Longest parent-agent chain |
| `maximum_parallel_agents` | Maximum overlap of active agent lifecycle intervals |
| `model_time_ms` | Sum of client-observed provider spans; includes network, server queue, and inference |
| `model_wall_time_ms` | Union of overlapping model intervals |
| `tool_time_ms` | Sum of nested leaf handler execution, excluding human permission waits and wrapper tools whose children are measured separately |
| `tool_wall_time_ms` | Union of overlapping leaf-tool intervals |
| `human_wait_ms` | Console input and permission-wait intervals |
| scheduling wait | Workflow semaphore and agent-launch queue wait recorded by the scheduler |
| orchestration overhead | Approximate residual wall time after model, leaf-tool, and human-only interval unions |
| token totals | Sum of provider-reported input/output/cache usage; missing usage stays explicitly missing |

Summed model/tool durations may exceed wall time when calls overlap. Model time
is not pure GPU inference; vLLM server telemetry is required to split queue,
prefill, decode, and network time. Orchestration overhead is a residual estimate,
not profiler sampling.

## 12. Proposed visualization

The proposal is implemented by `s15_integrated_harness/trace_view.py`:

```bash
python s15_integrated_harness/trace_view.py traces/run_....jsonl --view tree
python s15_integrated_harness/trace_view.py traces/run_....jsonl --view timeline --width 120
python s15_integrated_harness/trace_view.py traces/run_....jsonl --view metrics
```

The tree shows causality and parentage. The timeline shows actual overlap using
`M`, `T`, `B`, `W`, `A`, `L`, and `P` for model, tool, background tool,
workflow node, active cycle, agent lifecycle, and human/permission wait. The
metrics view provides machine-checkable totals.

### Real trace: `run_717f03f3`

The first reviewed trace used:

```text
Prompt:   Explain this repo. Don't modify any files
Runtime:  s15
Model:    Qwen/Qwen3.8-27B
Provider: Anthropic Messages → http://localhost:8000
Mode:     full
```

It is a single-root-agent run. It created no one-shot agents, teammates, or
workflows; all tool dispatch occurred on `MainThread` and was sequential.

```text
Root Agent
├─ Round 1: LLM 3.041s
│  ├─ bash: permission 9.739s, execution 84ms
│  └─ glob("**/*.md"): about 99ms
├─ Round 2: LLM 3.692s
│  ├─ read_file(README.md): under 1ms
│  └─ bash: permission 4.275s, execution 35ms
├─ Round 3: LLM 9.810s
│  ├─ todo_write
│  └─ bash: permission 3.481s, execution 27ms
├─ Round 4: LLM 2.930s
│  └─ todo_write
├─ Round 5: LLM 19.135s
│  └─ final response; no tool_use
├─ Harness decision: stop(reason=no_tool_use)
└─ Memory extraction: LLM 17.417s
   └─ stop_reason=max_tokens
```

Model usage and context growth:

| Call | Purpose | Input tokens | Output tokens | Duration | Result |
|---:|---|---:|---:|---:|---|
| 1 | Lead | 2,855 | 171 | 3.041s | `bash`, `glob` |
| 2 | Lead | 6,013 | 193 | 3.692s | `read_file`, `bash` |
| 3 | Lead | 13,128 | 510 | 9.810s | `todo_write`, `bash` |
| 4 | Lead | 14,603 | 111 | 2.930s | `todo_write` |
| 5 | Lead | 14,733 | 1,036 | 19.135s | Final response |
| 6 | Memory extraction | 1,310 | 1,000 | 17.417s | Hit `max_tokens` |

The full process lasted 391.318s, but the user-triggered turn lasted only about
73.8s. Process lifetime was dominated by waiting for the initial prompt and
for another prompt after completion.

```text
Process timeline

0s                 37.2s                       111.0s                         391.3s
│-------------------│----------------------------│------------------------------│
wait for prompt      active user turn ≈73.8s     wait for next input / Ctrl-C
```

Verified metrics:

| Metric | Value |
|---|---:|
| Model calls | 6 |
| Tool calls | 7 (`bash` 3, `glob` 1, `read_file` 1, `todo_write` 2) |
| Subagents / total agents | 0 / 1 |
| Maximum agent depth / parallel agents | 0 / 1 |
| Input / output tokens | 52,642 / 3,021 |
| Model time | 56.025s |
| Leaf tool execution | 0.246s |
| Human/input/permission wait over the process | 335.027s |
| Observed scheduling wait | 0 |
| Approximate orchestration overhead | 0.021s |

The trace proves that Qwen followed the no-edit constraint and successfully
used Anthropic-style tool blocks through vLLM. It also exposes a performance
issue: memory extraction consumed 17.4s, about 31% of all model time, produced
1,000 output tokens, and stopped at `max_tokens`.

## 13. Experiment methodology

Run every prompt in a fresh CLI process, warm the provider first, repeat each
experiment at least three times, and retain the repository revision, vLLM
version, model configuration, hardware, permission responses, and trace mode.
Compare medians and individual timelines because model behavior is stochastic.

| Experiment | Prompt | Expected trace behavior |
|---|---|---|
| A — no-tool baseline | `Without using tools, reply with exactly: baseline complete` | One root turn, normally one lead model call plus post-turn memory calls, no tool or child-agent spans. Separates request/memory/harness overhead. |
| B — tool-heavy inspection | `Inspect s15_integrated_harness/code.py and trace_runtime.py. Find every model and tool-dispatch boundary, citing function names. Use filesystem search and reads; do not delegate.` | Several ordered filesystem/shell calls and repeated lead calls; no `agent_create`. Shows permission and tool-result/context costs. |
| C — decomposition | `Create three independent task-board items to analyze model calls, tool dispatch, and context compaction. Delegate each to a teammate, then synthesize their messages. Do not edit files.` | Three task records and teammate `agent_create` events, task claims, mailbox events, independent spans, then root synthesis. |
| D — explicit parallel work | `In parallel, have separate teammates count tools in s15, workflow primitives in s16, and trace event types in trace_runtime.py. Report the three results as a table; do not edit files.` | Overlapping teammate intervals on distinct threads and `maximum_parallel_agents > 1`; mailbox results form the join. |
| E — long context | `Read all chapter README files from s01 through s17 and compare how context, delegation, and stopping evolve. Quote no more than one sentence from any file.` | Large observations, repeated context events, persisted/truncated outputs, and possibly `context_compact` plus a compaction-summary model call. |

Add an s16-specific run to validate deterministic workflows:

```bash
python s16_workflow_runtime/code.py demo
python s15_integrated_harness/trace_view.py --view tree
python s15_integrated_harness/trace_view.py --view timeline --width 120
```

The mock demo should show workflow nodes, dependencies, parallel overlap, and
cache/resume behavior without provider `model_request` events. Then run an
interactive Qwen `Workflow` call to validate `AnthropicAgentRunner`, local JSON
parsing/schema retry, usage, and eight-slot scheduling.

For Qwen-versus-Claude comparison, keep prompt, commit, permission answers,
temperature/server settings, trace mode, and warmed state identical. Compare
task success as well as latency, token use, tool selection, failed/denied calls,
retries, context growth, child count/depth, and achieved parallelism.

## 14. Files that would need modification

The historical wording was prospective; the tracing/Qwen plan has now been
implemented in commit `8835ae4`. The resulting change surface is:

| Files | Implemented change | Why |
|---|---|---|
| `.env.example` | Qwen/vLLM endpoint, parser, auth, and trace configuration examples | Makes model/provider and retention choices explicit without Qwen branches |
| `requirements.txt` | Dependency updates required by the traced Anthropic path | Keeps the runtime environment reproducible |
| `s15_integrated_harness/code.py` | Recorder initialization, client wrapping, run/turn/agent/context/decision/tool/permission/background/team spans, shared memory client | Instruments existing boundaries while preserving loop semantics |
| `s15_integrated_harness/trace_runtime.py` | New JSONL recorder, redaction, summaries, context propagation, and Messages wrapper | Centralizes tracing rather than scattering log formats |
| `s15_integrated_harness/trace_view.py` | New tree, timeline, and metrics postprocessor | Turns raw events into observable plan/topology/performance views |
| `s16_workflow_runtime/code.py` | Shared observer, orchestrator/agent/node/dependency/cache/scheduling events, traced real runner | Makes deterministic workflow topology and concurrency visible |
| `s15_integrated_harness/README.md` and localized variants | Trace usage, semantics, Qwen recipe, and experiment prompts | Documents operation and limitations |
| `s16_workflow_runtime/README.md` and localized variants | Workflow trace topology, dependencies, concurrency, and viewer usage | Documents s16-specific interpretation |
| `tests/test_trace_runtime.py` | Boundary privacy, redaction, concurrent writer, viewer, and workflow dependency tests | Protects schema validity and semantic reconstruction |
| `traces/*.jsonl` | Committed and local experiment evidence | Supplies real records for review; large/full traces require privacy care |
| `understanding_harness.md` | This consolidated architecture and experiment record | Replaces fragmented conversation notes with one handoff document |

The core Qwen switch itself is configuration-only because vLLM supplies the
Anthropic compatibility boundary. If that endpoint is removed or an
OpenAI-only provider is selected, a new provider adapter and tests would be
required in addition to these files.

## 15. Risks / compatibility issues

1. **vLLM compatibility is version-sensitive.** The current recipe expects a
   release with `/v1/messages`, Qwen3 reasoning parsing, and Qwen tool parsing.
   Probe the exact deployed build; do not infer support from the model name.
2. **Tool parser failure looks like normal completion.** If tool syntax remains
   text, s15 sees no `tool_use` and stops. Always run a harmless tool-call probe.
3. **Anthropic-compatible is not behavior-identical.** Thinking blocks,
   stop reasons, usage, tool-history validation, error codes, and token limits
   may differ across providers.
4. **S16 structured output is soft.** JSON is requested in the prompt and
   checked locally with one retry; Qwen may still return invalid or extra text.
5. **The real validation sample is narrow.** It proves one single-agent s15
   run, not team depth, mailbox causality, s16 concurrency, cache resume, or
   long-context compaction.
6. **Trace privacy is best-effort.** Key/text redaction cannot understand every
   secret format. `full` mode may retain sensitive prompts, files, and outputs;
   keep traces private and review before sharing.
7. **A file is a process trace, not automatically a task trace.** Console wait
   can dominate `total_runtime_ms`; use turn spans for active-task latency.
8. **Timing categories are observational.** Model duration combines network,
   queue, and inference; residual orchestration overhead is approximate; sums
   exceed wall time under concurrency.
9. **S15 has no hard teammate cap.** A compliant model can still create too
   many threads and provider calls. Resource/rate limits are only practical
   ceilings.
10. **Some team policy is prompt-only.** Confirmation-before-spawn and cleanup
    expectations are not complete host-enforced authorization/lifecycle rules.
11. **Daemon cleanup is weak.** In-flight tools cannot be forcibly cancelled,
    idle teammates have no TTL, and process exit is ungraceful.
12. **Worktrees are not sandboxes.** They separate Git working copies but do
    not contain processes or prevent access outside the assigned directory.
13. **Memory extraction is unexpectedly expensive.** The real trace shows a
    17.4s, 1,000-token call ending at `max_tokens`; this can distort short-run
    comparisons and should be isolated or fixed.
14. **Documentation can drift from code.** Use symbol searches and trace tests
    when counts or line references disagree with older notes.

## 16. Step-by-step implementation plan

This section closes the original plan by recording what is complete and what
still needs empirical validation. Each remaining step is decision-complete.

### Step 1 — Select the canonical scope and defaults (complete)

**Files affected:** s15/s16 runtime and documentation.

**Change:** Target s15 plus its s16 extension; retain tutorial snapshots. Use
metadata plus bounded summaries by default, with opt-in full traces.

**Why:** This covers the cumulative model-driven and deterministic workflow
paths without duplicating instrumentation across every lesson.

**How to validate:** Import s15/s16 and confirm no trace is created; start each
CLI and confirm one trace path is printed.

**Expected output:** No import side effect; `traces/run_<timestamp>_<id>.jsonl`
for each CLI process.

### Step 2 — Establish and probe the Qwen provider path (complete for s15)

**Files affected:** `.env`, `.env.example`, provider deployment configuration.

**Change:** Serve `Qwen/Qwen3.8-27B` with vLLM's reasoning/tool parsers and
point the existing Anthropic SDK at `/v1/messages`.

**Why:** It preserves the harness's content-block semantics and avoids a
Qwen-specific branch.

**How to validate:** Run one plain-response prompt, one harmless `glob` call,
and inspect model/usage fields in the trace.

**Expected output:** Qwen returns text and `tool_use`; the result is accepted on
the next model round; token usage is present. `run_717f03f3` satisfies this for
s15. Repeat with one interactive s16 `Workflow` call before declaring all paths
validated.

### Step 3 — Add the shared recorder and safe payload policy (complete)

**Files affected:** `s15_integrated_harness/trace_runtime.py`.

**Change:** Implement schema v1, exclusive `0600` JSONL creation, RLock writes,
context scopes, spans, recursive redaction, bounded summaries/hashes, null mode,
and the transparent Messages wrapper.

**Why:** All model-call purposes and threads need one consistent causal schema.

**How to validate:** Run the model-boundary, redaction, and concurrent-writer
tests in `tests/test_trace_runtime.py`.

**Expected output:** Valid unique JSONL records; no prompt/reasoning body in
summary mode; redacted secrets; paired spans with durations.

### Step 4 — Instrument the s15 lead loop and tools (complete)

**Files affected:** `s15_integrated_harness/code.py`.

**Change:** Add run/turn/active-agent scopes, context boundaries, explicit
harness decisions, tool wrapper/handler spans, permission wait, background
events, retry/recovery events, and post-turn memory purposes.

**Why:** These are the boundaries needed to reconstruct the executed plan and
separate provider, tool, human, and host time.

**How to validate:** Run a no-tool prompt, a foreground read, a permissioned
bash call, a background bash call, and a context-heavy prompt.

**Expected output:** Ordered paired events with one `harness_decision` after
each model response and no change to tool-result semantics.

### Step 5 — Instrument child-agent topology and communication (complete)

**Files affected:** `s15_integrated_harness/code.py`.

**Change:** Emit `agent_create/start/end`, propagate context into threads, and
record task/message/background causal links for one-shot and persistent agents.

**Why:** Counts alone cannot show parentage, concurrency, task ownership, or
the mailbox join.

**How to validate:** Run Experiments C and D, then compare tree and timeline.

**Expected output:** Root-parented child nodes, distinct thread names, task and
message events, overlapping active intervals, and a root synthesis after
mailbox delivery.

### Step 6 — Instrument s16 workflows without changing scheduling (complete)

**Files affected:** `s16_workflow_runtime/code.py`.

**Change:** Reuse the s15 observer; record orchestrator and workflow agents,
node queue/start/end, dependencies, cache hits, semaphore wait, and real runner
model calls.

**Why:** The workflow plan is code-owned and must expose its declared DAG,
parallelism, and resume behavior separately from root model choice.

**How to validate:** Run `demo`, then resume it, then run one real Qwen workflow.

**Expected output:** Original run has executed nodes; resume has cached node
spans with `executed=false` and no duplicate model request; real run includes
workflow-agent model spans.

### Step 7 — Build visualization and metric derivation (complete)

**Files affected:** `s15_integrated_harness/trace_view.py`.

**Change:** Add tree, timeline, and metrics views with interval-union math,
agent depth/parallelism, tokens, waits, cache counts, and residual overhead.

**Why:** Raw JSONL is auditable but not fast to interpret.

**How to validate:** Render the synthetic concurrency fixture and the real
`run_717f03f3` trace.

**Expected output:** Correct child tree, visibly overlapping timeline rows,
and the verified 6-model/7-tool real-run totals.

### Step 8 — Test and document the implementation (complete)

**Files affected:** `tests/test_trace_runtime.py`, `.env.example`, s15/s16
READMEs and translations.

**Change:** Cover privacy, redaction, concurrent writes, viewer metrics,
workflow lineage, deployment variables, interpretation, and experiment prompts.

**Why:** Trace correctness and privacy are part of runtime correctness.

**How to validate:** Run:

```bash
python tests/test_trace_runtime.py
```

**Expected output:** `Ran 5 tests` followed by `OK`. If `pytest` is installed,
`pytest -q tests/test_trace_runtime.py` exercises the same cases.

### Step 9 — Complete the experiment matrix (remaining)

**Files affected:** New private `traces/*.jsonl` samples and an experiment
results table; no runtime code unless a defect appears.

**Change:** Run Experiments A–E at least three times for Qwen, plus s16 demo,
resume, and one real workflow. Record medians and task-success judgments.

**Why:** One single-agent trace cannot validate delegation, concurrency,
compaction, structured JSON, or caching.

**How to validate:** The viewer must show the predicted structural signature
for each experiment; manually verify final-answer correctness.

**Expected output:** Baseline, tool-heavy, team/decomposition, parallel, long-
context, and workflow trace sets with comparable configuration metadata.

### Step 10 — Resolve findings from empirical runs (remaining)

**Files affected:** Most likely s09 memory settings/runtime, s15 policy, tests,
and documentation; change only after reproducing a finding.

**Change:** First isolate the 17.4s memory-extraction `max_tokens` behavior.
Then add a hard teammate/resource cap or stronger approval gate only if team
experiments show uncontrolled spawning. Add provider normalization only if the
Qwen workflow probe exposes an incompatibility.

**Why:** These are measured risks; speculative refactors would obscure the
teaching architecture and could change semantics unnecessarily.

**How to validate:** Re-run the affected experiment with identical settings and
compare task success, event topology, latency, usage, and errors before/after.

**Expected output:** Memory extraction completes within its intended bounded
budget; team runs stay within declared limits; s16 Qwen JSON/tool behavior is
confirmed or a narrowly scoped adapter requirement is documented.
