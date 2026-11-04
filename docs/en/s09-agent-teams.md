# s09: Agent Teams

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > [ s09 ] > s10 > s11 > s12`

> *"When the task is too big for one, delegate to teammates"* -- persistent teammates + async mailboxes.
>
> **Harness layer**: Team mailboxes -- multiple models, coordinated through files.

## Problem

Subagents (s04) are disposable: spawn, work, return summary, die. No identity, no memory between invocations. Background tasks (s08) run shell commands but can't make LLM-guided decisions.

Real teamwork needs: (1) persistent agents that outlive a single prompt, (2) identity and lifecycle management, (3) a communication channel between agents.

## Solution

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

1. TeammateManager maintains config.json with the team roster.

```python
class TeammateManager:
    def __init__(self, team_dir: Path):
        self.dir = team_dir
        self.dir.mkdir(exist_ok=True)
        self.config_path = self.dir / "config.json"
        self.config = self._load_config()
        self.threads = {}
```

2. `spawn()` creates a teammate and starts its agent loop in a thread.

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

3. MessageBus: append-only JSONL inboxes. `send()` appends a JSON line; `read_inbox()` reads all and drains.

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
        msgs = [json.loads(l) for l in path.read_text(encoding="utf-8").strip().splitlines() if l]
        path.write_text("", encoding="utf-8")  # drain
        return json.dumps(msgs, indent=2)
```

4. Each teammate checks its inbox before every LLM call, injecting received messages into context.

```python
def _teammate_loop(self, name, role, prompt):
    messages = [{"role": "user", "content": prompt}]
    for _ in range(50):
        inbox = BUS.read_inbox(name)
        if inbox != "[]":
            messages.append({"role": "user",
                "content": f"<inbox>{inbox}</inbox>"})
        response = client.messages.create(...)
        if response.stop_reason != "tool_use":
            break
        # execute tools, append results...
    self._find_member(name)["status"] = "idle"
```

## What Changed From s08

| Component      | Before (s08)     | After (s09)                |
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
python agents/s09_agent_teams.py
```

1. `Spawn alice (coder) and bob (tester). Have alice send bob a message.`
2. `Broadcast "status update: phase 1 complete" to all teammates`
3. `Check the lead inbox for any messages`
4. Type `/team` to see the team roster with statuses
5. Type `/inbox` to manually check the lead's inbox
