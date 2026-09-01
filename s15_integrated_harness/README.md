# s15: Integrated Harness — Many Mechanisms, One Loop

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s13 → [s14](../s14_mcp_plugin/) → `s15` → [s16](../s16_workflow_runtime/) → s17

> *"Many mechanisms, one loop"* — tools, permissions, memory, tasks, teams, and plugins all hang off the same `while True`.
>
> **Harness layer**: Integration — put the mechanisms used by this example into one runnable system.

---

## Problem

The earlier chapters keep separate mechanisms in separate runnable examples. This chapter connects the mechanisms needed by the integrated runtime.

A long-running coding agent needs all of these at once:

- tool dispatch and permission boundaries
- hook extension points
- todo planning and task graphs
- skills, memory, and runtime system prompt assembly
- compaction and error recovery
- background tasks and cron scheduling
- teams, protocols, and IDLE task claiming
- task-bound worktrees
- MCP external tool integration

S15 does not introduce another isolated mechanism. It shows where the existing mechanisms enter the model loop and how their events return to the same conversation.

---

## Solution

![System Architecture](images/system-architecture.en.svg)

S15 does not introduce a new mechanism. It connects the components from the earlier chapters in one integrated harness:

```text
user input
  → UserPromptSubmit hooks
  → cron/background notification injection
  → context compact
  → memory + skills + MCP state assemble the system prompt
  → LLM
  → has tool_use block?
      no  → Stop hooks → return
      yes → PreToolUse hooks + permission
          → TOOL_HANDLERS / MCP handlers / background dispatch
          → PostToolUse hooks
          → tool_result / task_notification back to messages
          → next round
```

The loop keeps the same structure: call the model, check whether the response contains a `tool_use` block, execute tools, and append results to `messages`. The presence of a `tool_use` block decides whether tool execution continues.

---

## Where Each Component Sits

| Position | Component | Role |
|----------|-----------|------|
| Around user input | `UserPromptSubmit` hooks | Log, inject, or audit user input |
| Before LLM | cron queue | Inject scheduled prompts into `messages` |
| Before LLM | background notifications | Inject completed background work as `<task_notification>` |
| Before LLM | compaction pipeline | Budget large outputs, trim history, compact old tool results, summarize when needed |
| Before LLM | memory / skills / MCP state | Assemble the system prompt so the model sees current capabilities and long-term context |
| LLM call | error recovery | Retry 429/529, escalate `max_tokens`, compact on prompt-too-long |
| Before tool execution | `PreToolUse` hooks + permission | Block dangerous commands, out-of-bounds writes, destructive MCP tools |
| Tool dispatch | `assemble_tool_pool` | Assemble built-in tools and dynamic MCP tools |
| During tool execution | background dispatch | Move explicitly marked bash work into a daemon thread and return a placeholder result |
| After tool execution | `PostToolUse` hooks | Large-output warnings, logs, post-processing |
| Back to loop | tool_result | One `tool_result` per `tool_use`, then the next model round |
| No tool_use this round / on stop | `Stop` hooks | Stats, cleanup, audit |

---

## What code.py Contains

### Tools and Dispatch

The built-in tool pool contains 26 tools:

```text
bash, read_file, write_file, edit_file, glob
todo_write, task, load_skill, compact
create_task, update_task, list_tasks, get_task, claim_task, complete_task
schedule_cron, list_crons, cancel_cron
spawn_teammate, list_teammates, send_message
request_shutdown, request_plan, review_plan
create_worktree
connect_mcp
```

`assemble_tool_pool()` assembles these every round:

```text
BUILTIN_TOOLS + connected MCP tools
BUILTIN_HANDLERS + mcp__server__tool handlers
```

After `connect_mcp("docs")`, the next round exposes tools like `mcp__docs__search`.

### Permissions and Hooks

Permission is not hardcoded into the tool execution line. It is a `PreToolUse` hook:

```python
blocked = trigger_hooks("PreToolUse", block)
if blocked:
    results.append(tool_result(block.id, blocked))
    continue
```

That means permission, logging, and audit logic all attach to the same hook point. Lead tools, one-shot subagent tools, and teammate tools all pass through `PreToolUse`; an allowed call then runs `PostToolUse` after its handler.

The policy does not trust an MCP server's own description as authorization. The host owns a small exact allowlist for known read-only calls; every other MCP tool asks the user. File tools are denied outside `WORKDIR`, and every bash command asks before execution. Only the foreground user turn may open an interactive approval prompt; asynchronous turns fail closed instead of competing with the main CLI for stdin.

### Planning and Tasks

S15 keeps two planning layers:

- `todo_write`: lightweight plan for the current session, kept in memory
- task graph: cross-session, dependency-aware, claimable task files under `.tasks/task_*.json`

The first keeps a single agent from drifting. The second supports team coordination.

They share an intent, not an implementation: `todo_write` replaces one session checklist, while task records have stable IDs and individual lifecycle updates. The separate `task` tool below means "dispatch one isolated subagent"; it is not the Task System.

Task graph construction remains two-phase in the integrated host: the Lead creates all task nodes first, then calls `update_task` with the runtime IDs returned by `create_task`. Teammates receive only list, claim, and complete operations, so dependency structure is fixed by the Lead before work is distributed.

### Subagents and Teams

S15 has two kinds of delegation:

- `task`: one-shot subagent. It uses an isolated `messages[]`, discards intermediate context, and returns only a final summary.
- `spawn_teammate`: persistent teammate thread. When given a ready `task_id`, the runtime claims it before the thread starts; without one, the teammate can wait in IDLE for later work. A teammate without an assignment cannot use file or Shell tools. It follows `WORK → result → IDLE` without a fixed tool-round cap; model or dispatch failures emit an `error`, and thread cleanup releases an unfinished assignment back to the task board. It drains its inbox before every model call, so direct messages and shutdown requests cannot wait behind an unbroken tool-use sequence. While idle it waits for `MessageBus` delivery first, then scans ready tasks only after the wait times out and atomically claims at most one.

After spawning a teammate, Lead ends the current turn instead of repeatedly querying its status inside the model loop. A team event in Lead's mailbox makes the runtime start the next turn.

One-shot subagents solve context isolation. Persistent teammates solve long-running parallel collaboration.

Neither child tool pool contains `task` or `spawn_teammate`, so an s15 child cannot recursively create another child; the topology is Root → one-shot or teammate. There is no numeric teammate-count cap in s15 beyond unique-name and host-resource constraints. A one-shot runs synchronously inside its parent's tool call, while teammate daemon threads can overlap each other and the Lead. Children do not inherit the Lead's conversation: a one-shot receives only its assigned description plus `SUB_SYSTEM`, and a teammate receives its assignment plus a private message history. They share the model client, hooks, task/message stores, and workspace policy; a one-shot returns through its `task` tool result, while a teammate returns through `MessageBus` events.

### Memory, Skills, and Prompt

S15 reuses the s09 memory runtime directly. Before each model call, it reads the `.memory/MEMORY.md` catalog, selects records relevant to the current request, and passes their contents to `assemble_system_prompt(context)`. At the end of the turn, `extract_memories()` keeps information that can help in later sessions; when new records are stored, `consolidate_memories()` runs next.

The same system prompt also includes identity, tool guidance, the workspace, the skills catalog, and connected MCP servers. Skills contribute only their catalog; `load_skill(name)` loads full content on demand.

### Compaction and Recovery

Before the LLM call, S15 runs the compaction pipeline:

```text
tool_result_budget → snip_compact → micro_compact → compact_history
```

`snip_compact` archives the complete history before trimming its middle. `micro_compact` runs only above the context limit: it saves older consumed results before replacing them with recovery paths, keeps the latest 3 complete, and stops near 80% of the limit. If a new unseen result is itself too large, S15 keeps a preview and the full-output path before considering history summarization.

The model call is wrapped with recovery:

- 429: exponential backoff retry
- 529: exponential backoff, optionally switch to fallback model after repeated failures
- `max_tokens`: raise max tokens, then request continuation
- prompt too long: reactive compact and retry

### Background and Cron

When a bash call sets `run_in_background=true`, the main loop returns a placeholder without waiting for the command:

```text
should_run_background → start_background_task → placeholder tool_result
background done → task_notification → next round injects messages
```

Only explicitly marked bash calls enter the background path. A non-zero exit or worker exception produces a `failed` notification. Each shell runs in its own process group, which the runtime stops when the command or Agent process ends through the normal or `SIGTERM` path. A process that creates another session can leave that group.

The cron scheduler runs as a daemon thread and checks once per second. A durable one-shot job is persisted as `pending_delivery` before entering the queue and remains there until the model call containing its prompt succeeds; a failed call restores it to the queue, and a restart queues it again. Delivery is therefore at-least-once. The CLI watches `cron_queue`, Lead's inbox, and terminal background work; any of them can wake one automatic agent turn.

### Worktree and MCP

The task-scoped worktree behavior inherited from s13 manages working directories:

- a pending, unowned task may remain in the main workspace or be bound by `create_worktree(name, task_id)` to a separate branch and directory
- creation prevalidates the task, name, path, branch, and Git registry; a failed Git command is reconciled against the registry and branch state, and any partial checkout remains unbound and preserved for manual recovery
- an idle teammate atomically claims one ready task; the assignment records both `task_id` and its effective `cwd`
- Lead can also pass a ready `task_id` to `spawn_teammate`; the thread starts only after the claim succeeds
- all teammate file tools use that `cwd`; only the owning teammate can complete the task, and the assignment stays selected until that model turn ends
- removal stays in the host-side `remove_worktree()` helper. The model cannot call it. The user or host first checks task ownership, assignment leases, background work, and Git state; destructive removal requires separate user confirmation

The worktree changes tool default directories. It separates working copies; it is not a sandbox, and process-group cleanup does not contain a process that starts another session. This is why deletion remains host-owned.

Claiming or releasing a Task changes the assignment version and invalidates an old plan approval. An ordinary `send_message` only delivers text; it changes neither the Task identity nor the plan state.

MCP owns external capability:

- `connect_mcp(name)` connects a mock server
- `assemble_tool_pool()` assembles MCP tools and rejects normalized name collisions
- tool names use `mcp__server__tool`

---

## Structured Execution Traces

The s15 and s16 CLI entry points create one JSONL trace per interactive process. Importing either lesson does not create a trace, which keeps unit tests and library-style use free of side effects. Tracing is enabled by default and can be configured without changing the harness:

```sh
HARNESS_TRACE=1                         # set to 0 to disable
HARNESS_TRACE_DIR=traces                # relative to the process working directory
HARNESS_TRACE_OUTPUT=summary            # summary (safe default) or full
HARNESS_TRACE_PREVIEW_CHARS=500
python s15_integrated_harness/code.py
```

The CLI prints the selected `traces/run_<timestamp>_<id>.jsonl` path. Every record has a wall-clock timestamp, monotonic time, run/turn/agent identity, parent agent, span and causal IDs, thread identity, event name, and event-specific data. Paired boundary events share a `span_id`:

```text
run_start
turn_start
agent_active_start
model_request → model_response | model_error
harness_decision: dispatch_tools | continue | stop
tool_start → [tool_execution_start → tool_execution_end] → tool_end
agent_create → agent_start ... agent_end
background_queued → background_start ... background_end → background_notification
context_prepare → context_prepared
agent_active_end
turn_end
run_end
```

Tool arguments are recorded after recursive credential redaction. Tool results, prompts, assigned tasks, and messages use bounded previews plus character counts and SHA-256 hashes; set `HARNESS_TRACE_OUTPUT=full` only for a controlled experiment. Model response metadata records requested action types, tool names, stop reason, latency, and token usage when the provider reports it. It deliberately does not record hidden or natural-language reasoning content.

Use the standard-library viewer on a specific trace, or omit the path to select the newest trace in `traces/`:

```sh
python s15_integrated_harness/trace_view.py traces/run_....jsonl
python s15_integrated_harness/trace_view.py --view tree
python s15_integrated_harness/trace_view.py --view timeline --width 120
python s15_integrated_harness/trace_view.py --view metrics
```

The tree interleaves each agent's model calls and tools with child creation. The timeline uses `M`, `T`, `B`, `W`, `A`, `L`, and `P` for model, tool, background tool, workflow node, active cycle, agent lifecycle, and user/permission-wait spans. Derived metrics include model/tool counts, tool types, subagent and cache counts, maximum depth, maximum simultaneous active agents, provider token usage, summed and wall-clock model/tool time, workflow semaphore and agent-launch wait, human wait, and approximate orchestration overhead. `tool_time_ms` measures the nested handler-execution boundary, excluding permission waits and wrapper tools whose child work is measured separately. `model_time_ms` is client-observed provider latency—network plus server queue and inference—not pure GPU inference; use vLLM server metrics to split those components. Model/tool sums can exceed wall time when calls overlap, so their `*_wall_time_ms` variants merge overlaps. Orchestration overhead is residual wall time after model work, leaf tool execution, and human-only waits, so it is an estimate rather than a profiler sample.

The trace exposes the plan that actually executed, not private chain-of-thought. The model chooses whether to return text or `tool_use`, which tool and arguments to request, and whether to delegate. Deterministic code applies permissions, dispatches handlers, schedules threads, updates task and message state, compacts context, retries providers, and stops when the response has no tool use (or a recovery limit is reached). The event order lets those two layers be compared directly.

## Qwen/Qwen3.8-27B through Remote vLLM

`Qwen/Qwen3.8-27B` is the exact official Hugging Face model identifier. The clean integration path keeps the existing Anthropic SDK and points it at a current vLLM server, whose Anthropic-compatible `/v1/messages` endpoint translates system, assistant, `tool_use`, and `tool_result` blocks. The harness model path therefore remains:

```text
.env MODEL_ID
  → code.py MODEL
  → Anthropic.messages.create
  → ANTHROPIC_BASE_URL/v1/messages
  → vLLM
  → Qwen/Qwen3.8-27B
```

On the remote GPU host, use vLLM 0.17.0 or newer (prefer a current release) and enable both reasoning and automatic tool parsing:

```sh
vllm serve Qwen/Qwen3.8-27B \
  --host 0.0.0.0 --port 8000 \
  --served-model-name Qwen/Qwen3.8-27B \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --max-num-seqs 512
```

On the harness host:

```dotenv
ANTHROPIC_API_KEY=EMPTY
ANTHROPIC_BASE_URL=http://your-vllm-host:8000
MODEL_ID=Qwen/Qwen3.8-27B
```

For a vLLM server launched with `--api-key YOUR_TOKEN`, leave `ANTHROPIC_API_KEY` empty and set `ANTHROPIC_AUTH_TOKEN=YOUR_TOKEN`. The Anthropic SDK then sends `Authorization: Bearer YOUR_TOKEN`, which is the authentication form vLLM's protected `/v1/messages` endpoint expects.

No Qwen-specific branch is added to the agent loop. This runtime is non-streaming, so no streaming adapter is required. S16 structured output is prompt-requested JSON followed by local validation and one retry, rather than provider-enforced JSON schema, so it remains usable but should be tested empirically. Keep the vLLM tool parser enabled: without it, Qwen's generated tool syntax will not arrive as Anthropic `tool_use` blocks and the harness will stop as though it received an ordinary answer. Keep the reasoning parser enabled because Qwen3.8 thinks by default. Validate the endpoint with one plain response and one harmless tool call before a full experiment, and expose an unauthenticated `EMPTY` endpoint only on a trusted private network. See the [official model card](https://huggingface.co/Qwen/Qwen3.8-27B), [vLLM Qwen3.8 recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B), and [vLLM serving interfaces](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/).

## Trace Experiments

Run each prompt in a fresh CLI process so every JSONL file is one comparable sample. Warm the remote model first, repeat each experiment at least three times, retain server version and hardware beside the traces, and compare medians as well as individual timelines. Model choice is probabilistic, so the expected shape is a hypothesis, not an assertion.

| Experiment | Prompt | Expected trace |
|---|---|---|
| A — single-agent baseline | `Without using tools, reply with exactly: baseline complete` | One root turn and usually one model call, no tools or subagents. This estimates request plus harness overhead. |
| B — tool-heavy inspection | `Inspect s15_integrated_harness/code.py and trace_runtime.py. Find every model and tool-dispatch boundary, citing function names. Use filesystem search and reads; do not delegate.` | Several ordered `glob`/`read_file`/`bash` calls, repeated model calls, no `agent_create`. Tool latency dominates more of the active timeline. |
| C — decomposition | `Create three independent task-board items to analyze model calls, tool dispatch, and context compaction. Delegate each to a teammate, then synthesize their messages. Do not edit files.` | Three teammate `agent_create` events with root parent, task claims, mailbox events, independent model/tool spans, then a root synthesis call. |
| D — explicit parallel work | `In parallel, have separate teammates count tools in s15, workflow primitives in s16, and trace event types in trace_runtime.py. Report the three results as a table; do not edit files.` | Overlapping teammate spans on distinct threads and `maximum_parallel_agents > 1` if the model follows the request. Message delivery creates the join before root synthesis. |
| E — long context | `Read all chapter README files from s01 through s17 and compare how context, delegation, and stopping evolve. Quote no more than one sentence from any file.` | Many large tool results, repeated `context_prepare/context_prepared`, archived or truncated result summaries, and possibly `context_compact` plus a compaction-summary model call. |

For Qwen/Claude comparisons, use identical prompts, repository revision, permission answers, temperature/server settings, and warmed provider state. Compare not just total latency but tool choice, retries, depth, parallelism, failed calls, and whether the final task was actually completed.

---

## Changes from s14

| Scope | s14 MCP | s15 Integrated Harness |
|-------|---------|-------------------------|
| built-in tools | 6 | 25 |
| external tools | connected MCP tools | the same dynamic MCP path and host policy |
| local mechanisms | S04 tools, hooks, permission, MCP | todo, subagent, skills, compaction, memory, task graph, background bash, cron, teams, and worktrees |
| event sources | user input and tool results | user input, tool results, cron prompts, background notifications, and team events |

---

## Try It

```sh
cd learn-claude-code
python s15_integrated_harness/code.py
```

Try:

1. `Inspect this repository and tell me which Python files matter most.`
2. `Search the connected documentation for agent loop guidance.`
3. `Refactor the authentication module and login page in parallel in separate worktrees. Show me each plan before editing.`
4. `Remind me about the meeting in 3 minutes.`
5. `Install the dependencies in the background while you read README.md.`

Watch for:

- whether each tool call passes through hooks/permission
- whether MCP tools appear on the next round after `connect_mcp`
- whether a bash call with `run_in_background=true` returns a background placeholder
- whether cron automatically reminds you when the time arrives
- whether teammates submit plans and pause before approval
- whether an idle teammate atomically claims only one ready task
- whether every teammate file tool switches to the claimed task's `cwd`
- whether completion keeps the task `cwd` through the rest of the turn and releases it at IDLE

---

## Next

[s16 Workflow Runtime](../s16_workflow_runtime/) adds a `Workflow` tool to this host. A workflow keeps a fixed orchestration path in code and records progress so the same run can resume.

<!-- translation-sync: zh@v15, en@v15, ja@v15 -->
