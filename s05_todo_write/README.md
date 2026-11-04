# s05: TodoWrite — An Agent Without a Plan Drifts Off Course

[English](README.md) · [中文](README.zh.md) · [日本語](README.ja.md)

s01 → s02 → s03 → s04 → `s05` → [s06](../s06_subagent/) → s07 → ... → s16 → s17

> *"An agent without a plan goes wherever the wind blows"* — List the steps first, then execute. Complex tasks are less likely to miss steps.
>
> **Harness Layer**: Planning — Let the Agent think before it acts.

---

## The Problem

Give the Agent a complex task: "Rename all Python files to snake_case, run tests, and fix failures."

The Agent starts working, renames 3 files, runs a test, finds 2 failures, starts fixing. While fixing, it forgets the original goal was "rename to snake_case", the test failures have consumed all its attention.

The longer the conversation, the worse it gets: tool results keep filling the context, diluting the system prompt's influence. A 10-step refactoring: after steps 1-3, the Agent starts improvising because steps 4-10 have been pushed out of its attention.

---

## The Solution

![Todo Overview](images/todo-overview.en.svg)

S05 keeps the tool dispatch, permissions, and hooks from S04, then adds `todo_write` and a reminder counter. `todo_write` only updates planning state; the existing tools still perform the work.

The new tool uses the same `TOOL_HANDLERS[block.name]` dispatch path. After three consecutive tool-use rounds without `todo_write`, the harness adds a reminder to that round's tool results.

---

## How It Works

**TodoManager** owns the in-memory list, validates updates, and renders the state returned to the model. `run_todo_write` also prints that state in the terminal:

```python
class TodoManager:
    def __init__(self):
        self.items = []

    def update(self, todos: list | str) -> str:
        # Parse and validate before replacing the current list.
        validated = []
        ...
        self.items = validated
        return self.render()

    def render(self) -> str:
        # [ ] pending, [>] in progress, [x] completed
        ...


TODO = TodoManager()

def run_todo_write(todos: list | str) -> str:
    output = TODO.update(todos)
    print(output)
    return output
```

An update may contain at most 20 items, each item needs non-empty `content`, and only one item may be `in_progress`. The string input path accepts JSON or a Python list representation without using `eval`.

The tool definition joins the other 5 in the dispatch map:

```python
TOOLS = [
    {"name": "bash",       ...},
    {"name": "read_file",  ...},
    {"name": "write_file", ...},
    {"name": "edit_file",  ...},
    {"name": "glob",       ...},
    # s05: new entry
    {"name": "todo_write", "description": "Create and manage a task list ...",
     "input_schema": {
         "type": "object",
         "properties": {
             "todos": {
                 "type": "array",
                 "items": {
                     "type": "object",
                     "properties": {
                         "content": {"type": "string"},
                         "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                     },
                 },
             },
         },
     },
    },
]

TOOL_HANDLERS["todo_write"] = run_todo_write
```

**Reminder**: after three tool-use rounds without `todo_write`, the reminder is appended to the third round's results and the counter resets:

```python
rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
if rounds_since_todo >= 3:
    results.append({
        "type": "text",
        "text": "<reminder>Update your todos.</reminder>",
    })
    rounds_since_todo = 0
```

Typical flow when the Agent receives a task: first call `todo_write` to list all steps (all `pending`) → pick one step, set it to `in_progress` → complete it, set to `completed` → look at the next `pending` → continue.

**Key insight**: todo_write doesn't give the Agent any additional **execution capability**. What it adds is **planning capability**.

---

## Changes from s04

| Component | Before (s04) | After (s05) |
|-----------|-------------|-------------|
| Tool count | 5 (bash, read, write, edit, glob) | 6 (+todo_write) |
| Planning | None | Stateful TODO list + reminder |
| SYSTEM prompt | Generic prompt | Added "plan before executing" guidance |
| Loop | Tool dispatch and hooks | Same dispatch path, plus rounds_since_todo and reminder injection |

---

## Try It

```sh
cd learn-claude-code
python s05_todo_write/code.py
```

Try these prompts:

1. `Refactor s05_todo_write/example/hello.py: add type hints, docstrings, and a main guard` (should list 3 steps first, then execute)
2. `Create a Python package under s05_todo_write/example/demo_pkg with __init__.py, utils.py, and tests/test_utils.py`
3. `Review Python files under s05_todo_write/example and fix any style issues`

What to watch for: Was the first tool call `todo_write`? How many TODO steps were listed? Did statuses move from `pending` to `in_progress` / `completed` during execution?

---

## What's Next

The Agent can plan now. But if a task is too large, say "refactor the entire auth module", a TODO list alone isn't enough. That task is itself a collection of dozens of subtasks that would drown in a single conversation's context.

→ s06 Subagent: Break large tasks into subtasks, each handled by an independent Agent with its own clean context, no cross-contamination.


<!-- translation-sync: zh@v1, en@v1, ja@v1 -->
