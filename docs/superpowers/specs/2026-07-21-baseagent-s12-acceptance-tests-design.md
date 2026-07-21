# BaseAgent s12 Acceptance Tests Design

## Objective

Create a focused pytest acceptance suite for the mandatory s12 Task System
requirements in `homework/REQUIREMENTS_s11_s15.md`. The suite must assess the
current `homework/BaseAgent.py` without calling a real Anthropic API or changing
the production implementation.

Optional s12 challenges—dependency-cycle detection, cancel/reopen operations,
timestamps, results, and list filtering—are outside the acceptance boundary.

## Test Architecture

The test module will follow the isolation pattern used by
`tests/test_homework_baseagent_error_recovery.py`:

- Replace `anthropic` and `dotenv` with deterministic fake modules.
- Set required model environment variables.
- Load `BaseAgent.py` with `runpy.run_path(..., run_name="not_main")`.
- Obtain the function globals through `agent_loop.__globals__`.
- Redirect `TASK_DIR` and `TODO_FILE` to pytest `tmp_path` locations.
- Avoid all live API calls and repository runtime-state dependencies.

The suite will combine public tool-interface tests with focused helper-level
tests. This verifies both Agent integration and the storage/state behavior behind
the tools.

## Acceptance Coverage

### Contract and registration

- `Task` exposes `id`, `subject`, `description`, `status`, `owner`, and
  `blockedBy`.
- `create_task`, `list_tasks`, `get_task`, `claim_task`, and `complete_task`
  appear in both `TOOLS` and `TOOL_HANDLERS`.
- Tool schemas require the appropriate fields.

### Persistence and presentation

- Each created task produces its own `.tasks/<task_id>.json` file.
- JSON is indented UTF-8 and preserves non-ASCII text.
- A saved task can be reloaded with all fields intact.
- Empty task lists and populated task lists produce stable, readable output.
- `get_task` returns complete JSON details.
- IDs remain unique when time and random values collide.

### Dependencies and state transitions

- A missing or incomplete dependency blocks claiming.
- Only `pending` tasks can transition to `in_progress`.
- A successful claim stores the owner.
- Only `in_progress` tasks can transition to `completed`.
- Completing an upstream task allows its downstream task to be claimed.
- Completion preserves the owner and reports newly unblocked downstream work.
- Invalid repeated transitions return clear messages.

### Safety and resilience

- Invalid task IDs cannot escape `TASK_DIR` with absolute paths, separators, or
  `..` traversal.
- Missing tasks return understandable errors through public handlers.
- A corrupt JSON file does not crash task listing or hide valid tasks.
- Public detail access reports corrupt task data clearly.

### Integration and concurrency

- `todo_write` state and durable Task state remain independent.
- The system prompt distinguishes current-session todos from durable tasks.
- Simultaneous claims of one pending task produce at most one successful owner.

## Concurrency Test Strategy

The concurrency test will create one pending task, release several worker threads
at one start barrier, and have each thread call `claim_task` with a distinct
owner. It will assert that exactly one call reports success and that persisted
state contains that winning owner. The test will use a bounded timeout so a lock
bug cannot hang the suite indefinitely.

## Failure Reporting

Tests will use narrow assertions that map directly to the requirement being
checked. A failure means the current BaseAgent does not yet satisfy that s12
requirement; the acceptance suite will not patch or compensate for production
behavior.

The final handoff will report:

- the new test-file path;
- the exact pytest command and result;
- requirements that passed;
- requirements that failed, with corresponding BaseAgent locations;
- concise repair guidance without applying production fixes.

## Verification

Run the focused suite first:

```text
uv run --with pytest pytest tests/test_homework_baseagent_task_system.py -q
```

Then run relevant regressions:

```text
uv run --with pytest pytest \
  tests/test_homework_baseagent_error_recovery.py \
  tests/test_homework_baseagent_todo_resume.py \
  tests/test_compaction_tool_pairs.py -q
```
