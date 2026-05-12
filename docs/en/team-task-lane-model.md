# Team Task Lane Model

> **Deep Dive** -- Best read at the start of Stage 4 (s15-s18). It separates five concepts that look similar but live on different layers.

### When to Read This

Before you start the team chapters. Keep it open as a reference during s15-s18.

---

> By the time you reach `s15-s18`, the easiest thing to blur is not a function name.
>
> It is this:
>
> **Who is working, who is coordinating, what records the goal, and what provides the execution lane.**

## What This Bridge Doc Fixes

Across `s15-s18`, you will encounter these words that can easily blur into one vague idea:

- teammate
- protocol request
- task
- runtime task
- worktree

They all relate to work getting done, but they do **not** live on the same layer.

If you do not separate them, the later chapters start to feel tangled:

- Is a teammate the same thing as a task?
- What is the difference between `request_id` and `task_id`?
- Is a worktree just another runtime task?
- Why can a task be complete while a worktree is still kept?

This document exists to separate those layers cleanly.

## Recommended Reading Order

1. Read [`s15-agent-teams.md`](./s15-agent-teams.md) for long-lived teammates.
2. Read [`s16-team-protocols.md`](./s16-team-protocols.md) for tracked request-response coordination.
3. Read [`s17-autonomous-agents.md`](./s17-autonomous-agents.md) for self-claiming teammates.
4. Read [`s18-worktree-task-isolation.md`](./s18-worktree-task-isolation.md) for isolated execution lanes.

If the vocabulary starts to blur, you might find it helpful to revisit:

- [`entity-map.md`](./entity-map.md)
- [`data-structures.md`](./data-structures.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

## The Core Separation

```text
teammate
  = who participates over time

protocol request
  = one tracked coordination request inside the team

task
  = what should be done

runtime task / execution slot
  = what is actively running right now

worktree
  = where the work executes without colliding with other lanes
```

The most common confusion is between the last three:

- `task`
- `runtime task`
- `worktree`

Ask three separate questions every time:

- Is this the goal?
- Is this the running execution unit?
- Is this the isolated execution directory?

## The Smallest Clean Diagram

```text
Team Layer
  teammate: alice (frontend)

Protocol Layer
  request_id=req_01
  kind=plan_approval
  status=pending

Work Graph Layer
  task_id=12
  subject="Implement login page"
  owner="alice"
  status="in_progress"

Runtime Layer
  runtime_id=rt_01
  type=in_process_teammate
  status=running

Execution Lane Layer
  worktree=login-page
  path=.worktrees/login-page
  status=active
```

Only one of those records the work goal itself:

> `task_id=12`

The others support coordination, execution, or isolation around that goal.

## 1. Teammate: Who Is Collaborating

Introduced in `s15`.

This layer answers:

- what the long-lived worker is called
- what role it has
- whether it is `working`, `idle`, or `shutdown`
- whether it has its own inbox

Example:

```python
member = {
    "name": "alice",
    "role": "frontend",
    "status": "idle",
}
```

The point is not "another agent instance."

The point is:

> a persistent identity that can repeatedly receive work.

## 2. Protocol Request: What Is Being Coordinated

Introduced in `s16`.

This layer answers:

- who asked whom
- what kind of request this is
- whether it is still pending or already resolved

Example:

```python
request = {
    "request_id": "a1b2c3d4",
    "kind": "plan_approval",
    "from": "alice",
    "to": "lead",
    "status": "pending",
}
```

This is not ordinary chat.

It is:

> a coordination record whose state can continue to evolve.

## 3. Task: What Should Be Done

This is the durable work-graph task from `s12`, and it is what `s17` teammates claim.

It answers:

- what the goal is
- who owns it
- what blocks it
- what progress state it is in

Example:

```python
task = {
    "id": 12,
    "subject": "Implement login page",
    "status": "in_progress",
    "owner": "alice",
    "blockedBy": [],
}
```

Keyword:

**goal**

Not directory. Not protocol. Not process.

## 4. Runtime Task / Execution Slot: What Is Running

This layer was already clarified in the `s13a` bridge doc, but it matters even more in `s15-s18`.

Examples:

- a background shell command
- a long-lived teammate currently working
- a monitor process watching an external state

These are best understood as:

> active execution slots

Example:

```python
runtime = {
    "id": "rt_01",
    "type": "in_process_teammate",
    "status": "running",
    "work_graph_task_id": 12,
}
```

Important boundary:

- one work-graph task may spawn multiple runtime tasks
- a runtime task is an execution instance, not the durable goal itself

## 5. Worktree: Where the Work Happens

Introduced in `s18`.

This layer answers:

- which isolated directory is used
- which task it is bound to
- whether that lane is `active`, `kept`, or `removed`

Example:

```python
worktree = {
    "name": "login-page",
    "path": ".worktrees/login-page",
    "task_id": 12,
    "status": "active",
}
```

Keyword:

**execution boundary**

It is not the task goal itself. It is the isolated lane where that goal is executed.

## How The Layers Connect

```text
teammate
  coordinates through protocol requests
  claims a task
  runs as an execution slot
  works inside a worktree lane
```

In a more concrete sentence:

> `alice` claims `task #12` and progresses it inside the `login-page` worktree lane.

That sentence is much cleaner than saying:

> "alice is doing the login-page worktree task"

because the shorter sentence incorrectly merges:

- the teammate
- the task
- the worktree

## Common Mistakes

### 1. Treating teammate and task as the same object

The teammate executes. The task expresses the goal.

### 2. Treating `request_id` and `task_id` as interchangeable

One tracks coordination. The other tracks work goals.

### 3. Treating the runtime slot as the durable task

The running execution may end while the durable task still exists.

### 4. Treating the worktree as the task itself

The worktree is only the execution lane.

### 5. Saying "the system works in parallel" without naming the layers

Good teaching does not stop at "there are many agents."

It can say clearly:

> teammates provide long-lived collaboration, requests track coordination, tasks record goals, runtime slots carry execution, and worktrees isolate the execution directory.

## What You Should Be Able to Say After Reading This

1. `s17` autonomy claims `s12` work-graph tasks, not `s13` runtime slots.
2. `s18` worktrees bind execution lanes to tasks; they do not turn tasks into directories.
3. A teammate can be idle while the task still exists and while the worktree is still kept.
4. A protocol request tracks a coordination exchange, not a work goal.

## Key Takeaway

**Five things that sound alike -- teammate, protocol request, task, runtime slot, worktree -- live on five separate layers. Naming which layer you mean is how you keep the team chapters from collapsing into confusion.**
