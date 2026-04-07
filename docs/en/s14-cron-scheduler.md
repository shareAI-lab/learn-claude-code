# s14: Cron Scheduler

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > [ s14 ] > s15 > s16 > s17 > s18 > s19`

## What You'll Learn

- How schedule records store future intent as durable data
- How a time-based checker turns cron expressions into triggered notifications
- The difference between durable jobs (survive restarts) and session-only jobs (die with the process)
- How scheduled work re-enters the agent system through the same notification queue from s13

In s13 you learned to run slow work in the background so the agent does not block. But that work still starts immediately -- the user says "run this" and it runs now. Real workflows often need work that starts later: "run this every night," "generate the report every Monday morning," "remind me to check this again in 30 minutes." Without scheduling, the user has to re-issue the same request every time. This chapter adds one new idea: store future intent now, trigger it later. And it closes out Stage 3 by completing the progression from durable tasks (s12) to background execution (s13) to time-based triggers (s14).

## The Problem

Your agent can now manage a task graph and run commands in the background. But every piece of work begins with the user explicitly asking for it. If the user wants a nightly test run, they have to remember to type "run the tests" every evening. If they want a weekly status report, they have to open a session every Monday morning. The agent has no concept of future time -- it reacts to what you say right now, and it cannot act on something you want to happen tomorrow. You need a way to record "do X at time Y" and have the system trigger it automatically.

## The Solution

Add three moving parts: schedule records that describe when and what, a time checker that runs in the background and tests whether any schedule matches the current time, and the same notification queue from s13 to feed triggered work back into the main loop.

```text
schedule_create(...)
  ->
write a durable schedule record
  ->
time checker wakes up and tests "does this rule match now?"
  ->
if yes, enqueue a scheduled notification
  ->
main loop injects that notification as new work
```

The key insight is that the scheduler is not a second agent loop. It feeds triggered prompts into the same system the agent already uses. The main loop does not know or care whether a piece of work came from the user typing it or from a cron trigger -- it processes both the same way.

## How It Works

**Step 1.** Define the schedule record. Each job stores a cron expression (a compact time-matching syntax like `0 9 * * 1` meaning "9:00 AM every Monday"), the prompt to execute, whether it recurs or fires once, and a `last_fired_at` timestamp to prevent double-firing.

```python
schedule = {
    "id": "job_001",
    "cron": "0 9 * * 1",
    "prompt": "Run the weekly status report.",
    "recurring": True,
    "durable": True,
    "created_at": 1710000000.0,
    "last_fired_at": None,
}
```

A durable job is written to disk and survives process restarts. A session-only job lives in memory and dies when the agent exits. One-shot jobs (`recurring: False`) fire once and then delete themselves.

**Step 2.** Create a schedule through a tool call. The method stores the record and returns it so the model can confirm what was scheduled.

```python
def create(self, cron_expr: str, prompt: str, recurring: bool = True):
    job = {
        "id": new_id(),
        "cron": cron_expr,
        "prompt": prompt,
        "recurring": recurring,
        "created_at": time.time(),
        "last_fired_at": None,
    }
    self.jobs.append(job)
    return job
```

**Step 3.** Run a background checker loop that wakes up every 60 seconds and tests each schedule against the current time.

```python
def check_loop(self):
    while True:
        now = datetime.now()
        self.check_jobs(now)
        time.sleep(60)
```

**Step 4.** When a schedule matches, enqueue a notification. The `last_fired_at` field is updated to prevent the same minute from triggering the job twice.

```python
def check_jobs(self, now):
    for job in self.jobs:
        if cron_matches(job["cron"], now):
            self.queue.put({
                "type": "scheduled_prompt",
                "schedule_id": job["id"],
                "prompt": job["prompt"],
            })
            job["last_fired_at"] = now.timestamp()
```

**Step 5.** Feed scheduled notifications back into the main loop using the same drain pattern from s13. From the agent's perspective, a scheduled prompt looks just like a user message.

```python
notifications = scheduler.drain()
for item in notifications:
    messages.append({
        "role": "user",
        "content": f"[scheduled:{item['schedule_id']}] {item['prompt']}",
    })
```

## Read Together

- If `schedule`, `task`, and `runtime task` still feel like the same object, reread [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) -- it draws the boundary between planning records, execution records, and schedule records.
- If you want to see how one trigger eventually returns to the mainline, pair this chapter with [`s00b-one-request-lifecycle.md`](./s00b-one-request-lifecycle.md).
- If future triggers start to feel like a whole second execution system, reset with [`data-structures.md`](./data-structures.md) and separate schedule records from runtime records.

## What Changed

| Mechanism | Main question |
|---|---|
| Background tasks (s13) | "How does slow work continue without blocking?" |
| Scheduling (s14) | "When should future work begin?" |

| Component | Before (s13) | After (s14) |
|---|---|---|
| Tools | 6 (base + background) | 8 (+ schedule_create, schedule_list, schedule_delete) |
| Time awareness | None | Cron-based future triggers |
| Persistence | Background tasks in memory | Durable schedules survive restarts |
| Trigger model | User-initiated only | User-initiated + time-triggered |

## Try It

```sh
cd learn-claude-code
python agents/s14_cron_scheduler.py
```

1. Create a repeating schedule: `Schedule "echo hello" to run every 2 minutes`
2. Create a one-shot reminder: `Remind me in 1 minute to check the build`
3. Create a delayed follow-up: `In 5 minutes, run the test suite and report results`

## What You've Mastered

At this point, you can:

- Define schedule records that store future intent as durable data
- Run a background time checker that matches cron expressions to the current clock
- Distinguish durable jobs (persist to disk) from session-only jobs (in-memory)
- Feed scheduled triggers back into the main loop through the same notification queue used by background tasks
- Prevent double-firing with `last_fired_at` tracking

## Stage 3 Complete

You have finished Stage 3: the execution and scheduling layer. Looking back at the three chapters together:

- **s12** gave the agent a task graph with dependencies and persistence -- it can plan structured work that survives restarts.
- **s13** added background execution -- slow work runs in parallel instead of blocking the loop.
- **s14** added time-based triggers -- the agent can schedule future work without the user having to remember.

Together, these three chapters transform the agent from something that only reacts to what you type right now into something that can plan ahead, work in parallel, and act on its own schedule. In Stage 4 (s15-s18), you will use this foundation to coordinate multiple agents working as a team.

## Key Takeaway

> A scheduler stores future intent as a record, checks it against the clock in a background loop, and feeds triggered work back into the same agent system -- no second loop needed.
