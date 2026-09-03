# Understanding the Agentic Harness — S15 & S16 Synthesis (GLM)

A synthesis of the S15 (Integrated Harness) and S16 (Workflow Runtime) chapters
of `learn-claude-code`, cross-referenced into `s13_agent_teams`, `s09_memory`,
and `s17_goal_loop` where the design questions lead there.

Abbreviated paths: `s15/code.py` = `s15_integrated_harness/code.py`,
`s16/code.py` = `s16_workflow_runtime/code.py`. Line numbers refer to the
repository at commit `8835ae4` and will drift as the lessons evolve — treat
symbol names as authoritative.

---

## 1. The Big Picture: What S15 and S16 Each Contribute

**S15 is the integration layer.** It takes the ~15 mechanisms built in s01–s14
(tools, permissions, hooks, todo, tasks, skills, memory, compaction, error
recovery, background tasks, cron, teams, worktrees, MCP) and hangs them all off
one `while True` loop — `agent_loop()` at `s15/code.py:3405`. One cycle:

```text
inject cron prompts + background task_notifications + todo reminders
  → prepare_context()        (compaction pipeline: budget → snip → micro → summarize)
  → update_context()         (memory recall + skills catalog + MCP state)
  → assemble_system_prompt() (rebuilt EVERY turn from live state)
  → call_llm()               (retry 429/529 → fallback model → reactive compact)
  → no tool_use block?  → Stop hooks → memory extraction → END turn
  → yes → PreToolUse hooks / permission check
        → dispatch: builtin handler | MCP handler | background thread
        |          | spawn_teammate | one-shot task | Workflow (s16)
        → PostToolUse hooks
        → append tool_result(s) to messages[] → next cycle
```

**S16 adds exactly one tool to that pool: `Workflow`.** The model calls it once
with `{name, args, resume_from_run_id}`; behind it a **deterministic
host-owned script** (not the model) decides the orchestration via `agent()`,
`parallel()`, `pipeline()`, `phase()` primitives. Every `agent()` result is
journaled to disk (`.runtime/<runId>.journal.jsonl`) keyed by a stable content
hash, so a resumed run replays cached results for unchanged calls and only
re-runs what changed.

The two chapters form a deliberate contrast:

| | S15 Integrated Harness | S16 Workflow Runtime |
|---|---|---|
| Who decides the next step | The model, every round | A trusted script, declared in advance |
| Multiple agents | Model-discretion subagents/teammates | Scripted `agent()` calls |
| Parallelism | OS threads, overlap with lead | `asyncio.gather` + semaphore (8) |
| Recoverability | Conversation history only | Journal + snapshot + resume by `runId` |

---

## 2. Q1 — Is there a cap on teammate count?

**No hard numeric cap in S15.** The README states it directly
(`s15/README.md:143`): *"There is no numeric teammate-count cap in S15 beyond
unique-name and host-resource constraints."* The only mechanical constraints:

- names match `^[A-Za-z0-9_-]{1,64}$`
- names are unique (case-insensitive) among active teammates
- `lead` and `agent` are reserved (`s15/code.py:1171`)

Practical ceiling: threads / RAM / provider rate limits.

**S16 does have numeric caps** (`s16/code.py:38-39`):

- `AGENT_CAP = 1000` — hard cap on `agent()` calls per run
- `CONCURRENCY = 8` — `asyncio.Semaphore` on simultaneous agent calls
- nested `workflow()` limited to one level; workflow agents get no tools, so
  the agent tree is depth 2 (Root → workflow-orchestrator → workflow-agent)

---

## 3. Q2 — How many teammates can a lead spawn? Do they run in parallel?

One `spawn_teammate` call spawns **one** teammate, but the lead may call it
repeatedly (multiple `tool_use` blocks per response, or across rounds). Two
delegation flavors with very different execution models:

| Kind | Tool | Execution | Context | Round cap |
|---|---|---|---|---|
| One-shot subagent | `task` | **synchronous** — blocks inside the lead's tool call | fresh `messages[]`, returns only a final summary | 30 (`range(30)`, `s15/code.py:2117`) |
| Persistent teammate | `spawn_teammate` | **async daemon thread** — overlaps other teammates and the lead | own private `messages[]`, `WORK → result → IDLE` loop | none |

Anti-recursion guard: neither child tool pool contains `task` or
`spawn_teammate`, so the topology is strictly Root → children (depth 1 in S15;
depth 2 in S16). After spawning, the lead is prompted to **end its turn**
instead of polling — team events landing in its mailbox wake the next turn
(`async_event_loop`, `s15/code.py:3632`).

---

## 4. Q3 — What stops an agent loop? Qualitative judgment or pre-designed tests?

Two stop layers, both decided by **deterministic code reading model output** —
never by running a test suite:

**Layer 1 — turn-level (mechanical, S15).** The loop stops when the response
contains **no `tool_use` block** (`has_tool_use()`, `s15/code.py:2083`; the
code comment explicitly says do not trust `stop_reason` alone). Error exits:
model error after retries, or `max_tokens` recovery exhausted
(`MAX_RECOVERY_RETRIES = 2`).

**Layer 2 — goal-level (qualitative, S17).** "No more tool calls" only means
*the turn* wants to end, not that *the goal* is met. A **separate evaluator
model call** (`PromptGoalEvaluator`) judges the user's stated condition against
the conversation, returning `{ok, reason, impossible}`:

- The evaluator has **no tools** — it cannot run tests itself; it only checks
  whether concrete evidence (e.g. "pytest exited 0") is present in the
  transcript. The *tests* are run by the worker's tools; the evaluator only
  judges the record.
- `ok=false` → the reason is appended to `messages[]` and the loop `continue`s
  into another turn automatically.
- Safety exits live *outside* the goal: global `MAX_TURNS` (env, default 0 =
  unlimited, `s17/code.py:853`), a cap on consecutive Stop-hook blocks, and
  `defer` while background work is still running.

So: Layer 1 is a mechanical signal; Layer 2 is **qualitative judgment over
concrete in-transcript evidence** — not a pre-designed test being executed.

---

## 5. Q4 — Typical loop counts before stopping

| Context | Bound | Typical |
|---|---|---|
| s01 / s15 lead turn | unbounded `while True` | 2–5 model rounds (simple); ~10–20 (chained reads/edits) |
| One-shot subagent (`task`) | hard cap **30** rounds | usually 3–10 |
| s15 teammate | no cap; `WORK → result → IDLE` | as long as the board has work |
| s16 workflow run | **1000** `agent()` calls, 8 concurrent | dimensions × stages agents |
| s17 goal loop | `MAX_TURNS` env, default unlimited | whole turns repeated until evaluator says `ok=true` |

---

## 6. Q5 — How many types of tools?

S15's lead pool has **26 built-in tools** (`BUILTIN_TOOLS`,
`s15/code.py:3132`), plus unbounded dynamic `mcp__server__tool` entries after
`connect_mcp`, plus S16's `Workflow`. Grouped into 9 families:

1. **Filesystem** (4): `read_file`, `write_file`, `edit_file`, `glob`
2. **Execution** (1): `bash` (`run_in_background=true` → background thread)
3. **Planning** (7): `todo_write` (session checklist) + task graph
   `create_task`, `update_task`, `list_tasks`, `get_task`, `claim_task`,
   `complete_task`
4. **Delegation** (1): `task` (one-shot subagent)
5. **Team** (6): `spawn_teammate`, `list_teammates`, `send_message`,
   `request_shutdown`, `request_plan`, `review_plan`
6. **Scheduling** (3): `schedule_cron`, `list_crons`, `cancel_cron`
7. **Isolation** (1): `create_worktree`
8. **Context / knowledge** (2): `load_skill`, `compact`
9. **Extension** (2): `connect_mcp` (+ s16 `Workflow`)

MCP authorization comes from the host's exact allowlist (`MCP_HOST_POLICY`),
never from a server's own description; anything unlisted defaults to user
confirmation. `assemble_tool_pool()` merges builtin + MCP every round and
rejects normalized name collisions.

---

## 7. Q6 — Do teammates share the lead's memory?

Three distinct things are often conflated as "memory":

| Layer | Shared with teammates? |
|---|---|
| **Conversation history** | **Never.** Each teammate has a private `messages[]` starting from its assignment prompt; children do not inherit the lead's conversation (`s15/README.md:143`). |
| **Persistent memory** (s09, `.memory/MEMORY.md`) | **Lead-only.** Recall is injected via `update_context()` → `assemble_system_prompt()` in the lead loop; extraction (`remember_after_turn`) runs only after lead turns. A teammate's system prompt is a fixed string (`s15/code.py:1541`) with no memory catalog, and its loop never calls `MEMORY_RUNTIME`. |
| **Shared substrate** | **Yes:** the model client, hooks, the task board (`.tasks/*.json`), the `MessageBus` mailboxes (`.mailboxes/`), and workspace policy. Coordination happens through **tasks + messages**, not memory. |

So teammates do not have "their own memory" in the s09 sense at all — they have
private conversation histories plus the shared task/message stores.

---

## 8. When does the lead spawn a teammate?

**Purely an LLM decision — there is no quantitative trigger anywhere.** No code
of the form "if pending tasks ≥ N, spawn" or "if context > X%, delegate." A
spawn happens iff the model emits a `tool_use` block named `spawn_teammate`.

The s15 trace README states the division of labor: *"The model chooses …
**whether to delegate**. Deterministic code applies permissions, dispatches
handlers, schedules threads…"*

| Layer | Who decides | Nature |
|---|---|---|
| *Whether* to spawn | LLM | Qualitative — infers "parallel work would help" from the conversation |
| *Whether the spawn succeeds* | Harness code | Deterministic validation, only after the model has decided |

**What shapes the model's "when" (soft, prompt-level):**
`PROMPT_SECTIONS["teams"]` (`s15/code.py:892`): *"When parallel work would
help, first propose a small team … wait for the user's confirmation. Do not
call spawn_teammate before the user confirms."* Note this confirmation gate is
**prompt-only** — nothing in `spawn_teammate_thread()` verifies user approval,
and the permission hook doesn't gate the tool either. Prompt conventions and
mechanical gates are different layers, deliberately.

Also: the lead does not automatically see teammate state —
`assemble_system_prompt()` injects memory/skills/MCP but **not** the teammate
list; the model must call `list_teammates`.

**Deterministic post-decision gates** (`s15/code.py:1493`): name
validity/uniqueness/reserved check; if `task_id` is passed, the atomic
`claim_task` must succeed or the spawn **rolls back** (the thread never
starts); `require_plan=true` sets the plan gate so the teammate's
bash/write/edit is blocked until the lead approves a plan. None of these decide
*when* — only *whether a requested spawn is legal*. A spawn can also only occur
inside a lead turn; `async_event_loop` never spawns on its own, it only wakes
the lead.

---

## 9. When is a teammate recycled?

**Teammates are persistent by design — no watchdog, TTL, or idle-reaper
exists.** An idle teammate polls forever (`IDLE_SCAN_INTERVAL = 2.0` s). "Lasts
as long as it can" resolves to exactly three exit paths:

```text
spawn → WORK ──final text──▶ result to lead ──▶ IDLE
          ▲                                     │
          │ auto-claim one ready task           │ inbox message (2 s wait, then board scan)
          └─────────────────────────────────────┘

IDLE/WORK ──validated shutdown_request──▶ stopping ──▶ gone (thread exits, state popped)
```

### Path 1 — Lead-initiated graceful shutdown (the only proactive path)

`request_shutdown(teammate)` (`s15/code.py:1870`) creates a `ProtocolState`
with a `request_id`; the teammate's inbox drain calls
`apply_shutdown_request()` (`:1462`), which validates sender=`lead`,
recipient=self, request still pending, teammate not already `"stopping"`. On
match: replies `shutdown_response` (approve), `should_stop = True`, loop exits.

- **Cooperative, not a kill:** takes effect at the next inbox-drain point; a
  tool call already in flight always finishes first. There is no
  `thread.kill()`.
- **Unenforced:** the system prompt says *"shut teammates down when
  coordination is complete"* — same soft convention as "propose a team first."
  A lead that never calls it leaves teammates idling until process exit.

### Path 2 — Self-recycling on error

`client.messages.create` throwing inside the teammate loop → the thread sends
the error to the lead and `break`s (`:1735`). Any uncaught exception in
`run_loop` is caught in `run()`, marked `status="error"`, reported to the lead.
So a teammate can die without the lead deciding anything.

### Path 3 — Process exit

Threads are daemons (`:1836`) — they die with the CLI process, ungracefully.

**Cleanup on any exit** is the same `finally` block (`:1815`):
`release_teammate_assignment()` returns unfinished work to the board
(`status → pending`, `owner → None` — work isn't lost, it's re-claimable),
then pops `active_teammates`, `teammate_trace_ids`, `plan_gates`,
`plan_request_ids`, and emits the trace `agent_end`.

### Work distribution is decentralized — teammates self-serve

The lead does not need to "ask" an idle teammate to help:

1. **Explicit assignment (optional, spawn-time only):** a `task_id` passed to
   `spawn_teammate` is claimed by the runtime before the thread starts.
2. **Self-service (main path):** after its first task the teammate enters IDLE
   and pulls work itself: `BUS.wait_for_messages(name, 2.0)` — messages take
   priority; on timeout it runs `claim_next_task(name)` (`:1370`), scanning
   ready tasks (pending, unowned, dependencies satisfied) and **atomically
   claiming at most one** via the file-locked `claim_task`. The task board
   *is* the coordination medium. One teammate grinds the board serially (one
   assignment at a time, enforced by `claim_task`); N teammates race, with the
   atomic claim preventing double-claiming.

Cost of the no-proactive-recycling design: an idle teammate with no board work
generates **no event at all** — it silently waits forever; idleness is cheap (a
sleeping thread) but nothing signals that the team has become useless.

---

## 10. Visualization of the Full Loop

```text
                        ┌──────────────────────────────────────────────┐
     user input ───────▶│  USER TURN (agent_lock)                      │
                        │  UserPromptSubmit hook → history.append      │
                        └──────────────┬───────────────────────────────┘
                                       ▼
   cron queue ───────┐   ┌──────────────────────── THE AGENT LOOP ──────────────────────┐
   bg notifications ─┼──▶│ 1. inject cron/background/todo reminders                     │
   team events ──────┘   │ 2. prepare_context (compact pipeline)                        │
                         │ 3. system prompt ← memory + skills + MCP                     │
   (async_event_loop     │ 4. LLM call (retry 429/529 → fallback model)                 │
    wakes lead too)      │ 5. ── no tool_use? ──▶ Stop hook / Goal evaluator ──▶ END    │
                         │        (s17: ok=false → append reason → continue)            │
                         │ 6. tool_use: PreToolUse hook → permission check              │
                         │      ├─ denied → tool_result(error)                          │
                         │      ├─ background bash → thread + placeholder               │
                         │      └─ handler: builtin | MCP | Workflow(s16) | spawn       │
                         │ 7. PostToolUse hook → tool_result[] → messages[] ───▶ (1)    │
                         └──────────────────────┬───────────────────────────────────────┘
                                                │ spawn_teammate / task
                          ┌─────────────────────┼──────────────────────┐
                          ▼                     ▼                      ▼
                   one-shot subagent      teammate thread A       teammate thread B
                   (sync, 30-round cap)   (daemon, own messages,  (daemon, own cwd
                   returns via tool_result own task/worktree,     from worktree, plan
                   to lead's messages)    WORK→result→IDLE)       gate, mailbox)
                          │                     │                      │
                          └───────── results via MessageBus ───────────┘
                                       (wake lead's next turn)
```

---

## 11. Dry-Run Example

Prompt: **"Count the Python files in s01 and s02 in parallel using two
teammates, then summarize."**

| Step | Actor | Action | `messages[]` / state |
|---|---|---|---|
| 1 | user | types prompt | `[{user: "count..."}]` |
| 2 | lead R1 | model returns 3 tool_calls: `create_task`×2 | +assistant, +2 tool_results `task_a1b2`, `task_c3d4` |
| 3 | lead R2 | `update_task`, `spawn_teammate(alice, task_a1b2)`, `spawn_teammate(bob, task_c3d4)` — runtime claims tasks, starts threads | tool_results: "spawned... end this turn" |
| 4 | lead | **no tool_use** → turn ends *(no active goal → return)* | lead idles |
| 5 | alice thread | own loop: `glob "**/*.py"` → 12 files → final text "s01: 12 files" → `BUS.send(alice→lead, "result")` → IDLE | alice's private messages only |
| 6 | bob thread | same, in parallel → "s02: 9 files" → result → IDLE | bob's private messages only |
| 7 | runtime | `async_event_loop` sees lead inbox non-empty → appends `[Team events] [result] alice: … [result] bob: …` → **starts lead turn automatically** | +user(team events) |
| 8 | lead R1′ | model answers "s01 has 12, s02 has 9, total 21." — **no tool_use** → Stop hook → memory extraction → stop | final text printed |

What the mechanics show:

- teammates ran **concurrently** (steps 5–6) but never touched the lead's
  `messages[]` or `.memory`
- results returned through the **MessageBus**, not tool_results
- the stop at step 8 was decided **mechanically** by `has_tool_use() == False`;
  an s17 `/goal` would insert the evaluator between that stop and the return,
  appending its reason and `continue`-ing if the evidence weren't there yet

---

## 12. Key Takeaways

1. **One loop, many mechanisms.** Everything in S15 — tools, hooks, memory,
   cron, teams, MCP — enters the same `while True`; the only continuation
   signal is the presence of a `tool_use` block.
2. **The model decides; code executes.** Delegation, tool choice, and stopping
   are model decisions; permissions, dispatch, compaction, retries, and
   cleanup are deterministic code. Every "gate" in the system is one or the
   other — and prompt-level conventions (propose-a-team, shut-down-when-done)
   are neither.
3. **Coordination is data, not telepathy.** Teams coordinate through a shared,
   file-locked task board and mailboxes — never through shared conversation or
   memory.
4. **S15 vs S16 is model-driven vs code-driven orchestration.** S15 leaves
   "when and how many" open and qualitative; S16 makes it deterministic,
   capped (1000 agents, 8 concurrent), journaled, and resumable.
5. **Termination has layers.** Turn-level stop is mechanical (no tool_use);
   goal-level stop (s17) is an independent evaluator judging in-transcript
   evidence qualitatively; safety exits (`MAX_TURNS`, consecutive-block cap)
   live outside both.
