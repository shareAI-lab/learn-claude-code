# s12: Cron Scheduler — Start Work on a Schedule

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s10 → s11 → `s12` → [s13](../s13_agent_teams/) → ... → s17

---

## The Problem

S11 changes how a command runs after it starts: a long Bash command can run in the background. It does not record when future work should start, and no component keeps checking the current time.

For requests such as "run tests every morning at 9am" or "check CI status every 30 minutes," the user would still have to submit the prompt again at each scheduled time. The Harness needs to store the schedule, put the corresponding prompt into a pending queue when it becomes due, and deliver it to the Agent Loop when the Agent is idle.

---

## The Solution

![Cron Scheduler Overview](images/cron-scheduler-overview.en.svg)

Suppose the Agent registers this job:

```text
cron:   0 9 * * *
prompt: run tests
```

At 09:00 local time, the scheduler thread matches the job and puts `[Scheduled] run tests` into `cron_queue`. The queue processor waits until the Agent is idle, then starts an Agent Loop turn. The model can then call Bash to run the tests.

The S12 code keeps the five base tools and Hooks from S04, then adds `schedule_cron`, `list_crons`, and `cancel_cron`. It does not include S11 background commands because this chapter delivers a prompt to start work, not the result of a command that is already running.

---

## How It Works

### What CronJob stores

```python
@dataclass
class CronJob:
    id: str
    cron: str
    prompt: str
    recurring: bool
    durable: bool
    pending_delivery: bool = False
    last_fired: str | None = None
```

`cron` controls when the job becomes due. `prompt` is the task sent to the Agent. `pending_delivery` marks a due job that the model has not accepted, while `last_fired` prevents another enqueue in the same minute.

### Five-field cron expressions

```text
minute hour day month weekday
   *     *    *    *      *    every minute
   0     9    *    *      *    every day at 09:00
  */5    *    *    *      *    every 5 minutes
   0     9    *    *     1-5   weekdays at 09:00
```

This chapter supports `*`, `*/N`, `N`, `N-M`, and `N,M,...`. Before saving a job, `schedule_job()` calls `validate_cron()` and rejects expressions with the wrong number of fields or out-of-range values.

### Enqueue when due

The scheduler thread reads local time once per second. When an expression matches and the job has not fired in the current minute, `_enqueue_due_job()` saves `pending_delivery` and `last_fired` before adding the job to the in-memory queue:

```python
def poll_due_jobs(moment: datetime):
    minute_marker = moment.strftime("%Y-%m-%d %H:%M")
    with cron_lock:
        for job in list(scheduled_jobs.values()):
            if job.pending_delivery or job.last_fired == minute_marker:
                continue
            if cron_matches(job.cron, moment):
                _enqueue_due_job(job, minute_marker)
```

If persistence fails, `_enqueue_due_job()` restores the previous state and does not expose a memory-only delivery to the queue processor.

### Deliver when the Agent is idle

`queue_processor_loop()` does not check the time. It checks the queue, and `agent_lock` prevents a scheduled turn from changing the session while a user turn is running:

```python
def queue_processor_loop(stop_event=RUNTIME_STOP):
    while not stop_event.wait(0.2):
        if not has_cron_queue() or not agent_lock.acquire(blocking=False):
            continue
        try:
            if has_cron_queue():
                run_agent_turn_locked()
        finally:
            agent_lock.release()
```

The Agent Loop takes due jobs from the queue and appends each one as a new user message:

```python
fired = consume_cron_queue()
for job in fired:
    messages.append({"role": "user", "content": f"[Scheduled] {job.prompt}"})
```

If the model call fails, those messages are removed from the current session and the jobs return to the queue. Once the model accepts the call, one-shot jobs are removed and recurring jobs clear `pending_delivery` until the next match.

### Persistence boundary

| Mode | Stored in | After a process restart |
|---|---|---|
| `durable=True` | `.scheduled_tasks.json` | Loaded again |
| `durable=False` | Memory | Gone |

The code updates `.scheduled_tasks.json` through a temporary file and `os.replace()`. If the file is corrupt, startup reports the error instead of ignoring it.

Delivery is at least once. If the process exits after the model accepts a prompt but before the acknowledgement reaches disk, the same job may be delivered again after restart.

### Runtime boundary

- The scheduler uses the Agent process's local time.
- The scheduler stops when the Agent process exits. `durable` preserves the job definition only.
- Restart loads saved jobs but does not replay schedule times missed while the process was down.
- Scheduled turns run in the queue processor thread. A tool call that needs interactive approval is denied instead of competing with the main terminal for input.
- Scheduler and queue processor threads start only in the CLI. Importing `code.py` starts no background thread.

Use crontab, a systemd timer, or an external scheduler when jobs must run while the Agent is closed.

---

## Try It

```sh
cd learn-claude-code
python s12_cron_scheduler/code.py
```

Enter these prompts in order:

1. `Schedule "run date" every 2 minutes and keep it after restart.`
2. `List all cron jobs.`
3. `Cancel the cron job you just created.`

You can inspect `.scheduled_tasks.json` and watch for the `[Scheduled] run date` message when the job becomes due. Keep the Agent process running while testing a minute-level schedule.

---

## What's Next

The scheduler can start an Agent Loop turn at a specified time, but one Agent still handles that turn. When a task requires parallel investigation, changes across multiple modules, and a combined result, the Harness also needs to assign work to multiple Agents and collect what each one produces.

s13 Agent Teams → A Lead assigns tasks, teammates run independently, and results return through inboxes.

<!-- translation-sync: zh@v9, en@v9, ja@v9 -->
