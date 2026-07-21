# BaseAgent Session-Only Todos Design

## Objective

Change `homework/BaseAgent.py` so `todo_write` manages an in-memory execution
plan for the current process only. Todos must remain available across multiple
user turns during one BaseAgent run, but must not survive a process restart.

This change affects only the todo planning system. The s12 durable Task system
under `.tasks/` remains persistent and independent.

## Lifecycle

`CURRENT_TODOS` remains the single source of truth:

```text
process starts -> CURRENT_TODOS = []
todo_write     -> replace CURRENT_TODOS
later turns    -> update_context includes CURRENT_TODOS
process exits  -> todo state disappears
next process   -> CURRENT_TODOS = []
```

The implementation must not read, write, delete, or prompt about `.todo.json`.
An existing `.todo.json` from an older version is ignored and left untouched;
silently deleting user runtime state during startup would be an unrelated
destructive action.

## BaseAgent Changes

Remove the persistence-only constant and helpers:

- `TODO_FILE`
- `save_todos()`
- `read_saved_todos()`
- `all_todos_completed()`
- `ask_resume_todos()`

Update `run_todo_write()` so it validates the input, replaces
`CURRENT_TODOS`, prints the current plan, and returns the existing result string
without calling a persistence helper.

Update `main()` so startup initializes history and context and then immediately
enters the user input loop. It must not generate an automatic resume prompt or
invoke an Agent turn before the first user input.

Keep these existing behaviors:

- `_normalize_todos()` validation;
- the `todo_write` tool schema and handler registration;
- todo display in `run_todo_write()`;
- `format_current_todos()` and `update_context()` prompt injection;
- `rounds_since_todo` reminder/reset behavior;
- todos shared across user turns in the same process.

## Test Changes

Rewrite `tests/test_homework_baseagent_todo_resume.py` around the new lifecycle:

- BaseAgent no longer exposes `TODO_FILE` or persistence/resume helpers.
- `run_todo_write()` updates `CURRENT_TODOS` without creating `.todo.json`.
- `format_current_todos()` and `update_context()` expose the in-memory plan.
- multiple turns in one loaded namespace retain the current plan.
- loading BaseAgent again creates a fresh empty plan.
- startup does not ask whether to resume an old plan or invoke an automatic
  resume turn.
- existing todo input-validation behavior remains covered.

Update `tests/test_homework_baseagent_task_system.py` so its independence test
asserts that todo updates do not create a persistence file and durable Task
updates do not change `CURRENT_TODOS`.

No test may call a real Anthropic API. Fake modules and `runpy` loading remain
the isolation strategy.

## Verification

Run the focused todo tests first:

```text
uv run --with pytest pytest tests/test_homework_baseagent_todo_resume.py -q
```

Then run the s12 acceptance suite to confirm todo/Task separation:

```text
uv run --with pytest pytest tests/test_homework_baseagent_task_system.py -q
```

The s12 suite may continue to report pre-existing Task System acceptance gaps,
but the todo-independence test must pass under the session-only behavior.

Finally run related regressions:

```text
uv run --with pytest pytest \
  tests/test_homework_baseagent_error_recovery.py \
  tests/test_compaction_tool_pairs.py -q
```

## Non-Goals

- Do not modify the s12 durable Task storage.
- Do not add a persistence configuration flag.
- Do not retain no-op compatibility wrappers for removed todo persistence APIs.
- Do not delete an existing `.todo.json` automatically.
- Do not change todo statuses, schema, display formatting, or reminder cadence.
