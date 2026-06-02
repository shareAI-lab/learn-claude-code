# s19: Agent Memory & Persistence

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > [ s19 ]`

> *"Files outside the conversation outlive the conversation"* -- state survives restarts.
>
> **Harness layer**: Persistence -- save and restore agent state across sessions.

## Problem

By s18, the harness optimizes cost. But when the agent exits, all conversation state is lost. The next session starts from scratch -- the agent doesn't remember what it learned, what tasks it was doing, or what directives were given.

## Solution

```
.agent_memory/
|-- priority.json      (always loaded, < 500 chars, never pruned)
|                       {"directives": ["..."], "notes": {...}}
|-- working/
|   |-- 2025-01-01T12-00-00.json  (timestamped entries)
|   `-- 2025-01-02T08-30-00.json
`-- checkpoint.json    (last conversation state)

Session lifecycle:
1. STARTUP: load priority + recent working memory
2. LOAD: restore checkpoint (conversation state)
3. WORK: agent loop, append messages
4. SAVE: checkpoint after each turn
5. PRUNE: remove working memory > 7 days old

Priority vs Working:
Priority  -- small, always loaded, never pruned
Working   -- timestamped, loaded if recent, auto-pruned
```

## How It Works

1. **Priority memory.** Small JSON file, always loaded.

```python
def add_directive(self, directive: str):
    data = self.read_priority()
    data["directives"].append(directive)
    self.write_priority(data)
```

2. **Working memory.** Timestamped entries, auto-pruned after 7 days.

```python
def write_working(self, content: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    path = self.working / f"{ts}.json"
    path.write_text(json.dumps({"timestamp": ts, "content": content}))

def prune(self, days=7) -> int:
    cutoff = datetime.now() - timedelta(days=days)
    for f in self.working.glob("*.json"):
        ts = datetime.fromisoformat(json.loads(f.read_text())["timestamp"])
        if ts < cutoff:
            f.unlink()
```

3. **Checkpoint.** Save/restore conversation state.

```python
def save_checkpoint(self, messages: list):
    path = self.base / "checkpoint.json"
    path.write_text(json.dumps(messages))

def load_checkpoint(self) -> list:
    path = self.base / "checkpoint.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())
```

## Try It

```sh
cd learn-claude-code
python agents/s19_agent_memory.py
```

Try these:

1. Add a directive: `/directive Always use type hints`
2. Save memory: `/memsave Learned that the API uses v2`
3. Check state: `/memory`
4. Exit and restart -- the directive and memory persist
5. `/clear` -- wipe all memory and start fresh
