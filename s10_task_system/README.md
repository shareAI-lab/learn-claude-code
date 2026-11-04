# s10: Task System — From an Execution Checklist to Coordinated Task State

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → s08 → s09 → `s10` → [s11](../s11_background_tasks/) → s12 → ... → s16 → s17

> *"Break big goals into small tasks, order them, persist"* — File-persisted task graph, the foundation for multi-agent collaboration.
>
> **Harness Layer**: Tasks — Persisted goals, recoverable progress.

---

## The Problem

s05's TodoWrite lets an agent record the steps of its current task. Each checklist item has content and a status, helping the agent keep track of what remains.

When a project is split into three tasks—creating database tables, writing an API, and adding tests—the Harness also needs to know how they relate: the API must wait for the database tables, and the tests must wait for a stable API. It also needs to record who is responsible for each task.

TodoWrite does not record these dependencies or assignments. It can show that "write the API" is unfinished, but the Harness cannot use that information to decide whether the task is ready to start.

This chapter adds a Task System. Each task has its own ID and status; `blockedBy` records prerequisites, and `owner` records the agent responsible for the task.

---

## The Solution

![Task System Overview](images/task-system-overview.en.svg)

The code keeps S04's five base tools, Permission, Hooks, and shared `execute_tool`, then adds 6 task tools, persistence in the `.tasks/` directory, and `blockedBy` dependency checks.

TodoWrite vs Task System:

| | TodoWrite (s05) | Task System (s10) |
|---|---|---|
| Role | Execution checklist for the current task | Recoverable task system |
| Storage | In-process / session state | `.tasks/{id}.json` |
| Dependencies | None | `blockedBy` dependency graph |
| Lifecycle | Current session / current task | Cross-session |
| Coordination | No task claiming | `owner` / claim |
| Status | pending / in_progress / completed | pending / in_progress / completed |
| Granularity | The agent's own steps | Tasks that can be claimed, tracked, and unblocked |
| Update contract | Replace the whole checklist | Create/get/update/list individual records |

---

## How It Works

![Task DAG](images/task-dag.en.svg)

### Task: Data Structure

Each task is a JSON file, stored in the `.tasks/` directory:

```python
@dataclass
class Task:
    id: str
    subject: str
    description: str
    status: str          # pending | in_progress | completed
    owner: str | None    # Agent responsible for this task
    blockedBy: list[str] # List of dependency task IDs
```

IDs use the `task_` prefix followed by 8 random hexadecimal characters. Files are created exclusively; an existing ID is discarded and regenerated.

`TaskStore` validates task IDs and reads and writes the JSON files. `TASKS = TaskStore(TASKS_DIR)` is the store used by this chapter.

### create_task: Create Tasks

```python
def create_task(subject: str, description: str = "") -> Task:
    return TASKS.create(subject, description)
```

`TaskStore.create` checks the subject, allocates a random ID, and writes `.tasks/{id}.json`. A new task always starts with an empty `blockedBy` list. The tool result returns the runtime-generated ID to the model.

### update_task: Add Dependencies with Returned IDs

```python
def update_task(task_id: str, addBlockedBy: list[str]) -> Task:
    return TASKS.update_dependencies(task_id, addBlockedBy)
```

Task graph construction uses two phases: create every node first, then call `update_task` with the IDs returned by `create_task` to add edges. This matters when the model emits several tool calls in one response: sibling calls are formed before any tool result exists, so one `create_task` call cannot consume another call's newly generated ID.

`update_task` validates the entire change before saving it. The target and dependencies must exist, the target must still be pending and unowned, and the new edges must not introduce self-dependencies or cycles. Repeating an existing edge is safe and does not duplicate it.

### can_start: Dependency Check

A task can only start after all its `blockedBy` dependencies are **completed**:

```python
def can_start(task_id: str) -> bool:
    return not incomplete_dependencies(load_task(task_id))
```

`incomplete_dependencies` loads each prerequisite. A task cannot be claimed if any prerequisite is not completed or its file no longer exists.

### claim_task: Claim a Task

When the agent starts working on a task, it calls `claim_task`: sets `owner`, changes status from `pending` → `in_progress`. The `owner` field records who claimed the task:

```python
def claim_task(task_id: str, owner: str = "agent") -> str:
    task = load_task(task_id)
    if task.status != "pending":
        return f"Task {task_id} is {task.status}, cannot claim"
    dependencies = incomplete_dependencies(task)
    if dependencies:
        return f"Blocked by: {dependencies}"
    task.owner = owner
    task.status = "in_progress"
    TASKS.save(task)
    return f"Claimed {task_id} ({task.subject})"
```

The claim is rejected if the task is not pending or its dependencies are incomplete. S10 only updates task state sequentially.

### complete_task: Complete and Unblock

When a task is done, set it to `completed`. Simultaneously scan all other tasks to find downstream tasks that were **just unblocked**:

```python
def complete_task(task_id: str, owner: str = "agent") -> str:
    task = load_task(task_id)
    if task.status != "in_progress":
        return f"Task {task_id} is {task.status}, cannot complete"
    if task.owner != owner:
        return f"Task {task_id} is owned by {task.owner}, not {owner}"
    ready_before = {t.id for t in list_tasks()
                    if t.status == "pending" and t.blockedBy
                    and can_start(t.id)}
    task.status = "completed"
    TASKS.save(task)
    unblocked = [t.subject for t in list_tasks()
                 if t.status == "pending" and t.blockedBy
                 and t.id not in ready_before
                 and can_start(t.id)]
    msg = f"Completed {task_id} ({task.subject})"
    if unblocked:
        msg += f"\nUnblocked: {', '.join(unblocked)}"
    return msg
```

After completing "schema", `can_start` returns True for "endpoints" and "docs"; they can begin.

### get_task: View Full Details

`list_tasks` only shows a one-line summary. `get_task` returns the full task JSON, including description and dependency details. When recovering across sessions, the agent needs to read the full description to continue work:

```python
def get_task(task_id: str) -> str:
    task = load_task(task_id)
    return json.dumps(asdict(task), indent=2)
```

### State Machine: Two Actions, Three States

```
pending ──claim──→ in_progress ──complete──→ completed
```

Here `claim` / `complete` are actions, while `pending` / `in_progress` / `completed` are states:

- **claim_task**: `pending` → `in_progress`. Sets owner, begins work.
- **complete_task**: `in_progress` → `completed`. Marks the task done and unblocks downstream.

### Putting It Together

```python
# Phase 1: create every node and receive its runtime ID
schema = create_task("setup database schema")
endpoints = create_task("create API endpoints")
tests = create_task("write tests")
docs = create_task("write docs")

# Phase 2: add edges using those returned IDs
update_task(endpoints.id, addBlockedBy=[schema.id])
update_task(tests.id, addBlockedBy=[endpoints.id])
update_task(docs.id, addBlockedBy=[schema.id])

# Agent claims the first available task
claim_task(schema.id)       # ✓ Claimed (no dependencies)
complete_task(schema.id)    # ✓ Completed → unblocks endpoints, docs

claim_task(endpoints.id)    # ✓ Claimed (schema completed)
complete_task(endpoints.id) # ✓ Completed → unblocks tests

claim_task(docs.id)         # ✓ Claimed (schema completed)
complete_task(docs.id)      # ✓ Completed

claim_task(tests.id)        # ✓ Claimed (endpoints completed)
complete_task(tests.id)     # ✓ Completed
```

Each `create_task` writes a JSON file; `update_task`, `claim_task`, and `complete_task` update it. Across sessions, the `.tasks/` directory persists — the agent reads the files to recover progress.

---

## Try It

```sh
cd learn-claude-code
python s10_task_system/code.py
```

Try these prompts:

1. `Create tasks: setup database schema, create API endpoints (depends on schema), write tests (depends on endpoints), write docs (depends on schema)`
2. `List all tasks and their statuses`
3. `Claim the first unblocked task and complete it`
4. `List tasks again — which ones are now unblocked?`

What to observe: Are JSON files generated in the `.tasks/` directory? After completing a task, are the blocked tasks unblocked?

---

## What's Next

The task graph is in place, but full test suites, dependency installation, and deployment commands can take a long time. When these commands run synchronously, the Agent Loop remains blocked in the current tool call and cannot continue until the command finishes.

s11 Background Tasks → Slow operations run in the background. The Agent Loop can continue processing other tasks and receives a notification when the background work finishes.


<!-- translation-sync: zh@v5, en@v5, ja@v5 -->
