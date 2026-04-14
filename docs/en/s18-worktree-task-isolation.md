# s18: Worktree + Task Isolation

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > [ s18 ] > s19`

## What You'll Learn
- How git worktrees (isolated copies of your project directory, managed by git) prevent file conflicts between parallel agents
- How to bind a task to a dedicated worktree so that "what to do" and "where to do it" stay cleanly separated
- How lifecycle events give you an observable record of every create, keep, and remove action
- How parallel execution lanes let multiple agents work on different tasks without ever stepping on each other's files

When two agents both need to edit the same codebase at the same time, you have a problem. Everything you have built so far -- task boards, autonomous agents, team protocols -- assumes that agents work in a single shared directory. That works fine until it does not. This chapter gives every task its own directory, so parallel work stays parallel.

## The Problem

By s17, your agents can claim tasks, coordinate through team protocols, and complete work autonomously. But all of them run in the same project directory. Imagine agent A is refactoring the authentication module, and agent B is building a new login page. Both need to touch `config.py`. Agent A stages its changes, agent B stages different changes to the same file, and now you have a tangled mess of unstaged edits that neither agent can roll back cleanly.

The task board tracks *what to do* but has no opinion about *where to do it*. You need a way to give each task its own isolated working directory, so that file-level operations never collide. The fix is straightforward: pair each task with a git worktree -- a separate checkout of the same repository on its own branch. Tasks manage goals; worktrees manage execution context. Bind them by task ID.

## Read Together

- If task, runtime slot, and worktree lane are blurring together in your head, [`team-task-lane-model.md`](./team-task-lane-model.md) separates them clearly.
- If you want to confirm which fields belong on task records versus worktree records, [`data-structures.md`](./data-structures.md) has the full schema.
- If you want to see why this chapter comes after tasks and teams in the overall curriculum, [`s00e-reference-module-map.md`](./s00e-reference-module-map.md) has the ordering rationale.

## The Solution

The system splits into two planes: a control plane (`.tasks/`) that tracks goals, and an execution plane (`.worktrees/`) that manages isolated directories. Each task points to its worktree by name, and each worktree points back to its task by ID.

```
Control plane (.tasks/)             Execution plane (.worktrees/)
+------------------+                +------------------------+
| task_1.json      |                | auth-refactor/         |
|   status: in_progress  <------>   branch: wt/auth-refactor
|   worktree: "auth-refactor"   |   task_id: 1             |
+------------------+                +------------------------+
| task_2.json      |                | ui-login/              |
|   status: pending    <------>     branch: wt/ui-login
|   worktree: "ui-login"       |   task_id: 2             |
+------------------+                +------------------------+
                                    |
                          index.json (worktree registry)
                          events.jsonl (lifecycle log)

State machines:
  Task:     pending -> in_progress -> completed
  Worktree: absent  -> active      -> removed | kept
```

## How It Works

**Step 1.** Create a task. The goal is recorded first, before any directory exists.

```python
TASKS.create("Implement auth refactor")
# -> .tasks/task_1.json  status=pending  worktree=""
```

**Step 2.** Create a worktree and bind it to the task. Passing `task_id` automatically advances the task to `in_progress` -- you do not need to update the status separately.

```python
WORKTREES.create("auth-refactor", task_id=1)
# -> git worktree add -b wt/auth-refactor .worktrees/auth-refactor HEAD
# -> index.json gets new entry, task_1.json gets worktree="auth-refactor"
```

The binding writes state to both sides so you can traverse the relationship from either direction:

```python
def bind_worktree(self, task_id, worktree):
    task = self._load(task_id)
    task["worktree"] = worktree
    if task["status"] == "pending":
        task["status"] = "in_progress"
    self._save(task)
```

**Step 3.** Run commands in the worktree. The key detail: `cwd` points to the isolated directory, not your main project root. Every file operation happens in a sandbox that cannot collide with other worktrees.

```python
subprocess.run(command, shell=True, cwd=worktree_path,
               capture_output=True, text=True, timeout=300)
```

**Step 4.** Close out the worktree. You have two choices, depending on whether the work is done:

- `worktree_keep(name)` -- preserve the directory for later (useful when a task is paused or needs review).
- `worktree_remove(name, complete_task=True)` -- remove the directory, mark the bound task as completed, and emit an event. One call handles teardown and completion together.

```python
def remove(self, name, force=False, complete_task=False):
    self._run_git(["worktree", "remove", wt["path"]])
    if complete_task and wt.get("task_id") is not None:
        self.tasks.update(wt["task_id"], status="completed")
        self.tasks.unbind_worktree(wt["task_id"])
        self.events.emit("task.completed", ...)
```

**Step 5.** Observe the event stream. Every lifecycle step emits a structured event to `.worktrees/events.jsonl`, giving you a complete audit trail of what happened and when:

```json
{
  "event": "worktree.remove.after",
  "task": {"id": 1, "status": "completed"},
  "worktree": {"name": "auth-refactor", "status": "removed"},
  "ts": 1730000000
}
```

Events emitted: `worktree.create.before/after/failed`, `worktree.remove.before/after/failed`, `worktree.keep`, `task.completed`.

In the teaching version, `.tasks/` plus `.worktrees/index.json` are enough to reconstruct the visible control-plane state after a crash. The important lesson is not every production edge case. The important lesson is that goal state and execution-lane state must both stay legible on disk.

## What Changed From s17

| Component          | Before (s17)               | After (s18)                                  |
|--------------------|----------------------------|----------------------------------------------|
| Coordination       | Task board (owner/status)  | Task board + explicit worktree binding       |
| Execution scope    | Shared directory           | Task-scoped isolated directory               |
| Recoverability     | Task status only           | Task status + worktree index                 |
| Teardown           | Task completion            | Task completion + explicit keep/remove       |
| Lifecycle visibility | Implicit in logs         | Explicit events in `.worktrees/events.jsonl` |

## Try It

```sh
cd learn-claude-code
python agents/s18_worktree_task_isolation.py
```

1. `Create tasks for backend auth and frontend login page, then list tasks.`
2. `Create worktree "auth-refactor" for task 1, then bind task 2 to a new worktree "ui-login".`
3. `Run "git status --short" in worktree "auth-refactor".`
4. `Keep worktree "ui-login", then list worktrees and inspect events.`
5. `Remove worktree "auth-refactor" with complete_task=true, then list tasks/worktrees/events.`

## What You've Mastered

At this point, you can:

- Create isolated git worktrees so that parallel agents never produce file conflicts
- Bind tasks to worktrees with a two-way reference (task points to worktree name, worktree points to task ID)
- Choose between keeping and removing a worktree at closeout, with automatic task status updates
- Read the event stream in `events.jsonl` to understand the full lifecycle of every worktree

## What's Next

You now have agents that can work in complete isolation, each in its own directory with its own branch. But every capability they use -- bash, read, write, edit -- is hard-coded into your Python harness. In s19, you will learn how external programs can provide new capabilities through MCP (Model Context Protocol), so your agent can grow without changing its core code.

## Key Takeaway

> Tasks answer *what work is being done*; worktrees answer *where that work runs*; keeping them separate makes parallel systems far easier to reason about and recover from.
