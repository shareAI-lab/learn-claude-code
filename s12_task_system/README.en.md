# s12: Task System — Break Big Goals into Small Tasks

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

s01 → ... → s10 → s11 → `s12` → [s13](../s13_background_tasks/) → s14 → ... → s20

> *"Break big goals into small tasks, order them, persist"* — File-persisted task graph, the foundation for multi-agent collaboration.
>
> **Harness Layer**: Tasks — Persisted goals, recoverable progress.

---

## The Problem

The agent receives a project: set up a database, write APIs, add tests. It uses s05's TodoWrite to create a checklist, then starts writing the API first, gets halfway through and realizes there are no database tables, goes back to fix them; when adding tests, discovers the API interface signatures have changed again...

You can't build the roof before laying the foundation. Tasks have ordering. Task dependencies should form a Directed Acyclic Graph (DAG); the teaching version only demonstrates `blockedBy` checking, without cycle detection.

s05's TodoWrite is a list. No dependencies, no persistence — when the conversation ends, the list is gone. What you need is a **task system**: each task is a JSON file, tasks have `blockedBy` dependencies, and they persist across sessions on disk.

---

## The Solution

![Task System Overview](images/task-system-overview.en.svg)

Teaching code keeps a basic agent loop, omitting S11's full error recovery (RecoveryState, backoff, escalation, reactive compact, fallback model) to stay focused on the task system. Added: 5 new task tools + `.tasks/` directory for persistence + `blockedBy` dependency checking. The task system and error recovery are independent layers: in CC source, `utils/tasks.ts` only handles CRUD, while `query.ts`'s with_retry/RecoveryState handles error recovery, with no coupling between them.

TodoWrite vs Task System:

| | TodoWrite (s05) | Task System (s12) |
|---|---|---|
| Storage | In-memory list | `.tasks/` JSON files |
| Dependencies | None | `blockedBy` dependency graph |
| Persistence | Lost when conversation ends | Cross-session |
| Multi-agent | None | `owner` field |
| Status | checked / unchecked | pending → in_progress → completed |

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
    owner: str | None    # Agent name (multi-agent scenarios)
    blockedBy: list[str] # List of dependency task IDs
```

IDs are generated with `timestamp + random hex`, simple but sufficient. CC uses sequential IDs + a highwatermark file to prevent ID reuse, which is a more rigorous design.

### create_task: Create Tasks

```python
def create_task(subject: str, description: str = "",
                blockedBy: list[str] | None = None) -> Task:
    task = Task(
        id=f"task_{int(time.time())}_{random_hex(4)}",
        subject=subject, description=description,
        status="pending", owner=None,
        blockedBy=blockedBy or [],
    )
    save_task(task)
    return task
```

Automatically calls `save_task` on creation to write `.tasks/{id}.json`. `blockedBy` declares dependencies, for example "write API" has `blockedBy: ["task_schema"]`.

### can_start: Dependency Check

A task can only start after all its `blockedBy` dependencies are **completed**:

```python
def can_start(task_id: str) -> bool:
    task = load_task(task_id)
    for dep_id in task.blockedBy:
        if not _task_path(dep_id).exists():
            return False  # missing dependency = blocked
        dep = load_task(dep_id)
        if dep.status != "completed":
            return False
    return True
```

`can_start` is a prerequisite check for `claim_task`: if any `blockedBy` dependency is not completed, the task cannot be claimed. Missing dependencies are treated as blocked, avoiding crashes from referencing wrong IDs.

### claim_task: Claim a Task

When the agent starts working on a task, it calls `claim_task`: sets `owner`, changes status from `pending` → `in_progress`. The `owner` field records who is working on the task, preventing duplicate claims in multi-agent scenarios:

```python
def claim_task(task_id: str, owner: str = "agent") -> str:
    task = load_task(task_id)
    if task.status != "pending":
        return f"Task {task_id} is {task.status}, cannot claim"
    if not can_start(task_id):
        deps = [d for d in task.blockedBy
                if load_task(d).status != "completed"]
        return f"Blocked by: {deps}"
    task.owner = owner
    task.status = "in_progress"
    save_task(task)
    return f"Claimed {task_id} ({task.subject})"
```

If the task is already claimed by someone else (`status != "pending"`), or dependencies aren't met (`can_start` returns False), the claim is rejected.

### complete_task: Complete and Unblock

When a task is done, set it to `completed`. Simultaneously scan all other tasks to find downstream tasks that were **just unblocked**:

```python
def complete_task(task_id: str) -> str:
    task = load_task(task_id)
    task.status = "completed"
    save_task(task)
    # Find newly unblocked downstream tasks
    unblocked = [t.subject for t in list_tasks()
                 if t.status == "pending" and t.blockedBy
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

CC has no `in_progress → pending` release path. If a teammate terminates or shuts down, CC unassigns its unfinished tasks (clears owner) and resets status to `pending`, allowing other agents to reclaim them. The teaching version omits this recovery path.

### Putting It Together

```python
# Create tasks with dependencies
schema = create_task("setup database schema")
endpoints = create_task("create API endpoints", blockedBy=[schema.id])
tests = create_task("write tests", blockedBy=[endpoints.id])
docs = create_task("write docs", blockedBy=[schema.id])

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

Each `create_task` writes a JSON file, each `claim_task` / `complete_task` updates the file. Across sessions, the `.tasks/` directory persists — the agent reads the files to recover progress.

---

## Changes from s11

| Component | Before (s11) | After (s12) |
|-----------|-------------|-------------|
| Task management | None | Task dataclass + 5 tools |
| New types | — | Task (id, subject, description, status, owner, blockedBy) |
| Storage | No persistence | `.tasks/{id}.json` cross-session |
| Dependencies | None | `blockedBy` graph + `can_start` check |
| Tools | bash, read_file, write_file (3) | + create_task, list_tasks, get_task, claim_task, complete_task (8) |
| Lifecycle | — | pending → in_progress → completed (no release rollback) |

---

## Try It

```sh
cd learn-claude-code
python s12_task_system/code.py
```

Try these prompts:

1. `Create tasks: setup database schema, create API endpoints (depends on schema), write tests (depends on endpoints), write docs (depends on schema)`
2. `List all tasks and their statuses`
3. `Claim the first unblocked task and complete it`
4. `List tasks again — which ones are now unblocked?`

What to observe: Are JSON files generated in the `.tasks/` directory? After completing a task, are the blocked tasks unblocked?

---

## What's Next

The task graph is in place. But some tasks take a long time — like running full test suites or deploying to a server. The agent calls the LLM billed by token, it can't afford to wait on a slow operation.

s13 Background Tasks → Slow operations go to the background. The agent continues processing other tasks, and gets notified when the background work is done.

<details>
<summary>Deep Dive into CC Source</summary>

> The following is a complete analysis based on CC source code `utils/tasks.ts` (862 lines), `tools/TaskCreateTool/TaskCreateTool.ts` (138 lines), `tools/TaskUpdateTool/TaskUpdateTool.ts` (406 lines), `tools/TaskGetTool/TaskGetTool.ts` (128 lines), `tools/TaskListTool/TaskListTool.ts` (116 lines), `hooks/useTaskListWatcher.ts` (221 lines).

### 1. TaskRecord's Full Fields

The tutorial only covers id, subject, status, owner, blockedBy. CC actually has 9 fields (`utils/tasks.ts:76-89`):

| Field | Type | Purpose |
|------|------|---------|
| `id` | string | Incrementing integer ID |
| `subject` | string | Short title |
| `description` | string | Free-form description |
| `activeForm` | string? | Present tense form, shown in spinner when in_progress |
| `owner` | string? | Assigned agent ID |
| `status` | pending/in_progress/completed | Lifecycle |
| `blocks` | string[] | Task IDs blocked by this task (downstream) |
| `blockedBy` | string[] | Task IDs blocking this task (upstream) |
| `metadata` | Record? | Arbitrary extension key-value pairs |

Storage location: `~/.claude/tasks/{taskListId}/{id}.json`. One file per task.

### 2. Not a TodoWrite Upgrade — Two Independent Systems

In CC, Task System and TodoWrite **coexist**, toggled by `isTodoV2Enabled()` (`utils/tasks.ts:133`) — interactive sessions default to Task (V2), non-interactive/SDK sessions default to TodoWrite. The `CLAUDE_CODE_ENABLE_TASKS` env var can force-enable Task. Task has what TodoWrite lacks: file-lock concurrency protection, dependency enforcement, ownership, fs.watch reactive monitoring, lifecycle hooks.

### 3. Concurrent Claim Locking

`claimTask()` (`utils/tasks.ts:541-612`) uses dual locking to prevent races:

**Task file lock**: `proper-lockfile` locks `{taskId}.json` (up to 30 retries, exponential backoff 5-100ms). Inside the lock:
1. Re-read task (prevent TOCTOU)
2. Check already claimed by another → `already_claimed`
3. Check already completed → `already_resolved`
4. Check upstream not completed → `blocked`
5. Set owner

**List-level lock** (agent busy check): `.lock` file, atomic scan of all tasks to check if the agent already has other open tasks.

Note: The teaching version combines claiming and starting work into one step (claim = set owner + in_progress); real CC's `claimTask` primarily resolves owner competition — it only sets owner without changing status. Status updates are handled by `TaskUpdate`.

### 4. High-Water Mark to Prevent ID Reuse

The `.highwatermark` file records the highest task ID ever assigned. Even if a task is deleted, its ID won't be reused.

### 5. Four Task Tools

CC's task system has four tools (not the tutorial's single generic Task tool): `TaskCreate`, `TaskGet`, `TaskUpdate`, `TaskList`. All set `isConcurrencySafe: true` and `shouldDefer: true` (tool schemas aren't in the initial prompt; only visible after ToolSearch).

The teaching version's `create_task(blockedBy=...)` declares dependencies at creation time, which is a reasonable simplification. Real CC's `TaskCreate` only accepts subject/description/activeForm/metadata — dependencies are maintained via `TaskUpdate`'s `addBlocks/addBlockedBy`.

</details>

<!-- translation-sync: zh@v1, en@v1, ja@v1 -->
