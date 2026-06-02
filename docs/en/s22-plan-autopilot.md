# s22: Plan + Autopilot Modes

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19 > s20 > s21 > [ s22 ] > s23`

> *"Plan with the human, execute without them"* -- two modes, one machine.
>
> **Harness layer**: Mode machine -- the harness shifts between planning and execution.

## Problem

By s21, the agent inherits context from the directory structure. But the user still needs to micromanage. "First plan the changes, then implement" -- the user has to say both. The agent either plans (and waits for approval after every step) or executes (without a shared plan to reference).

What the user wants: a planning phase where the agent proposes a plan, the human reviews and edits, then an autopilot phase where the agent executes the approved plan without constant hand-holding.

## Solution

```
Mode machine:

  +------+    /autopilot      +-------------+
  | PLAN | --------------->  | AUTOPILOT   |
  |      |                    |             |
  | - propose plan   +------>| - execute   |
  | - human reviews  | pause | - step-by-  |
  | - edits plan     |       |   step      |
  | - approves       |       | - reports   |
  +------+ <---------+       | - stops on  |
           /plan             |   errors    |
                             +-------------+

State transitions:
  PLAN  -- /autopilot (plan saved) --> AUTOPILOT
  AUTOPILOT -- /plan --> PLAN (pause, return to review)
  AUTOPILOT -- all steps done --> DONE
  AUTOPILOT -- error --> PLAN (stop, report, wait)

Shared state:
  .omc/state/autopilot.json
  {
    "mode": "autopilot",
    "plan": ["step 1", "step 2", "step 3"],
    "completed": [true, true, false],
    "iteration": 2
  }
```

## How It Works

1. **PLAN mode.** The agent proposes a structured plan.

```python
def propose_plan(self, task: str) -> list:
    response = client.messages.create(
        model=self.model,
        messages=[{"role": "user",
            "content": f"Create a step-by-step plan for: {task}\n"
                       "Return a JSON array of steps."}],
        tools=[{"name": "save_plan",
                "description": "Save the execution plan"}],
    )
    plan = extract_tool_call(response, "save_plan")
    self.state["plan"] = plan
    self.state["mode"] = "plan"
    self._save_state()
    return plan
```

2. **Transition to AUTOPILOT.** The user types `/autopilot`, the harness reads the saved plan.

```python
def enter_autopilot(self) -> str:
    if not self.state.get("plan"):
        return "Error: No saved plan. Plan first, then run /autopilot."
    self.state["mode"] = "autopilot"
    self.state["completed"] = [False] * len(self.state["plan"])
    self._save_state()
    return f"Autopilot started. {len(self.state['plan'])} steps to execute."
```

3. **AUTOPILOT execution loop.** Execute each step, update state, stop on errors.

```python
def autopilot_step(self) -> str:
    pending = next(
        (i for i, done in enumerate(self.state["completed"]) if not done),
        None
    )
    if pending is None:
        self.state["mode"] = "done"
        return "All steps completed."

    step = self.state["plan"][pending]
    result = self.run_agent(f"Execute this step: {step}")

    if result.get("error"):
        self.state["mode"] = "plan"  # stop on error
        return f"Step {pending + 1} failed: {result['error']}"

    self.state["completed"][pending] = True
    self.state["iteration"] = pending + 1
    self._save_state()
    return f"Step {pending + 1}/{len(self.state['plan'])} done: {step}"
```

4. **Pause and resume.** `/plan` stops autopilot, returns to review mode.

```python
def exit_autopilot(self) -> str:
    completed = sum(1 for d in self.state.get("completed", []) if d)
    total = len(self.state.get("plan", []))
    self.state["mode"] = "plan"
    self._save_state()
    return f"Autopilot paused. {completed}/{total} steps completed."
```

5. **State persistence.** Survives restarts -- the agent resumes where it left off.

```python
def _save_state(self):
    state_file = Path(".omc/state/autopilot.json")
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(self.state, indent=2))
```

## What Changed From s21

| Component       | Before (s21)              | After (s22)                      |
|-----------------|---------------------------|----------------------------------|
| Execution mode  | Single mode               | PLAN + AUTOPILOT mode machine    |
| User control    | Step-by-step prompts      | Plan review then hands-free      |
| Progress        | Implicit in conversation  | Explicit step tracking in state  |
| Recovery        | Lost on exit              | State persists in .omc/state/    |
| Error handling  | Continue anyway           | Stop autopilot, return to plan   |

## Try It

```sh
cd learn-claude-code
python agents/s22_plan_autopilot.py
```

Try these:

1. `Plan a refactor: add type hints to all functions in utils.py` -- enters PLAN mode
2. `/autopilot` -- starts executing the approved plan
3. Watch the agent execute step by step, reporting progress
4. `/plan` -- pause mid-execution, review remaining steps
5. `/autopilot` -- resume from where it stopped
