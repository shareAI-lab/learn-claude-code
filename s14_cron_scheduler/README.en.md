# s14: Cron Scheduler — Producing Work on a Schedule

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

s01 → ... → s12 → s13 → `s14` → [s15](../s15_agent_teams/) → s16 → ... → s20
> *"Produce work on a schedule, decouple scheduling from execution"* — Cron scheduling, durable or session-level.
>
> **Harness Layer**: Scheduling — Independent thread checks time, queue delivers triggers.

---

## The Problem

An alarm clock doesn't need you to watch it. You set 7:00, it rings at 7:00 — you could be sleeping, showering, cooking, it rings regardless.

s13 lets the agent run slow operations in the background, but every operation is still triggered manually. You say something, the agent acts. "Run tests every morning at 9am", "Check CI status every 30 minutes" — these recurring tasks shouldn't need a human to push them each time.

---

## The Solution

![Cron Scheduler Overview](images/cron-scheduler-overview.en.svg)

Teaching code carries forward S13's simplified task system, background execution, and prompt assembly; to stay focused on the scheduler, it omits full error recovery, memory, and skill systems. Added: an independent cron scheduler thread that polls every second, queues matching jobs into `cron_queue`, and a queue processor that delivers them when the agent is idle.

Manual vs Scheduled:

| | Manual (s13) | Scheduled (s14) |
|---|---|---|
| Triggered by | User input | Scheduler thread |
| Trigger timing | Anytime | Specified by cron expression |
| Human involvement | Yes | No (scheduler auto-enqueues, idle agent auto-delivers) |
| Persistence | — | Durable survives restart |

---

## How It Works

### Four-Layer Model

Cron scheduling has four layers:

1. **Scheduler**: daemon thread, polls every second, checks if it's time
2. **Queue**: `cron_queue`, scheduler writes fired jobs
3. **Queue Processor**: sees non-empty queue and idle agent, starts one agent_loop turn
4. **Consumer**: agent_loop consumes queue and injects into messages

The teaching version implements a minimal queue processor: `agent_lock` tells whether the agent is idle, and queued cron work is delivered automatically. Real CC's `useQueueProcessor.ts` also handles UI blocking, queue priority, and different message modes.

### CronJob: Data Structure

Each cron task is a `CronJob` object:

```python
@dataclass
class CronJob:
    id: str
    cron: str        # "0 9 * * *" (5-field cron expression)
    prompt: str      # Message injected to the agent when fired
    recurring: bool  # True=recurring, False=one-shot
    durable: bool    # True=write to disk, survives sessions
```

Cron expression, 5 fields, used by Unix for 50 years:

```
min  hour  dom  month  dow
 *    *     *     *     *      Every minute
 0    9     *     *     *      Every day at 9:00
*/5    *     *     *     *      Every 5 minutes
 0    9     *     *    1-5     Weekdays at 9:00
```

Supports `*`, `*/N`, `N`, `N-M`, `N,M,...`.

### cron_matches: 5-Field Matching

Standard cron semantics: minute, hour, month must all match; day-of-month (DOM) and day-of-week (DOW) use OR when both are constrained:

```python
def cron_matches(cron_expr: str, dt: datetime) -> bool:
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return False
    minute, hour, dom, month, dow = fields
    dow_val = (dt.weekday() + 1) % 7  # Python Monday=0 → cron Sunday=0

    m = _cron_field_matches(minute, dt.minute)
    h = _cron_field_matches(hour, dt.hour)
    dom_ok = _cron_field_matches(dom, dt.day)
    month_ok = _cron_field_matches(month, dt.month)
    dow_ok = _cron_field_matches(dow, dow_val)

    if not (m and h and month_ok):
        return False
    # DOM and DOW: both constrained → either matching is enough (OR)
    dom_unconstrained = dom == "*"
    dow_unconstrained = dow == "*"
    if dom_unconstrained and dow_unconstrained:
        return True
    if dom_unconstrained:
        return dow_ok
    if dow_unconstrained:
        return dom_ok
    return dom_ok or dow_ok
```

### Independent Scheduler Thread: 1-Second Polling

The scheduler runs in an independent daemon thread, not dependent on whether agent_loop is executing. Individual job errors don't kill the entire thread:

```python
def cron_scheduler_loop():
    while True:
        time.sleep(1)
        now = datetime.now()
        minute_marker = now.strftime("%Y-%m-%d %H:%M")
        with cron_lock:
            for job in list(scheduled_jobs.values()):
                try:
                    if cron_matches(job.cron, now):
                        if _last_fired.get(job.id) != minute_marker:
                            cron_queue.append(job)
                            _last_fired[job.id] = minute_marker
                        if not job.recurring:
                            scheduled_jobs.pop(job.id, None)
                            if job.durable:
                                save_durable_jobs()
                except Exception as e:
                    print(f"[cron error] {job.id}: {e}")
```

Key design:
- **Independent of agent_loop**: scheduler checks time in background even when agent_loop isn't running
- **Date-aware minute_marker**: uses `"YYYY-MM-DD HH:MM"` to prevent same-minute double-fire while not skipping on the next day
- **Per-job try/except**: one bad job doesn't crash the scheduler thread
- **One-shot jobs**: auto-removed from scheduled_jobs after firing

### Queue Processor + agent_loop: Delivery

The queue processor does not check time. It only starts a turn when queued work exists and the agent is idle:

```python
def queue_processor_loop():
    while True:
        time.sleep(0.2)
        if not has_cron_queue():
            continue
        if not agent_lock.acquire(blocking=False):
            continue
        try:
            if has_cron_queue():
                run_agent_turn_locked()
        finally:
            agent_lock.release()
```

agent_loop also doesn't check time. It only takes fired tasks from `cron_queue` and injects them into messages:

```python
fired = consume_cron_queue()
for job in fired:
    messages.append({"role": "user",
                     "content": f"[Scheduled] {job.prompt}"})
```

Producer (scheduler thread), deliverer (queue processor), and consumer (agent_loop) are decoupled via `cron_queue`, `cron_lock`, and `agent_lock`.

### Validation: Prevent Bad Cron from Killing the Scheduler

`schedule_job` validates the cron expression before registering, returning an error for invalid input:

```python
def schedule_job(cron, prompt, recurring=True, durable=True):
    err = validate_cron(cron)
    if err:
        return err
    # ... register job
```

Loading durable jobs from disk also skips invalid expressions, preventing a single bad task from breaking startup.

### Durable vs Session-only

- **Durable**: Task definition written to `.scheduled_tasks.json`. Loaded on agent restart.
- **Session-only**: In-memory only. Gone when the agent closes.

> **Important caveat**: The cron scheduler must run inside the agent process. Process exits, scheduler stops. Durable only means the task definition survives restarts — next time the agent starts, the scheduler discovers "it should fire" and fires. If you need "run even when the app is closed", use system crontab or systemd timer.

### Putting It Together

```
1. On startup:
   load_durable_jobs() → restore durable tasks from .scheduled_tasks.json
   Thread(cron_scheduler_loop, daemon=True).start() → scheduler begins polling
   Thread(queue_processor_loop, daemon=True).start() → processor waits to deliver

2. Register a task:
   schedule_cron(cron="*/2 * * * *", prompt="run date", durable=True)
   → CronJob written to scheduled_jobs + .scheduled_tasks.json

3. Every 2 minutes:
   Scheduler checks → cron_matches returns True → cron_queue.append(job)
   → queue processor sees idle agent → agent_loop consume_cron_queue
   → injects "[Scheduled] run date"
   → LLM receives message, runs date command

4. Process shutdown:
   Scheduler thread stops (daemon=True)
   .scheduled_tasks.json stays on disk
   Next startup → load_durable_jobs → tasks restored
```

---

## Changes from s13

| Component | Before (s13) | After (s14) |
|-----------|-------------|-------------|
| Trigger method | User manual trigger | Scheduler thread auto-enqueues |
| New types | — | CronJob dataclass (id, cron, prompt, recurring, durable) |
| New functions | — | cron_matches, validate_cron, schedule_job, cancel_job, cron_scheduler_loop, queue_processor_loop |
| New storage | — | .scheduled_tasks.json (durable) + memory (session-only) |
| Threads | Background execution thread | + Scheduler thread (daemon, 1s polling) + queue processor thread |
| Queue | background_results | + cron_queue (scheduler writes, queue processor delivers, agent_loop consumes) |
| Tools | 8 (s12/s13) | + schedule_cron, list_crons, cancel_cron (11) |

---

## Try It

```sh
cd learn-claude-code
python s14_cron_scheduler/code.py
```

Try these prompts:

1. `Schedule a task to print the current date every 2 minutes`
2. `List all cron jobs`
3. `Create a one-shot reminder in 1 minute to check the build status`
4. `Cancel the recurring job and verify with list_crons`

What to observe: Is the scheduler thread running independently? Do cron tasks fire at the correct time? Without a new prompt, do you see `[queue processor]` and automatic execution? Is the durable job written to `.scheduled_tasks.json`?

---

## What's Next

One agent can do a lot now: plan, compress, background, schedule. But some tasks are too big for one agent.

"Refactor the entire backend" — overhaul auth, database layer, API routes, and tests. One agent's attention is limited. This needs a team.

s15 Agent Teams → One agent isn't enough, form a team. Persistent teammates + async inboxes.

<details>
<summary>Deep Dive into CC Source</summary>

> The following is a complete analysis based on CC source code `CronCreateTool.ts`, `cronScheduler.ts`, `cron.ts`, `cronTasks.ts`, `cronTasksLock.ts`, `useScheduledTasks.ts` (139 lines).

### 1. Three Cron Tools

CC exposes three cron tools to the model: `CronCreate`, `CronDelete`, `CronList`. All controlled by compile-time gate `feature('AGENT_TRIGGERS')` and runtime GrowthBook flag `tengu_kairos_cron`. There's also a `CLAUDE_CODE_DISABLE_CRON` env var for local override.

### 2. Storage: `.claude/scheduled_tasks.json`

```json
{ "tasks": [{ "id": "abc12345", "cron": "0 9 * * *", "prompt": "...", "recurring": true, "durable": true, "createdAt": 1714567890000 }] }
```

Durable tasks write to disk; session-only tasks live in `STATE.sessionCronTasks` memory array (lost on process restart). A `.scheduled_tasks.lock` file prevents duplicate firing across multiple sessions of the same project.

### 3. Scheduler: 1-Second Polling

`cronScheduler.ts` checks every second (`CHECK_INTERVAL_MS = 1000`). Whoever holds the lock triggers file tasks; all sessions trigger session-only tasks. A `chokidar` file watcher monitors `scheduled_tasks.json` changes.

### 4. Cron Expression: Standard 5 Fields

Minute hour day month weekday. Supports `*`, `*/N`, `N`, `N-M`, `N-M/S`, `N,M,...`. Doesn't support `L`, `W`, `?`. All times interpreted in local timezone. Day-of-month and day-of-week use OR semantics when both are constrained.

### 5. Jitter (Thundering Herd Prevention)

- Recurring tasks: trigger delay up to 10% of period (max 15 min), deterministic hash based on task ID
- One-shot tasks: up to 90s early when firing time falls on `:00` or `:30`
- Jitter config adjustable via GrowthBook, refreshed every 60 seconds

### 6. Auto-Expiration

Recurring tasks auto-expire after 7 days (configurable, max 30 days). Fire one last time before expiry, then auto-delete.

### 7. Job Limit

`MAX_JOBS = 50` (`CronCreateTool.ts:25`). Returns error when exceeded: "Too many scheduled jobs (max 50). Cancel one first."

### 8. Trigger Injection

After firing, enqueued via `enqueuePendingNotification()` with `priority: 'later'` into the command queue. Tagged `workload: WORKLOAD_CRON` — API serves cron-initiated requests at lower QoS when capacity is tight.

### 9. Queue Processor: Automatic Delivery

Real CC auto-triggers processing through `useQueueProcessor.ts:48-60` when no query is active, UI isn't blocked, and queue is non-empty. `queueProcessor.ts:52-87` dispatches commands to `handlePromptSubmit()` by queue priority. The teaching version keeps the core behavior with `queue_processor_loop`: when queued work exists and the agent is idle, it starts one agent_loop turn automatically.

</details>

<!-- translation-sync: zh@v1, en@v1, ja@v1 -->
