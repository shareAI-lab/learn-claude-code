# s13a: Runtime Task Model

> **Deep Dive** -- Best read between s12 and s13. It prevents the most common confusion in Stage 3.

### When to Read This

Right after s12 (Task System), before you start s13 (Background Tasks). This note separates two meanings of "task" that beginners frequently collapse into one.

---

> This bridge note resolves one confusion that becomes expensive very quickly:
>
> **the task in the work graph is not the same thing as the task that is currently running**

## How to Read This with the Mainline

This note works best between these documents:

- read [`s12-task-system.md`](./s12-task-system.md) first to lock in the durable work graph
- then read [`s13-background-tasks.md`](./s13-background-tasks.md) to see background execution
- if the terms begin to blur, you might find it helpful to revisit [`glossary.md`](./glossary.md)
- if you want the fields to line up exactly, you might find it helpful to revisit [`data-structures.md`](./data-structures.md) and [`entity-map.md`](./entity-map.md)

## Why This Deserves Its Own Bridge Note

The mainline is still correct:

- `s12` teaches the task system
- `s13` teaches background tasks

But without one more bridge layer, you can easily start collapsing two different meanings of "task" into one bucket.

For example:

- a work-graph task such as "implement auth module"
- a background execution such as "run pytest"
- a teammate execution such as "alice is editing files"

All three can be casually called tasks, but they do not live on the same layer.

## Two Very Different Kinds of Task

### 1. Work-graph task

This is the durable node introduced in `s12`.

It answers:

- what should be done
- which work depends on which other work
- who owns it
- what the progress status is

It is best understood as:

> a durable unit of planned work

### 2. Runtime task

This layer answers:

- what execution unit is alive right now
- what kind of execution it is
- whether it is running, completed, failed, or killed
- where its output lives

It is best understood as:

> a live execution slot inside the runtime

## The Minimum Mental Model

Treat these as two separate tables:

```text
work-graph task
  - durable
  - goal and dependency oriented
  - longer lifecycle

runtime task
  - execution oriented
  - output and status oriented
  - shorter lifecycle
```

Their relationship is not "pick one."

It is:

```text
one work-graph task
  can spawn
one or more runtime tasks
```

For example:

```text
work-graph task:
  "Implement auth module"

runtime tasks:
  1. run tests in the background
  2. launch a coder teammate
  3. monitor an external service
```

## Why the Distinction Matters

If you do not keep these layers separate, the later chapters start tangling together:

- `s13` background execution blurs into the `s12` task board
- `s15-s17` teammate work has nowhere clean to attach
- `s18` worktrees become unclear because you no longer know what layer they belong to

The shortest correct summary is:

**work-graph tasks manage goals; runtime tasks manage execution**

## Core Records

### 1. `WorkGraphTaskRecord`

This is the durable task from `s12`.

```python
task = {
    "id": 12,
    "subject": "Implement auth module",
    "status": "in_progress",
    "blockedBy": [],
    "blocks": [13],
    "owner": "alice",
    "worktree": "auth-refactor",
}
```

### 2. `RuntimeTaskState`

A minimal teaching shape can look like this:

```python
runtime_task = {
    "id": "b8k2m1qz",
    "type": "local_bash",
    "status": "running",
    "description": "Run pytest",
    "start_time": 1710000000.0,
    "end_time": None,
    "output_file": ".task_outputs/b8k2m1qz.txt",
    "notified": False,
}
```

The key fields are:

- `type`: what execution unit this is
- `status`: whether it is active or terminal
- `output_file`: where the result is stored
- `notified`: whether the system already surfaced the result

### 3. `RuntimeTaskType`

You do not need to implement every type in the teaching repo immediately.

But you should still know that runtime task is a family, not just one shell command type.

A minimal table:

```text
local_bash
local_agent
remote_agent
in_process_teammate
monitor
workflow
```

## Minimum Implementation Steps

### Step 1: keep the `s12` task board intact

Do not overload it.

### Step 2: add a separate runtime task manager

```python
class RuntimeTaskManager:
    def __init__(self):
        self.tasks = {}
```

### Step 3: create runtime tasks when background work starts

```python
def spawn_bash_task(command: str):
    task_id = new_runtime_id()
    runtime_tasks[task_id] = {
        "id": task_id,
        "type": "local_bash",
        "status": "running",
        "description": command,
    }
```

### Step 4: optionally link runtime execution back to the work graph

```python
runtime_tasks[task_id]["work_graph_task_id"] = 12
```

You do not need that field on day one, but it becomes increasingly important once the system reaches teams and worktrees.

## The Picture You Should Hold

```text
Work Graph
  task #12: Implement auth module
        |
        +-- runtime task A: local_bash (pytest)
        +-- runtime task B: local_agent (coder worker)
        +-- runtime task C: monitor (watch service status)

Runtime Task Layer
  A/B/C each have:
  - their own runtime ID
  - their own status
  - their own output
  - their own lifecycle
```

## How This Connects to Later Chapters

Once this layer is clear, the rest of the runtime and platform chapters become much easier:

- `s13` background commands are runtime tasks
- `s15-s17` teammates can also be understood as runtime task variants
- `s18` worktrees mostly bind to durable work, but still affect runtime execution
- `s19` some monitoring or async external work can also land in the runtime layer

Whenever you see "something is alive in the background and advancing work," ask two questions:

- is this a durable goal from the work graph?
- or is this a live execution slot in the runtime?

## Common Beginner Mistakes

### 1. Putting background shell state directly into the task board

That mixes durable task state and runtime execution state.

### 2. Assuming one work-graph task can only have one runtime task

In real systems, one goal often spawns multiple execution units.

### 3. Reusing the same status vocabulary for both layers

For example:

- durable tasks: `pending / in_progress / completed`
- runtime tasks: `running / completed / failed / killed`

Those should stay distinct when possible.

### 4. Ignoring runtime-only fields such as `output_file` and `notified`

The durable task board does not care much about them.
The runtime layer cares a lot.

## Key Takeaway

**"Task" means two different things: a durable goal in the work graph (what should be done) and a live execution slot in the runtime (what is running right now). Keep them on separate layers.**
