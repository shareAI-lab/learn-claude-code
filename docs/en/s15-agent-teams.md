# s15: Agent Teams

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > [ s15 ] > s16 > s17 > s18 > s19`

## What You'll Learn
- How persistent teammates differ from disposable subagents
- How JSONL-based inboxes give agents a durable communication channel
- How the team lifecycle moves through spawn, working, idle, and shutdown
- How file-based coordination lets multiple agent loops run side by side

Sometimes one agent is not enough. A complex project -- say, building a feature that involves frontend, backend, and tests -- needs multiple workers running in parallel, each with its own identity and memory. In this chapter you will build a team system where agents persist beyond a single prompt, communicate through file-based mailboxes, and coordinate without sharing a single conversation thread.

## The Problem

Subagents from s04 are disposable: you spawn one, it works, it returns a summary, and it dies. It has no identity and no memory between invocations. Background tasks from s13 can keep work running in the background, but they are not persistent teammates making their own LLM-guided decisions.

Real teamwork needs three things: (1) persistent agents that outlive a single prompt, (2) identity and lifecycle management so you know who is doing what, and (3) a communication channel between agents so they can exchange information without the lead manually relaying every message.

## The Solution

The harness maintains a team roster in a shared config file and gives each teammate an append-only JSONL inbox. When one agent sends a message to another, it simply appends a JSON line to the recipient's inbox file. The recipient drains that file before every LLM call.

```
Teammate lifecycle:
  spawn -> WORKING -> IDLE -> WORKING -> ... -> SHUTDOWN

Communication:
  .team/
    config.json           <- team roster + statuses
    inbox/
      alice.jsonl         <- append-only, drain-on-read
      bob.jsonl
      lead.jsonl

              +--------+    send("alice","bob","...")    +--------+
              | alice  | -----------------------------> |  bob   |
              | loop   |    bob.jsonl << {json_line}    |  loop  |
              +--------+                                +--------+
                   ^                                         |
                   |        BUS.read_inbox("alice")          |
                   +---- alice.jsonl -> read + drain ---------+
```

## How It Works

**Step 1.** `TeammateManager` maintains `config.json` with the team roster. It tracks every teammate's name, role, and current status.

```python
class TeammateManager:
    def __init__(self, team_dir: Path):
        self.dir = team_dir
        self.dir.mkdir(exist_ok=True)
        self.config_path = self.dir / "config.json"
        self.config = self._load_config()
        self.threads = {}
```

**Step 2.** `spawn()` creates a teammate entry in the roster and starts its agent loop in a separate thread. From this point on, the teammate runs independently -- it has its own conversation history, its own tool calls, and its own LLM interactions.

```python
def spawn(self, name: str, role: str, prompt: str) -> str:
    member = {"name": name, "role": role, "status": "working"}
    self.config["members"].append(member)
    self._save_config()
    thread = threading.Thread(
        target=self._teammate_loop,
        args=(name, role, prompt), daemon=True)
    thread.start()
    return f"Spawned teammate '{name}' (role: {role})"
```

**Step 3.** `MessageBus` provides append-only JSONL inboxes. `send()` appends a single JSON line to the recipient's file; `read_inbox()` reads all accumulated messages and then empties the file ("drains" it). The storage format is intentionally simple -- the teaching focus here is the mailbox boundary, not storage cleverness.

```python
class MessageBus:
    def send(self, sender, to, content, msg_type="message", extra=None):
        msg = {"type": msg_type, "from": sender,
               "content": content, "timestamp": time.time()}
        if extra:
            msg.update(extra)
        with open(self.dir / f"{to}.jsonl", "a") as f:
            f.write(json.dumps(msg) + "\n")

    def read_inbox(self, name):
        path = self.dir / f"{name}.jsonl"
        if not path.exists(): return "[]"
        msgs = [json.loads(l) for l in path.read_text().strip().splitlines() if l]
        path.write_text("")  # drain
        return json.dumps(msgs, indent=2)
```

**Step 4.** Each teammate checks its inbox before every LLM call. Any received messages get injected into the conversation context so the model can see and respond to them.

```python
def _teammate_loop(self, name, role, prompt):
    messages = [{"role": "user", "content": prompt}]
    for _ in range(50):
        inbox = BUS.read_inbox(name)
        if inbox != "[]":
            messages.append({"role": "user",
                "content": f"<inbox>{inbox}</inbox>"})
            messages.append({"role": "assistant",
                "content": "Noted inbox messages."})
        response = client.messages.create(...)
        if response.stop_reason != "tool_use":
            break
        # execute tools, append results...
    self._find_member(name)["status"] = "idle"
```

## Read Together

- If you still treat a teammate like s04's disposable subagent, revisit [`entity-map.md`](./entity-map.md) to see how they differ.
- If you plan to continue into s16-s18, keep [`team-task-lane-model.md`](./team-task-lane-model.md) open -- it separates teammate, protocol request, task, runtime slot, and worktree lane into distinct concepts.
- If you are unsure how a long-lived teammate differs from a live runtime slot, pair this chapter with [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md).

## How It Plugs Into The Earlier System

This chapter is not just "more model calls." It adds durable executors on top of work structures you already built in s12-s14.

```text
lead identifies work that needs a long-lived worker
  ->
spawn teammate
  ->
write roster entry in .team/config.json
  ->
send inbox message / task hint
  ->
teammate drains inbox before its next loop
  ->
teammate runs its own agent loop and tools
  ->
result returns through team messages or task updates
```

Keep the boundary straight:

- s12-s14 gave you tasks, runtime slots, and schedules
- s15 adds durable named workers
- s15 is still mostly lead-assigned work
- structured protocols arrive in s16
- autonomous claiming arrives in s17

## Teammate vs Subagent vs Runtime Slot

| Mechanism | Think of it as | Lifecycle | Main boundary |
|---|---|---|---|
| subagent | a disposable helper | spawn -> work -> summary -> gone | isolates one exploratory branch |
| runtime slot | a live execution slot | exists while background work is running | tracks long-running execution, not identity |
| teammate | a durable worker | can go idle, resume, and keep receiving work | has a name, inbox, and independent loop |

## What Changed From s14

| Component      | Before (s14)     | After (s15)                |
|----------------|------------------|----------------------------|
| Tools          | 6                | 9 (+spawn/send/read_inbox) |
| Agents         | Single           | Lead + N teammates         |
| Persistence    | None             | config.json + JSONL inboxes|
| Threads        | Background cmds  | Full agent loops per thread|
| Lifecycle      | Fire-and-forget  | idle -> working -> idle    |
| Communication  | None             | message + broadcast        |

## Try It

```sh
cd learn-claude-code
python agents/s15_agent_teams.py
```

1. `Spawn alice (coder) and bob (tester). Have alice send bob a message.`
2. `Broadcast "status update: phase 1 complete" to all teammates`
3. `Check the lead inbox for any messages`
4. Type `/team` to see the team roster with statuses
5. Type `/inbox` to manually check the lead's inbox

## What You've Mastered

At this point, you can:

- Spawn persistent teammates that each run their own independent agent loop
- Send messages between agents through durable JSONL inboxes
- Track teammate status through a shared config file
- Coordinate multiple agents without funneling everything through a single conversation

## What's Next

Your teammates can now communicate freely, but they lack coordination rules. What happens when you need to shut a teammate down cleanly, or review a risky plan before it executes? In s16, you will add structured protocols -- request-response handshakes that bring order to multi-agent negotiation.

## Key Takeaway

> Teammates persist beyond one prompt, each with identity, lifecycle, and a durable mailbox -- coordination is no longer limited to a single parent loop.
