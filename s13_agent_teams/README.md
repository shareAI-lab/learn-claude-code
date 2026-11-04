# s13: Agent Teams — Runtime and Coordination Protocols

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → ... → [s10](../s10_task_system/) → `s13` → [s14](../s14_mcp_plugin/) → s15 → s16 → s17

> *"When one agent cannot hold the whole job, let teammates divide the work."* — Persistent teammates, shared task selection, optional worktrees, and coordination protocols.
>
> **Harness layer**: Team — how multiple agents divide work, share state, and stay under Lead's control.

---

## The Problem

Suppose we ask an agent to refactor an entire backend. The work may cover configuration loading, authentication, and tests. One agent can process those areas sequentially, but it takes longer and earlier details gradually leave its context.

This is a good candidate for parallel work, yet users normally describe the goal rather than design the team:

```text
Refactor this sample backend. Clean up configuration loading,
authentication, and tests, preserve the existing interfaces,
and make sure the tests pass.
```

The harness has to answer a connected set of questions:

1. Who decides that parallel work is useful, and who confirms the extra agents?
2. How does each teammate keep its identity and context across assignments?
3. How do results return to Lead without asking the model to poll an inbox?
4. Can an idle teammate pick up ready work without waiting for another assignment?
5. Which directory should a task use when parallel edits may conflict?
6. How do shutdown and plan approval become traceable, enforceable protocols?

---

## The Solution

![Agent Teams Overview](images/agent-teams-overview.en.svg)

s13 reuses s10's base tools, hooks, permission checks, and Task System, then adds a Lead-managed team runtime:

- **Lead** owns the user conversation, proposes a division of work, and waits for confirmation.
- **Teammates** run independent agent loops and alternate between WORK and IDLE.
- **MessageBus** carries ordinary messages, results, and control events through file-backed mailboxes.
- **Runtime delivery** consumes Lead's mailbox and injects team events into the next turn.
- **The shared task board** lets idle teammates find ready work and claim it under a lock.
- **Optional worktrees** bind a task to another working directory when the work needs it. Unbound tasks use the normal repository directory.
- **Typed protocols and a plan gate** make shutdown and approval state explicit and block mutating tools until a required plan is approved.

Task graph authoring keeps s10's two-phase contract. The Lead first calls `create_task` for every node, then uses the returned runtime IDs with `update_task(addBlockedBy=...)` before assigning ready work. Only the Lead receives `update_task`; teammates can list, claim, and complete tasks but cannot rewrite graph structure while the team is running.

s11 background tasks and s12 scheduled tasks are not carried into this chapter. Neither mechanism is required for teammate communication, task claiming, or plan approval.

These are all parts of the Team harness layer. Teammates do not need a separate loop for task discovery, and a worktree does not create a new kind of agent.

---

## How It Works

### 1. Lead proposes a team and waits for user confirmation

Starting teammates changes cost, concurrency, and the set of actors that may edit the workspace. Lead's system prompt keeps that boundary visible:

```python
"When parallel work would help, first propose a small team with clear "
"responsibilities and wait for the user's confirmation. Do not call "
"spawn_teammate before the user confirms."
```

For the first request, Lead only proposes a split:

```text
I suggest three parallel areas:
- config: clean up configuration loading
- auth: refactor authentication
- tests: add regression coverage

I will start the teammates after you confirm.
```

After the user says "Go ahead," Lead can call `spawn_teammate`. Lead creates the Task first and passes its initial `task_id` to the teammate. The user states the goal, Lead designs the team, and the user confirms the execution boundary.

### 2. Every teammate owns an independent loop

An s06 subagent is a one-shot call. A teammate is a persistent execution unit:

| | s06 Subagent | s13 Teammate |
|---|---|---|
| Lifecycle | Ends after one call | `WORK → IDLE → WORK` until shutdown |
| Context | Exists for one task | Persists across assignments |
| Communication | Returns one result | Receives messages and emits events |
| Coordination | One-way delegation | Two-way collaboration with Lead |

`TeammateRuntime` gives each teammate its own system prompt, messages, tools, and current Task, then runs its WORK / IDLE loop in a daemon thread. Lead can keep coordinating while teammates work. The names `lead` and `agent` are reserved for runtime identities, while `MessageBus` still accepts `lead` as the coordinator mailbox.

`spawn_teammate` claims the initial Task before the thread starts. A failed claim prevents the teammate from starting. Without a Task, workspace and Shell tools ask the teammate to claim one instead of falling back to the repository directory.

### 3. MessageBus keeps communication outside model context

Lead and teammates cannot share one messages array. Otherwise one teammate's tool results would leak into another teammate's reasoning. `MessageBus` gives each agent a `.mailboxes/<name>.jsonl` inbox:

```python
class MessageBus:
    def send(self, from_agent, to_agent, content,
             msg_type="message", metadata=None):
        msg = {
            "from": from_agent,
            "to": to_agent,
            "content": content,
            "type": msg_type,
            "metadata": metadata or {},
        }
        with self._changed:
            MAILBOX_DIR.mkdir(parents=True, exist_ok=True)
            with self._path(to_agent).open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(msg, ensure_ascii=True) + "\n")
            self._changed.notify_all()

    def wait_for_messages(self, agent, timeout=None):
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._changed:
            while not self.peek(agent):
                remaining = (None if deadline is None
                             else deadline - time.monotonic())
                if remaining is not None and remaining <= 0:
                    return []
                self._changed.wait(remaining)
            return self._read_unlocked(agent)
```

A lock protects mailbox files from concurrent access. A `Condition` lets the runtime wake a teammate for a message and also supports the short timeout used while IDLE.

### 4. The runtime delivers inbox events

`read_inbox()` consumes messages by reading and deleting the mailbox file, so Lead keeps a single consumer, `consume_lead_inbox()`:

```python
def consume_lead_inbox():
    messages = BUS.read_inbox("lead")
    for message in messages:
        if message["type"].endswith("_response"):
            match_response(...)
    return messages
```

The CLI loop waits for terminal input and Lead's mailbox at the same time. When a message arrives, it consumes the mailbox before starting another Lead turn:

```text
MessageBus → consume_lead_inbox
           → update protocol state
           → inject [Team events] into history
           → start another Lead turn
```

After spawning a teammate, Lead ends the current turn instead of repeatedly calling `list_teammates` or `get_task`. The runtime starts the next turn when a team event arrives.

`check_inbox` is not a model tool. Message arrival belongs to the runtime; the model handles events after the runtime has delivered them into its context.

### 5. Result and IDLE are separate events

When a teammate finishes one assignment, the runtime sends two events in order:

```text
result:            "Authentication refactored; related tests pass."
idle_notification: "Waiting for more work."
```

`result` answers "What did this assignment produce?" `idle_notification` answers "Can this teammate accept more work?" One vague "done" cannot represent both facts.

An idle teammate does not exit. A direct message or a ready task returns it to WORK; a `shutdown_request` starts a graceful shutdown handshake.

### 6. IDLE checks the mailbox before looking for ready tasks

IDLE gives messages priority, then checks the shared task board:

```python
while True:
    inbox = BUS.wait_for_messages(name, IDLE_SCAN_INTERVAL)
    if inbox:
        should_stop = handle_messages(inbox)
        if should_stop or messages[-1]["role"] == "user":
            break
        continue

    task = claim_next_task(name)
    if task:
        messages.append({
            "role": "user",
            "content": f"[Auto-claimed task {task.id}] {task.subject}",
        })
        break
```

Shutdown, plan approval, and direct instructions from Lead should arrive before opportunistic work. If there is no message and no ready task, the teammate remains IDLE. A blocked task may become ready after another teammate completes its prerequisite.

### 7. Discovery and claim are separate, and claim is atomic

Scanning only finds candidates:

```python
def scan_unclaimed_tasks() -> list[Task]:
    return [
        task for task in list_tasks()
        if task.status == "pending"
        and task.owner is None
        and can_start(task.id)
    ]
```

The list is a snapshot. Another teammate, or another harness process using the same task directory, may see the same task. Ownership changes therefore happen inside `claim_task()` under `task_store_lock()`, which combines the in-process lock with a file lock:

```python
def claim_task(task_id: str, owner: str) -> str:
    with task_store_lock():
        task = load_task(task_id)
        if task.status != "pending" or task.owner is not None:
            return "Task is no longer available"
        if _owner_in_progress(owner):
            return "Owner must complete its current task first"
        if not can_start(task_id):
            return "Task is blocked"
        cwd, error = task_worktree_cwd(task)
        if error:
            return f"Cannot claim {task_id}: {error}"
        task.owner = owner
        task.status = "in_progress"
        save_task(task)
        teammate_assignments[owner] = {"task_id": task.id, "cwd": cwd}
        return f"Claimed {task.id}"
```

Many teammates may discover the same candidate, but only one claim can move it to `in_progress`. Task files are written through a temporary file and atomically replaced while the same store lock is held. A teammate must also finish its current task before claiming another, and a broken worktree binding fails closed rather than falling back to the repository directory.

### 8. Claimed work reuses the same WORK loop

After a successful claim, the runtime injects the task ID, subject, and description into the teammate's messages:

```text
ready task appears
  → IDLE teammate discovers it
  → claim_task writes owner and in_progress
  → task enters teammate messages
  → WORK
  → complete_task
  → result + idle_notification
  → IDLE
```

The teammate uses the same model call, file tools, Shell, plan gate, result reporting, and shutdown protocol as a direct Lead assignment. Task discovery is another entry into the existing WORK loop.

### 9. The task selects the tools' working directory

`Task.worktree` is optional:

```python
@dataclass
class Task:
    id: str
    subject: str
    description: str
    status: str
    owner: str | None
    blockedBy: list[str]
    worktree: str | None = None
```

Lead can create and bind a worktree when separate directories will help:

```python
create_worktree(name="auth-refactor", task_id="task_1a2b3c4d")
```

`create_worktree` is a Lead-only tool. It accepts a pending, unowned, unbound task, validates the name, path, branch, and Git registry, creates the checkout, then writes the task binding. If Git reports failure after leaving a branch or registered checkout, the runtime reports a partial operation, leaves the task unbound, and preserves those artifacts for manual recovery. Teammates only see task and file tools.

Claiming the task stores its resolved directory in `teammate_assignments`; that teammate's `bash`, `read_file`, `write_file`, `edit_file`, and `glob` wrappers read the directory from the assignment. A task with no worktree resolves to `WORKDIR`; a teammate without a claimed Task cannot use those workspace tools:

```python
cwd, error = task_worktree_cwd(task)
if not error:
    teammate_assignments[owner] = {
        "task_id": task.id,
        "cwd": cwd,
    }
```

`complete_task(task_id, owner)` checks that the caller owns the in-progress task. Successful completion records the result but keeps the assignment directory selected until that model turn ends. This lets later tool calls in the same response stay in the task's worktree. The runtime releases the assignment when the teammate returns to IDLE; a failed completion keeps it so the teammate can fix the task and try again.

After a restart, `assignment_cwd()` can rebuild an in-progress assignment from the durable task owner and worktree binding. It also replaces a stale local lease when the same owner has moved to another task. A missing or invalid binding fails closed instead of silently routing work to the repository directory.

> A worktree separates Git working directories and branches. It is not a sandbox: Shell commands can still access paths and resources allowed to the parent process.

### 10. Worktree removal belongs to the host

The model can create a task-bound worktree, but it cannot remove one. Cleanup remains a host helper so the user or host can first inspect task ownership, the assignment lease, and Git status. The helper refuses pending or in-progress task bindings and current-turn leases. Without an explicit destructive choice, tracked, untracked, and ignored files all block removal.

`remove_worktree(name, discard_changes=True)` is reserved for host code that has already obtained explicit user confirmation. Either removal path retains the `wt/<name>` branch, including clean local commits with no upstream. A successful removal clears the task binding because the checkout no longer exists.

```text
clean worktree   → host may remove directory and retain wt/<name> branch
changed worktree → user decides how to preserve or discard it
pending/running task → refuse removal
```

Task completion also stays separate from worktree cleanup. `complete_task` records the task result; after the teammate reaches IDLE, the user or host can inspect, merge, keep, or remove the worktree.

### 11. Control messages use types and request IDs

Free-form text works for ordinary collaboration, but shutdown and approval should not depend on guessing intent. They use structured messages:

![Team Protocols](images/team-protocols-overview.en.svg)

```python
@dataclass
class ProtocolState:
    request_id: str
    type: str
    sender: str
    target: str
    status: str
    payload: str
    work_version: int | None = None
    task_id: str | None = None


pending_requests: dict[str, ProtocolState] = {}
```

The shutdown path is:

```text
Lead creates a pending shutdown request
  → shutdown_request(request_id) enters the teammate inbox
  → the teammate finishes its current step
  → shutdown_response(request_id) returns to Lead
  → request_id locates the original request
  → pending becomes approved and the teammate loop exits
```

The ID correlates one reply with one request, the type prevents a mismatched reply from changing state, and the status prevents duplicate responses from being applied twice.

### 12. Plan approval constrains execution

The plan protocol runs in the opposite direction:

```text
Lead → plan_request
teammate → plan_approval_request(request_id, plan)
Lead → plan_approval_response(request_id, approve, feedback)
```

When Lead already knows that a teammate must plan first, `spawn_teammate(..., task_id=task.id, require_plan=True)` claims the Task and activates the gate before the teammate thread starts. `request_plan` can also require a plan from a teammate that is already running.

Tool dispatch enforces the gate:

```python
def _run_teammate_tool(name, block, handlers):
    gate = plan_gates.get(name, "not_required")
    if block.name in {"bash", "write_file", "edit_file"} and gate not in {
        "not_required", "approved"
    }:
        return f"Blocked: plan status is {gate}."
    try:
        return handlers[block.name](**block.input)
    except Exception as error:
        return f"Error: {type(error).__name__}: {error}"
```

While the state is `required`, `pending`, or `rejected`, the teammate can read files and submit or revise a plan, but it cannot run Shell commands, write files, or edit files. A submitted plan records the teammate's current task and work version. Claiming or releasing a Task changes that version and invalidates the old approval; an ordinary message changes neither the task identity nor the approval state.

Teammates do not read user input from their background threads. A dangerous command or path outside the workspace returns a permission error so Lead can handle the decision with the user.

---

## One Complete Run

```text
s13 >> Put the backend refactor on a shared task board. Clean up
       configuration, authentication, and tests in parallel where possible.
       Use a worktree for authentication, preserve existing interfaces,
       and make sure the tests pass.

Lead: I suggest config, auth, and tests as three areas.
      Shall I start the team?

s13 >> Go ahead.

[task] config created
[task] auth created → worktree auth-refactor
[task] tests created
[claim] alice → config (cwd: repository)
[claim] bob → auth (cwd: .worktrees/auth-refactor)
[teammate] alice spawned
[teammate] bob spawned
[complete] auth
[bus] bob → lead (result) ...
[bus] bob → lead (idle_notification) ...
[wake: 2 team events → new turn]
Lead: I received the authentication result and will coordinate the rest.
```

The terminal exposes the user request, Lead's proposal, task state, claims, selected directories, results, IDLE transitions, and control events. The user does not have to name a Lead or ask it to check an inbox.

---

## What Changed from s10

| Component | s10 | s13 |
|---|---|---|
| Agents | One agent | One Lead plus persistent teammates |
| User flow | Execute the request | Propose a team, then confirm startup |
| Communication | None | File mailboxes plus runtime delivery |
| Lifecycle | One loop | Teammate `WORK / IDLE / shutdown` |
| Shared work | One agent uses task tools | IDLE scan plus atomic teammate claims |
| Working directory | Repository `WORKDIR` | A claimed Task, with an optional worktree |
| Reporting | Current agent output | Separate `result` and `idle_notification` |
| Control | None | Typed shutdown and plan approval protocols |
| Enforcement | No team constraint | Required plans gate mutating tools |

---

## Try It

```sh
cd learn-claude-code
python s13_agent_teams/code.py
```

Start with an ordinary request:

```text
Put the backend refactor on a shared task board. Complete configuration,
authentication, and tests in parallel where dependencies allow. Use a
worktree for authentication, preserve existing interfaces, and summarize
the result.
```

After Lead proposes the team, reply:

```text
Go ahead.
```

Watch `.tasks/` move from `pending` to `in_progress` and `completed`, `.mailboxes/` deliver `result` and `idle_notification`, and `.worktrees/` appear only for the bound task. Also check that direct messages beat task-board scans and that a failed `complete_task` does not reset the teammate's working directory.

---

## What's Next

The Lead and its teammates can only call tools defined directly in `code.py`. Connecting Jira, a deployment platform, or a knowledge base still requires separate tool schemas and handlers for each external system. Changes to those external tools also require changes to the course code.

s14 MCP Tools → Connect external services at runtime through one discovery and invocation protocol, then add their tools to the tool pool.

<!-- translation-sync: zh@v12, en@v12, ja@v12 -->
