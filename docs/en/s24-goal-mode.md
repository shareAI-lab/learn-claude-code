# s24: Goal Mode

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19 > s20 > s21 > s22 > s23 > [ s24 ]`

> *"Give the agent a north star, not just a to-do list"* -- persistent objectives that survive sessions.
>
> **Harness layer**: Goal tracking -- the harness maintains a persistent objective with state, progress, and self-evaluation.

## Problem

By s23, the agent runs safely inside a sandbox. But there's a deeper issue: each session starts blank. The agent forgets what it was building last time. The user has to re-explain the goal every time they return. A multi-week refactor gets reset to zero every time the session ends.

Even within a session, the agent drifts. Midway through a task, it chases tangents -- fixing a lint warning instead of shipping the feature. There's no north star to pull it back.

What the user wants: a goal that persists across sessions, tracks progress, and lets the agent self-evaluate whether it's moving toward the objective or wandering off.

## Solution

```
Goal lifecycle:

  +---------+  start    +---------+  working    +---------+
  | CREATED | --------> | RUNNING | ----------> | PAUSED  |
  |         |            |         |              |         |
  | - goal  |            | - tool  |  /goal pause | - save  |
  |   set   |            |   calls |              |   state |
  | - crit- |            |   toward |              | - user  |
  |   eria  |            |   goal   |  /goal resum<-|   broke |
  |   saved |            |         |  e           |   it    |
  +---------+            +----+----+              +---------+
                               |                     ^
                         complete|                    |
                         +------v------+              |
                         | COMPLETED  |<--------------+
                         |            |  /goal resumefailed
                         | - summary  |              |
                         | - archive  |              v
                         +------------+          +---------+
                                          +----->| FAILED  |
                                          |      |         |
                                  max_retries| - error    |
                                          |   - last   |
                                          |   - log    |
                                          +---------+

Goal state file (.omc/state/goal.json):
  {
    "goal": "Refactor auth module to use OAuth2",
    "state": "running",
    "criteria": [
      {"id": 1, "desc": "Add OAuth2 provider", "done": true},
      {"id": 2, "desc": "Migrate login flow", "done": true},
      {"id": 3, "desc": "Remove legacy tokens", "done": false},
      {"id": 4, "desc": "Add integration tests", "done": false}
    ],
    "progress": "50%",
    "iteration": 14,
    "last_check": "2025-03-15T10:30:00",
    "created_at": "2025-03-10T09:00:00"
  }

Self-evaluation loop (every N tool calls or on /goal check):
  Model generates tool call
          |
          v
  +------------------------+
  |  Is there an active    |
  |  goal?                 |
  +---------+--------------+
            |
       +----+----+
       |         |
      yes        no -> normal execution
       |
       v
  +------------------------+
  |  self_evaluate()       |
  |  "Does this tool call  |
  |   advance the goal?"   |
  +---------+--------------+
            |
     +------+------+
     |      |      |
    yes    maybe  no
     |      |      |
     v      v      v
  Execute  Execute Warn: "This may
             with    not advance the
             caution goal. Continue?"
                      |
                      v
               +------------+
               | Log drift  |
               | Update     |
               | progress   |
               +------------+
```

## How It Works

1. **Goal creation.** The user sets a persistent goal with acceptance criteria.

```python
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
import json

@dataclass
class Goal:
    goal: str
    criteria: list[dict] = field(default_factory=list)
    state: str = "created"
    progress: str = "0%"
    iteration: int = 0
    created_at: str = ""
    last_check: str = ""
    error: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
```

2. **Persistence.** The goal survives session restarts -- stored in `.omc/state/goal.json`.

```python
GOAL_PATH = Path(".omc/state/goal.json")

def save_goal(self):
    GOAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOAL_PATH.write_text(json.dumps(asdict(self), indent=2))

def load_goal() -> Goal | None:
    if not GOAL_PATH.exists():
        return None
    data = json.loads(GOAL_PATH.read_text())
    return Goal(**data)
```

3. **State transitions.** The goal moves through a defined state machine.

```python
VALID_TRANSITIONS = {
    "created":   ["running", "failed"],
    "running":   ["paused", "completed", "failed"],
    "paused":    ["running", "failed"],
    "completed": [],
    "failed":    ["created"],
}

def transition(self, new_state: str) -> str:
    if new_state not in VALID_TRANSITIONS.get(self.state, []):
        return f"Cannot go {self.state} -> {new_state}"
    old = self.state
    self.state = new_state
    self.last_check = datetime.now().isoformat()
    self.save_goal()
    return f"Goal: {old} -> {new_state}"
```

4. **Self-evaluation loop.** Every N tool calls (or on demand), the agent checks whether it's on track.

```python
def self_evaluate(self, tool_call: dict, context: str) -> dict:
    prompt = f"""Goal: {self.goal}
Criteria remaining: {[c['desc'] for c in self.criteria if not c.get('done')]}
Last tool call: {json.dumps(tool_call)}
Context: {context[-500:]}

Rate alignment: aligned / drifting / off_track
Brief reason (one line)."""

    response = client.messages.create(
        model=self.model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )

    alignment = extract_alignment(response)
    self.iteration += 1
    self.last_check = datetime.now().isoformat()
    self.save_goal()

    return {
        "alignment": alignment,
        "iteration": self.iteration,
        "progress": self.calculate_progress(),
    }

def calculate_progress(self) -> str:
    total = len(self.criteria)
    if total == 0:
        return "0%"
    done = sum(1 for c in self.criteria if c.get("done"))
    return f"{int(done / total * 100)}%"
```

5. **Progress tracking.** Criteria are marked complete as the agent advances.

```python
def mark_complete(self, criteria_id: int) -> str:
    for c in self.criteria:
        if c["id"] == criteria_id:
            c["done"] = True
            break
    self.progress = self.calculate_progress()
    self.save_goal()

    if all(c.get("done") for c in self.criteria):
        self.transition("completed")
        return f"All criteria met. Goal completed!"
    return f"Progress: {self.progress}"
```

6. **Drift detection and recovery.** When the agent wanders, surface a warning.

```python
CHECK_INTERVAL = 10  # evaluate every 10 tool calls

def on_tool_call(self, tool_call: dict) -> str | None:
    if self.state != "running":
        return None

    self.iteration += 1
    if self.iteration % CHECK_INTERVAL == 0:
        result = self.self_evaluate(tool_call, self.recent_context)

        if result["alignment"] == "off_track":
            return (
                f"DRIFT DETECTED (check #{self.iteration}):\n"
                f"Progress: {result['progress']}\n"
                f"Goal: {self.goal}\n"
                f"Pause and re-evaluate?"
            )
        elif result["alignment"] == "drifting":
            return f"Caution: may be drifting from goal. Progress: {result['progress']}."
    return None
```

## What Changed From s23

| Component       | Before (s23)                     | After (s24)                              |
|-----------------|----------------------------------|------------------------------------------|
| Objectives      | Per-session, implicit            | Persistent goal with explicit criteria   |
| State           | Sandbox mode only                | Goal state machine (5 states)            |
| Persistence     | Sandbox log                      | Goal saved to .omc/state/goal.json       |
| Self-check      | None                             | Self-evaluation every N tool calls       |
| Progress        | Not tracked                      | Criteria-based progress percentage       |
| Drift handling  | None                             | Alignment scoring + warnings             |
| Recovery        | User re-explains after restart   | Load goal state, resume automatically    |
| Completion      | User decides                     | Automatic when all criteria met          |

## Try It

```sh
cd learn-claude-code
python agents/s24_goal_mode.py
```

Try these:

1. `/goal set Refactor the auth module to use OAuth2` -- create a goal with criteria
2. `/goal status` -- see current goal state, progress, and criteria
3. Watch the agent work; every 10 tool calls it self-evaluates alignment
4. `/goal check` -- force an immediate self-evaluation
5. `/goal pause` -- pause the goal, save state, and stop tool execution
6. Restart the session -- the goal is still there
7. `/goal resume` -- continue from where you left off
8. `/goal mark 3` -- mark criterion 3 as complete, watch progress update
9. Complete all criteria -- the goal auto-transitions to COMPLETED
10. `/goal summary` -- see the full lifecycle: created, checks, transitions, completion
