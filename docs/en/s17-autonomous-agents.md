# s17: Autonomous Agents

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > [ s17 ] > s18 > s19`

## What You'll Learn
- How idle polling lets a teammate find new work without being told
- How auto-claim turns the task board into a self-service work queue
- How identity re-injection restores a teammate's sense of self after context compression
- How a timeout-based shutdown prevents idle agents from running forever

Manual assignment does not scale. With ten unclaimed tasks on the board, the lead has to pick one, find an idle teammate, craft a prompt, and hand it off -- ten times. The lead becomes a bottleneck, spending more time dispatching than thinking. In this chapter you will remove that bottleneck by making teammates autonomous: they scan the task board themselves, claim unclaimed work, and shut down gracefully when there is nothing left to do.

## The Problem

In s15-s16, teammates only work when explicitly told to. The lead must spawn each one with a specific prompt. If ten tasks sit unclaimed on the board, the lead assigns each one manually. This creates a coordination bottleneck that gets worse as the team grows.

True autonomy means teammates scan the task board themselves, claim unclaimed tasks, work on them, then look for more -- all without the lead lifting a finger.

One subtlety makes this harder than it sounds: after context compression (which you built in s06), an agent's conversation history gets truncated. The agent might forget who it is. Identity re-injection fixes this by restoring the agent's name and role when its context gets too short.

## The Solution

Each teammate alternates between two phases: WORK (calling the LLM and executing tools) and IDLE (polling for new messages or unclaimed tasks). If the idle phase times out with nothing to do, the teammate shuts itself down.

```
Teammate lifecycle with idle cycle:

+-------+
| spawn |
+---+---+
    |
    v
+-------+   tool_use     +-------+
| WORK  | <------------- |  LLM  |
+---+---+                +-------+
    |
    | stop_reason != tool_use (or idle tool called)
    v
+--------+
|  IDLE  |  poll every 5s for up to 60s
+---+----+
    |
    +---> check inbox --> message? ----------> WORK
    |
    +---> scan .tasks/ --> unclaimed? -------> claim -> WORK
    |
    +---> 60s timeout ----------------------> SHUTDOWN

Identity re-injection after compression:
  if len(messages) <= 3:
    messages.insert(0, identity_block)
```

## How It Works

**Step 1.** The teammate loop has two phases: WORK and IDLE. During the work phase, the teammate calls the LLM repeatedly and executes tools. When the LLM stops calling tools (or the teammate explicitly calls the `idle` tool), it transitions to the idle phase.

```python
def _loop(self, name, role, prompt):
    while True:
        # -- WORK PHASE --
        messages = [{"role": "user", "content": prompt}]
        for _ in range(50):
            response = client.messages.create(...)
            if response.stop_reason != "tool_use":
                break
            # execute tools...
            if idle_requested:
                break

        # -- IDLE PHASE --
        self._set_status(name, "idle")
        resume = self._idle_poll(name, messages)
        if not resume:
            self._set_status(name, "shutdown")
            return
        self._set_status(name, "working")
```

**Step 2.** The idle phase polls for two things in a loop: inbox messages and unclaimed tasks. It checks every 5 seconds for up to 60 seconds. If a message arrives, the teammate wakes up. If an unclaimed task appears on the board, the teammate claims it and gets back to work. If neither happens within the timeout window, the teammate shuts itself down.

```python
def _idle_poll(self, name, messages):
    for _ in range(IDLE_TIMEOUT // POLL_INTERVAL):  # 60s / 5s = 12
        time.sleep(POLL_INTERVAL)
        inbox = BUS.read_inbox(name)
        if inbox:
            messages.append({"role": "user",
                "content": f"<inbox>{inbox}</inbox>"})
            return True
        unclaimed = scan_unclaimed_tasks()
        if unclaimed:
            claim_task(unclaimed[0]["id"], name)
            messages.append({"role": "user",
                "content": f"<auto-claimed>Task #{unclaimed[0]['id']}: "
                           f"{unclaimed[0]['subject']}</auto-claimed>"})
            return True
    return False  # timeout -> shutdown
```

**Step 3.** Task board scanning finds pending, unowned, unblocked tasks. The scan reads task files from disk and filters for tasks that are available to claim -- no owner, no blocking dependencies, and still in `pending` status.

```python
def scan_unclaimed_tasks() -> list:
    unclaimed = []
    for f in sorted(TASKS_DIR.glob("task_*.json")):
        task = json.loads(f.read_text())
        if (task.get("status") == "pending"
                and not task.get("owner")
                and not task.get("blockedBy")):
            unclaimed.append(task)
    return unclaimed
```

**Step 4.** Identity re-injection handles a subtle problem. After context compression (s06), the conversation history might shrink to just a few messages -- and the agent forgets who it is. When the message list is suspiciously short (3 or fewer messages), the harness inserts an identity block at the beginning so the agent knows its name, role, and team.

```python
if len(messages) <= 3:
    messages.insert(0, {"role": "user",
        "content": f"<identity>You are '{name}', role: {role}, "
                   f"team: {team_name}. Continue your work.</identity>"})
    messages.insert(1, {"role": "assistant",
        "content": f"I am {name}. Continuing."})
```

## Read Together

- If teammate, task, and runtime slot are starting to blur into one layer, revisit [`team-task-lane-model.md`](./team-task-lane-model.md) to separate them clearly.
- If auto-claim makes you wonder where the live execution slot actually lives, keep [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) nearby.
- If you are starting to forget the core difference between a persistent teammate and a one-shot subagent, revisit [`entity-map.md`](./entity-map.md).

## What Changed From s16

| Component      | Before (s16)     | After (s17)                |
|----------------|------------------|----------------------------|
| Tools          | 12               | 14 (+idle, +claim_task)    |
| Autonomy       | Lead-directed    | Self-organizing            |
| Idle phase     | None             | Poll inbox + task board    |
| Task claiming  | Manual only      | Auto-claim unclaimed tasks |
| Identity       | System prompt    | + re-injection after compress|
| Timeout        | None             | 60s idle -> auto shutdown  |

## Try It

```sh
cd learn-claude-code
python agents/s17_autonomous_agents.py
```

1. `Create 3 tasks on the board, then spawn alice and bob. Watch them auto-claim.`
2. `Spawn a coder teammate and let it find work from the task board itself`
3. `Create tasks with dependencies. Watch teammates respect the blocked order.`
4. Type `/tasks` to see the task board with owners
5. Type `/team` to monitor who is working vs idle

## What You've Mastered

At this point, you can:

- Build teammates that find and claim work from a shared task board without lead intervention
- Implement an idle polling loop that balances responsiveness with resource efficiency
- Restore agent identity after context compression so long-running teammates stay coherent
- Use timeout-based shutdown to prevent abandoned agents from running indefinitely

## What's Next

Your teammates now organize themselves, but they all share the same working directory. When two agents edit the same file at the same time, things break. In s18, you will give each teammate its own isolated worktree -- a separate copy of the codebase where it can work without stepping on anyone else's changes.

## Key Takeaway

> Autonomous teammates scan the task board, claim unclaimed work, and shut down when idle -- removing the lead as a coordination bottleneck.
