# GLOSSARY — s15 Integrated Harness

Domain terms as used across `README.md`, `ARCHITECTURE.md`, and `code.py`
docstrings/comments. Every definition is grounded in the cited file and
function; entries are in alphabetical order.

### Active request

The running user request that the lead loop tracks as first-class state
(`session_state["active_user_request"]` in `__main__`, passed as
`active_request` through `agent_loop` in `code.py`). Scheduled cron lines
("Run scheduled task: …") are appended to it when jobs fire, and it is what
`compact_history` / `reactive_compact` preserve as the **Authoritative
request** field — the only field allowed to carry instructions after
compaction.

### Agent loop (integrated loop)

The single control loop shared by every lead turn, `agent_loop` in `code.py`:
inject scheduled cron prompts and background notifications, emit a todo
reminder, run the compaction pipeline (`prepare_context`), refresh context and
tool pool, call the model, then either stop (no concrete `tool_use` block —
checked by `has_tool_use`, not `stop_reason` alone) or dispatch the requested
tools and append their results as one user message, repeating.

### Async event loop

`async_event_loop` in `code.py`: the daemon thread ("lead-events") that polls
every second and, when the cron queue has fired, the lead's inbox has team
events, or background work finished, wakes the lead agent by running the same
`agent_loop` inside `traced_lead_turn` with a combined trigger
("cron+team+background").

### Background task

A `bash` call with `run_in_background: true` (`should_run_background`,
`start_background_task` in `code.py`) is moved into a daemon worker thread
(`background-<id>`, own process session); the model immediately receives a
placeholder tool_result, and the real output arrives later as a
`<task_notification>` user message via `collect_background_results` /
`inject_background_notifications` / `build_user_content`.

### Compaction

The layered, cheap-first context-shrinking pipeline in `prepare_context`
(`code.py`): `tool_result_budget` (persist oversized tool outputs of the
latest message to `.task_outputs/tool-results/`), `snip_compact` (archive old
message ranges to `.transcripts/`, keep head 3 + tail 46), `micro_compact`
(oldest consumed tool results → saved-path markers, keep the 3 newest),
`fit_tool_results` (largest results → 1000-char persisted previews), and
`compact_history` (full model summarization into one `[Compacted]` message) —
the last firing only while the estimated size (`estimate_size`,
`len(json.dumps(...))`) still exceeds `CONTEXT_LIMIT` (50000 chars). Two
additional entry points exist: the `compact` tool (special-cased in
`agent_loop`) and `reactive_compact` on prompt-too-long errors (at most once
per turn).

### Cron job

A scheduled prompt — a 5-field cron expression plus prompt, stored apart from
conversation history (`CronJob`, `schedule_job`, `validate_cron` in
`code.py`). A daemon scheduler thread (`cron_scheduler_loop`) ticks each
second and enqueues due jobs (deduped by a per-minute `_last_fired` marker);
`agent_loop` then consumes the queue as `[Scheduled]` user messages.
`durable` jobs persist to `.scheduled_tasks.json`, and one-shot jobs use
`pending_delivery` with `acknowledge_cron_jobs` / `restore_cron_jobs` for
at-least-once delivery.

### Error recovery

`RecoveryState` + `with_retry` in `code.py` wrap every model call with up to
3 attempts: 429/529 errors are retried with exponential backoff (500 ms base,
×2 per attempt, capped at 32 s, up to 25% jitter), and 2 consecutive 529s
switch to `FALLBACK_MODEL_ID` if configured. Separately, `agent_loop` recovers
`max_tokens` stops (one 8000→16000 escalation, then up to 2 continuation
prompts) and prompt-too-long errors (one-time `reactive_compact`, detected by
`is_prompt_too_long_error`).

### Harness decision

The `harness_decision` trace event emitted by `agent_loop` in `code.py` at
every control-flow branch — `dispatch_tools`, `continue` (reasons
`prompt_too_long`, `max_tokens`, `compact_tool`), and `stop` (reasons
`no_tool_use`, `model_error`, exhausted recovery) — carrying
`decision`/`reason`/`action` so a trace is a faithful record of the loop's
control flow.

### Hook

Extension points kept deliberately outside the tool handlers: the `HOOKS`
registry with `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop`
events, registered via `register_hook` and run by `trigger_hooks` in
`code.py`. `trigger_hooks` executes callbacks in registration order and
returns the first non-`None` result — for `PreToolUse` that string becomes the
denying tool_result. Built-ins: `user_prompt_hook`, `permission_hook` +
`log_hook` (PreToolUse), `large_output_hook` (PostToolUse, warns above 100000
chars), and `stop_hook` (counts tool results).

### Integrated harness

The s15 runtime as a whole (`code.py`, module docstring and `__main__`): one
Python process that combines the course's mechanisms — tool dispatch,
permissions/hooks, todo and task board, teams, worktrees, MCP, compaction,
background and cron, memory and skills, and tracing — into a single runnable
CLI agent sharing one `agent_loop`, one (traced) Anthropic client, and
file-backed state under the working directory.

### Lead agent

The interactive console agent (`agent-root`) running on the main thread
(`agent_loop`, `__main__` in `code.py`). It is the only thread allowed to ask
interactive permission questions — `permission_hook` fails closed for any
other thread — and it runs lead turns from user input or from the async event
loop while coordinating teammates.

### MCP integration

Late-bound external tools (`MCPClient`, `connect_mcp`, `assemble_tool_pool`,
`MCP_HOST_POLICY` in `code.py`): `connect_mcp` registers a server (in-process
mocks stand in for real MCP transports), and `assemble_tool_pool` merges its
tools into the pool under normalized `mcp__{server}__{tool}` names with
collision detection. Authorization comes from the host policy table
(default `confirm`), never from server-provided descriptions, and
`MCPClient.call_tool` bounds exceptions to `MCP error: …` strings.

### Memory runtime

The s09 memory runtime loaded by file path in `load_memory_runtime` (`code.py`),
sharing the host's client, model, and workspace (`.memory/`, index
`.memory/MEMORY.md`). Each turn `update_context` calls `load_memories`
(traced as purpose `memory_recall`) to supply the memory catalog and relevant
records for prompt assembly; at turn end `remember_after_turn` runs
`extract_memories` and, when new records are stored, `consolidate_memories`.

### One-shot subagent

The `task` tool (`spawn_subagent`, `SUB_SYSTEM` in `code.py`): a synchronous
nested tool loop (up to 30 rounds, five filesystem tools only) with an
isolated `messages[]` and its own system prompt, returning only the last
assistant text to the parent. It is traced as `agent_create` /
`agent_start` … `agent_end` with `agent_kind="one_shot"`.

### Permission boundary

Layered authorization checked on the raw `tool_use` block before dispatch
(`permission_hook`, `DENY_LIST`, `safe_path` in `code.py`): `bash` commands
are screened against a substring deny list (`rm -rf /`, `sudo`, …) and then
require an interactive `Allow? [y/N]` answer (main thread only — asynchronous
turns fail closed); `read_file`/`write_file`/`edit_file` paths must resolve
inside `WORKDIR`; `mcp__*` tools follow their host policy. A string returned
by the PreToolUse hook short-circuits dispatch and becomes the denying
tool_result.

### Plan gate

Per-teammate approval state (`plan_gates`, manipulated by
`spawn_teammate_thread`, `_teammate_submit_plan`, `_run_teammate_tool`,
`complete_task`, and `advance_assignment_version` in `code.py`): values
`required`/`pending`/`approved`/`rejected`/`not_required` hard-block
`bash`, `write_file`, and `edit_file` (in `_run_teammate_tool`) and
`complete_task` until the lead approves a submitted plan.
`advance_assignment_version` re-arms the gate to `required` whenever a new
assignment is claimed, so old approvals never leak into new work.

### Prompt assembly

`assemble_system_prompt` + `PROMPT_SECTIONS` in `code.py`: the system prompt
is rebuilt from live context **every turn** in fixed section order
(identity, tools, tasks, teams, workspace, memory, compaction), followed by
the current time, the skills catalog, and — when present — the memory
catalog, relevant memory records, and connected MCP servers, joined by blank
lines.

### Skill catalog

`skills/<name>/SKILL.md` packages (YAML frontmatter `name`/`description`)
scanned at startup into `SKILL_REGISTRY` by `scan_skills` (`code.py`). Only
the name-plus-description catalog (`list_skills`) enters the system prompt;
full skill content is fetched on demand through the `load_skill` tool.

### Summary stats

`trace_stats.py` (`validate_file`, `Aggregate.add_file`, `main`): a
read-only, directory-wide consumer of `traces/*.jsonl` that first validates
every line against the trace envelope (required fields, string `event`,
object `data`; warnings for schema drift, `run_id` changes, missing
`run_start`/`run_end`), then aggregates model calls/models, stop reasons,
token totals from `model_response` usage, tool-name frequency, and
error/retry counts. Exit code 1 if any malformed line is found.

### Task board

Cross-session, dependency-aware task records under `.tasks/task_*.json`
(`Task`, `create_task`, `update_task`, `claim_task`, `complete_task` in
`code.py`), protected by an in-process `RLock` plus a cross-process `flock`
and atomic tmp+rename writes. `update_task` adds `blockedBy` edges only while
a task is pending and unowned (rejecting self-dependencies, missing targets,
and cycles via `_task_depends_on`); `claim_task` atomically verifies all
blockers (`can_start`), sets the owner and `in_progress`, and binds the
owner's cwd lease; `complete_task` requires ownership and a cleared plan gate.

### Teammate

A persistent teammate agent in its own daemon thread (`teammate-<name>`,
created by `spawn_teammate_thread` in `code.py`) with a reduced tool pool
(five filesystem tools plus `send_message`, `submit_plan`, `list_tasks`,
`claim_task`, `complete_task`) and a `MessageBus` inbox. Its filesystem tools
resolve cwd through `assignment_cwd` and fail closed until a task is claimed;
its final text is delivered to the lead as a `result` message, and when idle
it waits on the bus before auto-claiming the next ready task via
`claim_next_task`.

### Tool dispatch

The per-`tool_use`-block sequence in `agent_loop` (`code.py`): the `compact`
special case, then `PreToolUse` hooks (which can deny), then background
dispatch for marked bash calls, then the handler inside a
`tool_execution_start`/`tool_execution_end` span via `call_tool_handler`,
followed by `PostToolUse` hooks. All results — plus any newly finished
background notifications — are collected and appended as a single user
message by `build_user_content`.

### Trace event

One JSON object per line in a `traces/run_*.jsonl` file, emitted by
`TraceRecorder.emit` in `trace_runtime.py` with a fixed envelope: schema
version 1.0, UTC timestamp, `monotonic_ns`, `elapsed_ms`, `run_id`, `turn_id`,
`event_id`, `event`, agent identity fields, `span_id`/`parent_span_id`,
causal fields, thread info, and redacted `data`. The file is opened mode 0600,
appended line-buffered, and flushed per event; harness examples include
`harness_decision`, `context_compact`, `cron_*`, `task_*`, `background_*`, and
`model_retry`.

### Trace runtime

The harness-independent tracing library in `trace_runtime.py`
(`BaseTraceRecorder`, `NullTraceRecorder`, `TraceRecorder`,
`create_recorder`, `TracedClient`) plus `initialize_tracing` in `code.py`:
`NullTraceRecorder` is the default so importing the lesson never creates
files, while the CLI entry point creates a `TraceRecorder` from the
`HARNESS_TRACE*` environment variables. `wrap_client` turns every
`messages.create` into a `model_request` → `model_response`/`model_error`
span; `contextvars` scopes (turn, agent, model purpose, span) with
`capture_context`/`restore_context` keep worker-thread events attributable;
and `span()` pairs start/end events by `span_id`, recording `duration_ms` and
capturing exceptions as error data.

### Worktree (task-bound)

A real Git worktree under `.worktrees/<name>` on branch `wt/<name>`, bound to
exactly one pending, unowned task after name, Git, and registry validation
(`create_worktree` in `code.py`). Claiming that task makes the worktree the
owner's cwd — `assignment_cwd`/`task_worktree_cwd` fail closed on broken
bindings — and removal stays host-owned (`remove_worktree`): it requires a
completed bound task, no active cwd leases or running background commands, and
a clean tree, and it always retains the branch.
