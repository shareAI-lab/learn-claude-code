# BaseAgent Layered Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `homework/BaseAgent.py` into an internal layered application package while preserving the executable CLI and existing agent behavior.

**Architecture:** Keep `homework/BaseAgent.py` as a compatibility entry point until the final task. Move code into `homework/agent_app/` from low-coupling pure functions toward stateful features, registries, and finally the Agent Loop; use explicit feature states and a lightweight `RuntimeContext` assembled only in `bootstrap.py`.

**Tech Stack:** Python 3.13, dataclasses, pathlib, threading, Anthropic Python SDK, pytest, uv.

## Global Constraints

- Follow `docs/superpowers/specs/2026-07-31-baseagent-layered-architecture-design.md`.
- Preserve `uv run python homework/BaseAgent.py` at every completed task.
- `homework/BaseAgent.py` is not a public API and must end as a thin CLI entry point.
- Reuse existing function bodies; do not regenerate equivalent implementations.
- Do not combine code movement with unrelated formatting, renaming, or behavior changes.
- Do not make live Anthropic API calls in tests.
- All filesystem tests use `tmp_path`; all thread tests use bounded waits or injected events.
- No module import may create runtime directories, an Anthropic client, or background threads.
- Before execution, the user must establish a recoverable Git baseline containing the current `homework/BaseAgent.py` and the six current BaseAgent test files. Do not stage unrelated dirty-worktree files on the user's behalf.
- Commit steps in this plan assume that approved baseline exists. If it does not, treat the commit step as a review checkpoint and do not stage user changes.

---

## Target File Map

| File | Responsibility |
|---|---|
| `homework/BaseAgent.py` | Temporary compatibility host; final CLI shim |
| `homework/agent_app/config.py` | Immutable paths, models, limits, and timeout configuration |
| `homework/agent_app/runtime.py` | Session state and final `RuntimeContext` |
| `homework/agent_app/bootstrap.py` | Composition root and default registrations |
| `homework/agent_app/cli.py` | Input loop and runtime lifecycle |
| `homework/agent_app/adapters/anthropic.py` | Anthropic SDK and streaming boundary |
| `homework/agent_app/core/loop.py` | Agent turn orchestration |
| `homework/agent_app/core/context.py` | Dynamic runtime context |
| `homework/agent_app/core/prompt.py` | System prompt assembly and cache |
| `homework/agent_app/core/recovery.py` | Retry, model fallback, and continuation state |
| `homework/agent_app/core/compaction.py` | Message compaction and transcript persistence |
| `homework/agent_app/tools/registry.py` | Tool schema/handler snapshots |
| `homework/agent_app/tools/executor.py` | Synchronous and background dispatch decisions |
| `homework/agent_app/tools/builtin.py` | bash/read/write/edit/glob tools |
| `homework/agent_app/tools/hooks.py` | Hook registry and default hooks |
| `homework/agent_app/features/todos.py` | Session-only Todo state |
| `homework/agent_app/features/tasks.py` | Durable task graph |
| `homework/agent_app/features/background.py` | Background tool execution and notifications |
| `homework/agent_app/features/scheduler.py` | Cron jobs and queue |
| `homework/agent_app/features/memory.py` | Long-term memory files and request injection |
| `homework/agent_app/features/skills.py` | Skill discovery and loading |
| `homework/agent_app/features/subagents.py` | Synchronous one-shot subagent |
| `homework/agent_app/features/worktrees.py` | Worktree lifecycle |
| `homework/agent_app/features/mcp.py` | MCP clients, metadata, and tool discovery |
| `homework/agent_app/features/teams/bus.py` | Mailbox persistence and message bus |
| `homework/agent_app/features/teams/protocol.py` | Permission, plan, and shutdown protocol state |
| `homework/agent_app/features/teams/teammates.py` | Teammate lifecycle and idle work |

## Compatibility Strategy

Until Task 14, `BaseAgent.py` may explicitly import moved symbols so its remaining local code
continues to run:

```python
from agent_app.core.recovery import (
    PartialStreamError,
    RecoveryState,
    is_prompt_too_long_error,
    retry_delay,
    with_retry,
)
```

These imports are temporary internal wiring, not supported re-exports. Task 15 deletes them
when the Agent Loop and CLI move.

---

### Task 1: Stabilize the Refactor Baseline

**Files:**
- Modify: `homework/BaseAgent.py:263`
- Modify: `tests/test_homework_baseagent_todo_resume.py`
- Modify: `tests/test_homework_baseagent_error_recovery.py`
- Modify: `tests/test_homework_baseagent_compact_tool.py`
- Modify: `tests/test_homework_baseagent_task_system.py`
- Modify: `tests/test_homework_baseagent_background_tasks.py`
- Modify: `tests/test_homework_baseagent_agent_teams.py`

**Interfaces:**
- Consumes: Current canonical `BUILTIN_TOOLS`, `BUILTIN_HANDLERS`, `assemble_tool_pool()`, `start_background_task(block, handlers)`, `update_context(context, messages, tools=None)`, and `run_agent_turn_locked(user_query=None)`.
- Produces: A green offline baseline that tests the current intended contracts without relying on removed aliases.

- [ ] **Step 1: Update stale tool registry assertions**

Replace every test lookup of `baseagent["TOOLS"]` and
`baseagent["TOOL_HANDLERS"]` with the canonical names:

```python
schemas = {
    tool["name"]: tool
    for tool in baseagent["BUILTIN_TOOLS"]
}
handlers = baseagent["BUILTIN_HANDLERS"]
```

Keep dynamic MCP assertions against `assemble_tool_pool()` rather than a static list.

- [ ] **Step 2: Update Agent Loop test doubles to the current context signature**

Every fake `update_context` used by loop tests must accept the optional tool snapshot:

```python
def fake_update_context(context, messages, tools=None):
    return context
```

Replace two-argument lambdas in error-recovery, background, team, and compact tests with this
function.

Every direct streaming call supplies the current tool snapshot:

```python
result = baseagent["create_message_streaming"](
    system="system",
    request_messages=[{"role": "user", "content": "test"}],
    model="primary-model",
    max_tokens=8_000,
    tools=baseagent["BUILTIN_TOOLS"],
)
```

- [ ] **Step 3: Update background task tests to pass a handler snapshot**

Direct calls use:

```python
bg_id = baseagent["start_background_task"](
    block,
    baseagent["BUILTIN_HANDLERS"],
)
```

Agent Loop fakes accept both arguments:

```python
def fake_start_background(block, handlers):
    captured.append((block, handlers))
    return "bg_0001"
```

Replace the removed `run_agent_turn(history, content, context)` test call with the current
session-owned turn:

```python
baseagent["session_history"].clear()
baseagent["session_context"].clear()
baseagent["run_agent_turn_locked"]("new question")
```

- [ ] **Step 4: Align current extended task and teammate contracts**

The current `Task` includes worktree binding, so assert:

```python
assert [field.name for field in fields(baseagent["Task"])] == [
    "id",
    "subject",
    "description",
    "status",
    "owner",
    "blockedBy",
    "worktree",
]
```

Make the task detail handler report corrupt JSON instead of leaking it:

```python
def run_get_task(task_id: str) -> str:
    try:
        return get_task(task_id)
    except (OSError, ValueError, TypeError) as exc:
        return f"Error: cannot read task {task_id}: {exc}"
```

The teammate history includes its identity message before the assigned prompt:

```python
assert captured_calls[0]["messages"] == [
    {
        "role": "user",
        "content": (
            "<identity>You are 'researcher', role: "
            "Repository investigator. Continue your work.</identity>"
        ),
    },
    {"role": "user", "content": "Inspect tests"},
]
```

- [ ] **Step 5: Restore the required mailbox path and remove real idle waits from tests**

Change the production default to:

```python
MAILBOX_DIR = WORKDIR / ".mailboxes"
```

In the team fixture set bounded test values:

```python
monkeypatch.setitem(globals_, "IDLE_POLL_INTERVAL", 1)
monkeypatch.setitem(globals_, "IDLE_TIMEOUT", 0)
monkeypatch.setitem(globals_, "PERMISSION_POLL_INTERVAL", 0)
monkeypatch.setitem(globals_, "PERMISSION_TIMEOUT", 0)
```

Tests that specifically exercise polling override these values and use an Event rather than
wall-clock sleep.

- [ ] **Step 6: Test the stabilized contract**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider \
  tests/test_homework_baseagent_todo_resume.py \
  tests/test_homework_baseagent_error_recovery.py \
  tests/test_homework_baseagent_compact_tool.py \
  tests/test_homework_baseagent_task_system.py \
  tests/test_homework_baseagent_background_tasks.py \
  tests/test_homework_baseagent_agent_teams.py -q
```

Expected: PASS with no test exceeding five seconds because of internal polling.

- [ ] **Step 7: Commit the baseline**

```bash
git add homework/BaseAgent.py tests/test_homework_baseagent_*.py
git commit -m "test: stabilize BaseAgent refactor baseline"
```

---

### Task 2: Create the Internal Package and Immutable Configuration

**Files:**
- Create: `homework/agent_app/__init__.py`
- Create: `homework/agent_app/config.py`
- Create: `homework/agent_app/runtime.py`
- Create: `tests/homework_agent_app_fakes.py`
- Create: `tests/test_homework_agent_app_foundation.py`

**Interfaces:**
- Consumes: Environment variables and path defaults currently declared at `homework/BaseAgent.py:17-33`.
- Produces: `AppConfig.from_env(repo_root) -> AppConfig` and `SessionState`.

- [ ] **Step 1: Write failing configuration tests**

```python
def test_app_config_derives_all_paths_without_creating_them(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "primary")
    monkeypatch.setenv("FALLBACK_MODEL_ID", "fallback")

    config = AppConfig.from_env(tmp_path)

    assert config.workdir == tmp_path
    assert config.skills_dir == tmp_path / "skills"
    assert config.memory_dir == tmp_path / ".memory"
    assert config.task_dir == tmp_path / ".tasks"
    assert config.mailbox_dir == tmp_path / ".mailboxes"
    assert config.primary_model == "primary"
    assert config.fallback_model == "fallback"
    assert not config.memory_dir.exists()
    assert not config.task_dir.exists()
    assert not config.mailbox_dir.exists()


def test_session_state_is_fresh_per_instance():
    first = SessionState()
    second = SessionState()

    first.history.append({"role": "user", "content": "one"})

    assert second.history == []
    assert second.context == {}
    assert second.todos == []
```

- [ ] **Step 2: Verify the tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_agent_app_foundation.py -q
```

Expected: FAIL because `homework.agent_app.config` and `runtime` do not exist.

- [ ] **Step 3: Implement immutable configuration**

Create `config.py` with this complete public shape:

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    repo_root: Path
    workdir: Path
    skills_dir: Path
    memory_dir: Path
    memory_index: Path
    transcripts_dir: Path
    tool_result_dir: Path
    task_dir: Path
    mailbox_dir: Path
    scheduled_tasks_path: Path
    worktrees_dir: Path
    primary_model: str
    fallback_model: str | None
    default_max_tokens: int = 8_000
    escalated_max_tokens: int = 64_000
    max_continuations: int = 3
    max_transient_retries: int = 10
    max_reactive_compacts: int = 1
    base_delay_ms: int = 500
    max_consecutive_529: int = 3
    context_limit: int = 50_000
    keep_recent: int = 3
    persist_threshold: int = 20_000
    idle_poll_interval: float = 5.0
    idle_timeout: float = 60.0
    permission_poll_interval: float = 0.5
    permission_timeout: float = 300.0

    @classmethod
    def from_env(cls, repo_root: Path) -> "AppConfig":
        root = repo_root.resolve()
        workdir = root
        memory_dir = workdir / ".memory"
        tool_result_dir = workdir / ".task_outputs" / "tool-results"
        return cls(
            repo_root=root,
            workdir=workdir,
            skills_dir=workdir / "skills",
            memory_dir=memory_dir,
            memory_index=memory_dir / "MEMORY.md",
            transcripts_dir=workdir / ".transcripts",
            tool_result_dir=tool_result_dir,
            task_dir=workdir / ".tasks",
            mailbox_dir=workdir / ".mailboxes",
            scheduled_tasks_path=workdir / ".scheduled_tasks.json",
            worktrees_dir=workdir / ".worktrees",
            primary_model=os.environ["MODEL_ID"],
            fallback_model=os.getenv("FALLBACK_MODEL_ID"),
        )
```

- [ ] **Step 4: Implement session-owned mutable state**

Create `runtime.py`:

```python
from dataclasses import dataclass, field


@dataclass(slots=True)
class SessionState:
    history: list = field(default_factory=list)
    context: dict = field(default_factory=dict)
    todos: list[dict] = field(default_factory=list)
    rounds_since_todo: int = 0
```

Keep `agent_app/__init__.py` empty except for a module docstring; do not re-export internal
symbols.

- [ ] **Step 5: Add shared response fakes used by later tasks**

Create `tests/homework_agent_app_fakes.py`:

```python
from types import SimpleNamespace


def text_response(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)],
    )


def tool_response(tool_id: str, name: str, tool_input: dict):
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(
                type="tool_use",
                id=tool_id,
                name=name,
                input=tool_input,
            )
        ],
    )


def tool_schema(name: str) -> dict:
    return {
        "name": name,
        "description": f"{name} test tool",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }


class FakeAdapter:
    def __init__(self, responses=()):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)

    def create_streaming(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeSDKClient:
    def __init__(self):
        self.messages = SimpleNamespace(create=None, stream=None)
```

- [ ] **Step 6: Run the foundation tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_agent_app_foundation.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add homework/agent_app tests/homework_agent_app_fakes.py \
  tests/test_homework_agent_app_foundation.py
git commit -m "refactor: add BaseAgent application foundation"
```

---

### Task 3: Extract Error Recovery

**Files:**
- Create: `homework/agent_app/core/__init__.py`
- Create: `homework/agent_app/core/recovery.py`
- Modify: `homework/BaseAgent.py:1546-1694`
- Modify: `tests/test_homework_baseagent_error_recovery.py`

**Interfaces:**
- Consumes: `AppConfig`, a request callable, and exceptions with optional response/status headers.
- Produces: `RecoveryState`, `PartialStreamError`, error classifiers, `retry_delay()`, `with_retry()`, and `append_unrecoverable_error()`.

- [ ] **Step 1: Change recovery tests to import the owning module**

```python
from homework.agent_app.core import recovery


def test_retry_delay_grows_exponentially(monkeypatch):
    monkeypatch.setattr(recovery.random, "uniform", lambda _a, _b: 0)
    assert recovery.retry_delay(0, base_delay_ms=500) == 0.5
    assert recovery.retry_delay(20, base_delay_ms=500) == 32.0
```

Keep Agent Loop integration tests in the same file using the legacy loader until Task 14.

- [ ] **Step 2: Verify the direct module tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_baseagent_error_recovery.py \
  -k "retry_delay or transient_retry_count or switches_model" -q
```

Expected: FAIL because `core.recovery` does not exist.

- [ ] **Step 3: Move recovery code with an explicit configuration boundary**

Move the current recovery classes and functions into `core/recovery.py`. Keep their current
bodies and expose these exact callable contracts:

```text
retry_delay(
    attempt: int,
    retry_after: float | None = None,
    *,
    base_delay_ms: int = 500,
) -> float

with_retry(
    fn,
    state: RecoveryState,
    *,
    max_transient_retries: int = 10,
    max_consecutive_529: int = 3,
    base_delay_ms: int = 500,
)
```

`RecoveryState` receives models explicitly:

```python
@dataclass(slots=True)
class RecoveryState:
    current_model: str
    fallback_model: str | None = None
    consecutive_529: int = 0
    continuation_count: int = 0
    reactive_compact_count: int = 0
    has_escalated: bool = False
```

Do not create or read environment variables in this module.

- [ ] **Step 4: Add temporary BaseAgent wiring**

Import the moved symbols into `BaseAgent.py`. Construct state with the existing model values:

```python
state = RecoveryState(
    current_model=PRIMARY_MODEL,
    fallback_model=FALLBACK_MODEL,
)
```

Pass the existing retry constants to `with_retry()` at each lead, teammate, and subagent call.

- [ ] **Step 5: Run recovery and loop regression tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider tests/test_homework_baseagent_error_recovery.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add homework/BaseAgent.py homework/agent_app/core/recovery.py \
  tests/test_homework_baseagent_error_recovery.py
git commit -m "refactor: extract BaseAgent recovery policy"
```

---

### Task 4: Extract the Compaction Pipeline

**Files:**
- Create: `homework/agent_app/core/compaction.py`
- Modify: `homework/BaseAgent.py:2470-2630`
- Create: `tests/test_homework_agent_app_compaction.py`
- Modify: `tests/test_homework_baseagent_compact_tool.py`

**Interfaces:**
- Consumes: Messages, `AppConfig`, and a summarizer callable.
- Produces: Pure message compaction plus explicit transcript/output persistence functions.

- [ ] **Step 1: Add direct compaction tests**

```python
def test_snip_compact_preserves_tool_pair():
    messages = [
        {"role": "user", "content": "start"},
        {
            "role": "assistant",
            "content": [
                SimpleNamespace(type="tool_use", id="tool-1", name="bash")
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "tool-1", "content": "ok"}
            ],
        },
        *[
            {"role": "assistant", "content": f"message-{index}"}
            for index in range(10)
        ],
    ]

    compacted = snip_compact(messages, max_messages=6)

    assert messages[1] in compacted
    assert messages[2] in compacted
```

Also test that `write_transcript(config, messages)` and
`persist_large_output(config, tool_use_id, output)` write only below configured roots.

- [ ] **Step 2: Verify the tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_agent_app_compaction.py -q
```

Expected: FAIL because `core.compaction` does not exist.

- [ ] **Step 3: Move the exact compaction symbol set**

Move these existing functions without changing their message semantics:

```text
estimate_size
_block_get
_block_type
_message_has_tool_use
_is_tool_result_message
snip_compact
collect_tool_results
build_tool_use_name_map
micro_compact
tool_result_budget
```

Change the side-effecting contracts to:

```text
persist_large_output(config: AppConfig, tool_use_id: str, output: str) -> str
write_transcript(config: AppConfig, messages: list) -> Path
summarize_history(summarize, messages: list) -> str
compact_history(config: AppConfig, summarize, messages: list) -> list
reactive_compact(config: AppConfig, summarize, messages: list) -> list
```

`summarize` is a callable supplied by the caller; `compaction.py` must not import an
Anthropic client.

- [ ] **Step 4: Wire legacy callers through explicit arguments**

Create one config instance in `BaseAgent.py` and pass it plus a local summarizer wrapper into
the moved functions. Keep `compact` as a control-flow branch rather than a normal handler.

- [ ] **Step 5: Run compaction and BaseAgent regressions**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider \
  tests/test_homework_agent_app_compaction.py \
  tests/test_homework_baseagent_compact_tool.py \
  tests/test_homework_baseagent_error_recovery.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add homework/BaseAgent.py homework/agent_app/core/compaction.py \
  tests/test_homework_agent_app_compaction.py \
  tests/test_homework_baseagent_compact_tool.py
git commit -m "refactor: extract BaseAgent compaction pipeline"
```

---

### Task 5: Extract Scheduler State and Cron Behavior

**Files:**
- Create: `homework/agent_app/features/__init__.py`
- Create: `homework/agent_app/features/scheduler.py`
- Modify: `homework/BaseAgent.py:63-260`
- Create: `tests/test_homework_agent_app_scheduler.py`

**Interfaces:**
- Consumes: `AppConfig.scheduled_tasks_path` and an injected clock.
- Produces: `CronJob`, `SchedulerState`, CRUD operations, queue drain, and scheduler loop.

- [ ] **Step 1: Add scheduler tests**

```python
def test_scheduler_state_is_isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")
    config = AppConfig.from_env(tmp_path)
    first = SchedulerState()
    second = SchedulerState()

    job = schedule_job(
        first,
        config,
        "*/5 * * * *",
        "run checks",
        recurring=True,
        durable=False,
    )

    assert isinstance(job, CronJob)
    assert job.id in first.jobs
    assert second.jobs == {}
```

Also port the existing cron validation, one-shot, durable-load, and duplicate-minute tests.

- [ ] **Step 2: Verify scheduler tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_agent_app_scheduler.py -q
```

Expected: FAIL because `features.scheduler` does not exist.

- [ ] **Step 3: Implement scheduler-owned state**

```python
@dataclass(slots=True)
class SchedulerState:
    jobs: dict[str, CronJob] = field(default_factory=dict)
    queue: list[CronJob] = field(default_factory=list)
    last_fired: dict[str, str] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
```

Move cron functions and replace their global registries with `SchedulerState`.
`cron_scheduler_loop(state, config, stop_event, now=datetime.now)` receives every dependency
explicitly.

- [ ] **Step 4: Add temporary BaseAgent scheduler state**

```python
SCHEDULER_STATE = SchedulerState()
```

Keep current wrapper names in `BaseAgent.py` and delegate to the new module so CLI behavior
remains unchanged.

- [ ] **Step 5: Run scheduler and related Agent Loop tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider \
  tests/test_homework_agent_app_scheduler.py \
  tests/test_homework_baseagent_background_tasks.py \
  tests/test_homework_baseagent_error_recovery.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add homework/BaseAgent.py homework/agent_app/features/scheduler.py \
  tests/test_homework_agent_app_scheduler.py
git commit -m "refactor: extract BaseAgent scheduler"
```

---

### Task 6: Extract Todo, Skill, and Memory Features

**Files:**
- Create: `homework/agent_app/features/todos.py`
- Create: `homework/agent_app/features/skills.py`
- Create: `homework/agent_app/features/memory.py`
- Modify: `homework/BaseAgent.py:1696-2028`
- Modify: `tests/test_homework_baseagent_todo_resume.py`
- Create: `tests/test_homework_agent_app_memory_skills.py`

**Interfaces:**
- Consumes: `SessionState`, `AppConfig.skills_dir`, `memory_dir`, and `memory_index`.
- Produces: Todo operations, `SkillState`, and `MemoryStore` operations.

- [ ] **Step 1: Write direct feature tests**

```python
def test_todo_update_is_session_owned():
    session = SessionState()
    result = run_todo_write(
        session,
        [{"content": "inspect", "status": "in_progress"}],
    )
    assert result == "Updated 1 tasks"
    assert session.todos == [{"content": "inspect", "status": "in_progress"}]


def test_skill_scan_has_no_import_time_side_effect(tmp_path):
    state = SkillState(root=tmp_path / "skills")
    assert state.registry == {}
    assert not state.root.exists()
```

Add memory tests using a temporary `MemoryStore`.

- [ ] **Step 2: Verify feature tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_baseagent_todo_resume.py \
  tests/test_homework_agent_app_memory_skills.py -q
```

Expected: FAIL on the new direct imports.

- [ ] **Step 3: Implement explicit feature state**

```python
@dataclass(slots=True)
class SkillState:
    root: Path
    registry: dict[str, dict] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MemoryStore:
    root: Path
    index_path: Path
```

Move Todo functions to accept `SessionState`, skill functions to accept `SkillState`, and
memory functions to accept `MemoryStore`. Request-memory functions receive the summarizer or
client callable explicitly.

- [ ] **Step 4: Delegate from BaseAgent during migration**

Create one temporary `SessionState`, `SkillState`, and `MemoryStore` in `BaseAgent.py`.
Replace direct global mutations with wrapper calls while preserving current function names for
the not-yet-migrated Agent Loop.

- [ ] **Step 5: Run Todo, memory, skill, and loop regressions**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider \
  tests/test_homework_baseagent_todo_resume.py \
  tests/test_homework_agent_app_memory_skills.py \
  tests/test_homework_baseagent_error_recovery.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add homework/BaseAgent.py homework/agent_app/features/todos.py \
  homework/agent_app/features/skills.py homework/agent_app/features/memory.py \
  tests/test_homework_baseagent_todo_resume.py \
  tests/test_homework_agent_app_memory_skills.py
git commit -m "refactor: extract BaseAgent session features"
```

---

### Task 7: Extract Durable Tasks and Worktrees

**Files:**
- Create: `homework/agent_app/features/tasks.py`
- Create: `homework/agent_app/features/worktrees.py`
- Modify: `homework/BaseAgent.py:1136-1262`
- Modify: `homework/BaseAgent.py:1434-1544`
- Modify: `tests/test_homework_baseagent_task_system.py`
- Create: `tests/test_homework_agent_app_worktrees.py`

**Interfaces:**
- Consumes: Configured task/worktree roots and an injected Git runner.
- Produces: `TaskStore`, task graph operations, `WorktreeState`, and worktree operations.

- [ ] **Step 1: Convert task tests to an explicit store**

```python
@pytest.fixture
def task_store(tmp_path):
    root = tmp_path / ".tasks"
    root.mkdir()
    return TaskStore(root=root)


def test_task_creation_is_store_scoped(task_store):
    task = create_task(task_store, "inspect parser")
    assert load_task(task_store, task.id).subject == "inspect parser"
```

Keep the existing state-transition, path-safety, corrupt-file, and simultaneous-claim
assertions.

- [ ] **Step 2: Add worktree tests with a fake Git runner**

```python
def test_create_worktree_uses_injected_runner(tmp_path):
    calls = []
    state = WorktreeState(
        workdir=tmp_path,
        root=tmp_path / ".worktrees",
        run_git=lambda args: calls.append(args) or (True, "ok"),
    )
    result = create_worktree(state, "feature-a")
    assert "feature-a" in result
    assert calls[0][:2] == ["worktree", "add"]
```

- [ ] **Step 3: Verify direct feature tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_baseagent_task_system.py \
  tests/test_homework_agent_app_worktrees.py -q
```

Expected: FAIL until the tests import the new owner modules.

- [ ] **Step 4: Move task storage behind `TaskStore`**

```python
@dataclass(slots=True)
class TaskStore:
    root: Path
    lock: threading.Lock = field(default_factory=threading.Lock)
```

Move `_task_path`, save/load/list/get/create/can-start/claim/complete and their tool wrappers.
Every function that touches task storage receives `TaskStore`.

- [ ] **Step 5: Move worktree operations behind `WorktreeState`**

```python
@dataclass(slots=True)
class WorktreeState:
    workdir: Path
    root: Path
    run_git: Callable[[list[str]], tuple[bool, str]]
    lock: threading.Lock = field(default_factory=threading.Lock)
```

Pass `TaskStore` only to the worktree functions that bind a task; do not let
`worktrees.py` import a global task store.

- [ ] **Step 6: Run task and worktree tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider \
  tests/test_homework_baseagent_task_system.py \
  tests/test_homework_agent_app_worktrees.py \
  tests/test_homework_baseagent_agent_teams.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add homework/BaseAgent.py homework/agent_app/features/tasks.py \
  homework/agent_app/features/worktrees.py \
  tests/test_homework_baseagent_task_system.py \
  tests/test_homework_agent_app_worktrees.py
git commit -m "refactor: extract BaseAgent task and worktree features"
```

---

### Task 8: Extract Builtin Tools and Hooks

**Files:**
- Create: `homework/agent_app/tools/__init__.py`
- Create: `homework/agent_app/tools/builtin.py`
- Create: `homework/agent_app/tools/hooks.py`
- Modify: `homework/BaseAgent.py:2034-2213`
- Modify: `homework/BaseAgent.py:2633-2752`
- Create: `tests/test_homework_agent_app_tools.py`

**Interfaces:**
- Consumes: `AppConfig.workdir`, hook callbacks, and user confirmation input.
- Produces: Path-safe builtin functions and `HookRegistry`.

- [ ] **Step 1: Add path and hook isolation tests**

```python
def test_safe_path_rejects_escape(tmp_path):
    with pytest.raises(ValueError):
        safe_path(tmp_path, "../outside")


def test_hook_registries_do_not_share_callbacks():
    first = HookRegistry()
    second = HookRegistry()
    first.register("Stop", lambda _messages: "first")
    assert second.trigger("Stop", []) is None
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_agent_app_tools.py -q
```

Expected: FAIL because the owner modules do not exist.

- [ ] **Step 3: Move builtin tools with explicit roots**

Use these exact callable contracts while moving the current bodies:

```text
resolve_tool_cwd(workdir: Path, cwd: str | Path | None = None) -> Path
safe_path(workdir: Path, path: str, cwd: str | Path | None = None) -> Path
run_bash(workdir: Path, command: str, run_in_background: bool = False, cwd=None) -> str
run_read(workdir: Path, path: str, offset: int = 0, limit: int | None = None, cwd=None) -> str
run_write(workdir: Path, path: str, content: str, cwd=None) -> str
run_edit(workdir: Path, path: str, old_text: str, new_text: str, cwd=None) -> str
run_glob(workdir: Path, pattern: str, cwd=None) -> str
```

Do not read a module-level `WORKDIR`.

- [ ] **Step 4: Implement instance-owned hooks**

```python
@dataclass(slots=True)
class HookRegistry:
    callbacks: dict[str, list[Callable]] = field(
        default_factory=lambda: {
            "UserPromptSubmit": [],
            "PreToolUse": [],
            "PostToolUse": [],
            "Stop": [],
        }
    )

    def register(self, event: str, callback: Callable) -> None:
        self.callbacks[event].append(callback)

    def trigger(self, event: str, *args):
        for callback in self.callbacks[event]:
            result = callback(*args)
            if result is not None:
                return result
        return None
```

Default permission, logging, output, context, summary, and diff hooks become factory functions
that close over the configured root and confirmation callback.

- [ ] **Step 5: Run tool, subagent, and team regressions**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider \
  tests/test_homework_agent_app_tools.py \
  tests/test_homework_baseagent_agent_teams.py \
  tests/test_homework_baseagent_background_tasks.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add homework/BaseAgent.py homework/agent_app/tools \
  tests/test_homework_agent_app_tools.py
git commit -m "refactor: extract BaseAgent builtin tools and hooks"
```

---

### Task 9: Extract Background Execution

**Files:**
- Create: `homework/agent_app/features/background.py`
- Create: `homework/agent_app/tools/executor.py`
- Modify: `homework/BaseAgent.py:1036-1134`
- Modify: `tests/test_homework_baseagent_background_tasks.py`

**Interfaces:**
- Consumes: Handler snapshot, post-tool callback, and output persistence callback.
- Produces: `BackgroundState`, dispatch policy, executor, worker start, and notification drain.

- [ ] **Step 1: Rewrite the fixture around `BackgroundState`**

```python
@pytest.fixture
def background_state():
    return BackgroundState()


def test_background_states_are_isolated():
    first = BackgroundState()
    second = BackgroundState()
    first.tasks["bg_0001"] = {"status": "running"}
    assert second.tasks == {}
```

- [ ] **Step 2: Verify background tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_baseagent_background_tasks.py -q
```

Expected: FAIL on direct `BackgroundState` imports.

- [ ] **Step 3: Implement owned background state**

```python
@dataclass(slots=True)
class BackgroundState:
    counter: int = 0
    tasks: dict[str, dict] = field(default_factory=dict)
    results: dict[str, str] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
```

Move `start_background_task` and `collect_background_results`. The exact worker-start contract
is:

```text
start_background_task(
    state: BackgroundState,
    block,
    handlers: dict,
    *,
    post_tool: Callable,
    persist_output: Callable[[str, str], str],
) -> str
```

- [ ] **Step 4: Move execution policy into `tools/executor.py`**

Move `is_slow_operation`, `should_run_background`, and `execute_tool`.
`execute_tool(block, handlers)` must never fall back to a module global handler map.

- [ ] **Step 5: Run background and loop regression tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider \
  tests/test_homework_baseagent_background_tasks.py \
  tests/test_homework_baseagent_error_recovery.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add homework/BaseAgent.py homework/agent_app/features/background.py \
  homework/agent_app/tools/executor.py \
  tests/test_homework_baseagent_background_tasks.py
git commit -m "refactor: extract BaseAgent background execution"
```

---

### Task 10: Extract Team Bus and Protocol State

**Files:**
- Create: `homework/agent_app/features/teams/__init__.py`
- Create: `homework/agent_app/features/teams/bus.py`
- Create: `homework/agent_app/features/teams/protocol.py`
- Modify: `homework/BaseAgent.py:262-526`
- Modify: `homework/BaseAgent.py:843-1034`
- Modify: `tests/test_homework_baseagent_agent_teams.py`

**Interfaces:**
- Consumes: Configured mailbox root, clock, sleep, and hook callback.
- Produces: `MessageBus`, `ProtocolStore`, request matching, permission processing, and lead inbox drain.

- [ ] **Step 1: Convert mailbox tests to construct `MessageBus` directly**

```python
@pytest.fixture
def bus(tmp_path):
    root = tmp_path / ".mailboxes"
    root.mkdir()
    return MessageBus(root=root)


def test_bus_consumes_each_message_once(bus):
    bus.send("lead", "worker", "hello")
    assert [message["content"] for message in bus.read_inbox("worker")] == ["hello"]
    assert bus.read_inbox("worker") == []
```

- [ ] **Step 2: Add protocol-store isolation test**

```python
def test_protocol_stores_do_not_share_requests():
    first = ProtocolStore()
    second = ProtocolStore()
    first.pending["req_1"] = ProtocolState(
        request_id="req_1",
        type="shutdown",
        sender="lead",
        target="worker",
        status="pending",
        payload="",
    )
    assert second.pending == {}
```

- [ ] **Step 3: Verify direct team tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_baseagent_agent_teams.py \
  -k "mailbox or protocol or permission" -q
```

Expected: FAIL until tests import the new modules.

- [ ] **Step 4: Move bus code without global paths**

```python
@dataclass(slots=True)
class MessageBus:
    root: Path
    lock: threading.RLock = field(default_factory=threading.RLock)
```

`mailbox_path(bus, agent)` resolves under `bus.root`. Directory creation occurs in bootstrap,
not module import.

- [ ] **Step 5: Move protocol code behind `ProtocolStore`**

```python
@dataclass(slots=True)
class ProtocolStore:
    pending: dict[str, ProtocolState] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)
```

Permission processing receives `MessageBus`, `ProtocolStore`, hook callback, tool cwd resolver,
clock, and sleep explicitly.

- [ ] **Step 6: Run team protocol tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider tests/test_homework_baseagent_agent_teams.py \
  -k "mailbox or protocol or permission or inbox" -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add homework/BaseAgent.py homework/agent_app/features/teams \
  tests/test_homework_baseagent_agent_teams.py
git commit -m "refactor: extract BaseAgent team bus and protocols"
```

---

### Task 11: Extract Teammates and Subagents

**Files:**
- Create: `homework/agent_app/features/teams/teammates.py`
- Create: `homework/agent_app/features/subagents.py`
- Modify: `homework/BaseAgent.py:375-842`
- Modify: `homework/BaseAgent.py:2367-2468`
- Modify: `tests/test_homework_baseagent_agent_teams.py`
- Create: `tests/test_homework_agent_app_subagents.py`

**Interfaces:**
- Consumes: LLM adapter, tool handlers, hooks, task store, worktree state, bus, clock, and sleep.
- Produces: `TeamState`, teammate spawn/idle lifecycle, and one-shot subagent execution.

- [ ] **Step 1: Define teammate-owned lifecycle state in tests**

```python
def test_team_states_are_isolated():
    first = TeamState()
    second = TeamState()
    first.active["worker"] = {"status": "running"}
    assert second.active == {}
```

- [ ] **Step 2: Add a fake-adapter subagent test**

```python
def test_subagent_uses_fresh_history(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")
    config = AppConfig.from_env(tmp_path)
    fake_adapter = FakeAdapter([text_response("done")])
    result = spawn_subagent(
        description="inspect parser",
        llm=fake_adapter,
        config=config,
        system="subagent system",
        tools=[],
        handlers={},
        hooks=HookRegistry(),
    )
    assert result == "done"
    assert fake_adapter.calls[0]["messages"] == [
        {"role": "user", "content": "inspect parser"}
    ]
```

- [ ] **Step 3: Verify lifecycle tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_baseagent_agent_teams.py \
  tests/test_homework_agent_app_subagents.py \
  -k "teammate or subagent or idle" -q
```

Expected: FAIL until the implementations move.

- [ ] **Step 4: Move teammate lifecycle with injected dependencies**

```python
@dataclass(slots=True)
class TeamState:
    active: dict[str, dict] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
```

`spawn_teammate_thread()` receives `TeamState`, `MessageBus`, LLM adapter, task/worktree
dependencies, tool registry snapshot, hooks, and timing functions. Preserve the current
identity message, guarded-tool permission flow, plan protocol, and cleanup behavior.

- [ ] **Step 5: Move the synchronous subagent loop**

`subagents.py` must not import a global client, hooks, or handler map. Keep recursion disabled
by accepting the explicit five-tool subagent schema and handlers. Its entry contract is
`spawn_subagent(description, llm, config, system, tools, handlers, hooks) -> str`.

- [ ] **Step 6: Run complete team and subagent tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider \
  tests/test_homework_baseagent_agent_teams.py \
  tests/test_homework_agent_app_subagents.py \
  tests/test_homework_baseagent_error_recovery.py -q
```

Expected: PASS without real idle waits.

- [ ] **Step 7: Commit**

```bash
git add homework/BaseAgent.py \
  homework/agent_app/features/teams/teammates.py \
  homework/agent_app/features/subagents.py \
  tests/test_homework_baseagent_agent_teams.py \
  tests/test_homework_agent_app_subagents.py
git commit -m "refactor: extract BaseAgent agent runtimes"
```

---

### Task 12: Extract MCP and Build the Tool Registry

**Files:**
- Create: `homework/agent_app/features/mcp.py`
- Create: `homework/agent_app/tools/registry.py`
- Modify: `homework/BaseAgent.py:1263-1433`
- Modify: `homework/BaseAgent.py:2214-2365`
- Create: `tests/test_homework_agent_app_tool_registry.py`
- Modify: `tests/test_homework_baseagent_compact_tool.py`

**Interfaces:**
- Consumes: Feature registration functions and MCP client definitions.
- Produces: `MCPState`, `ToolRegistry`, immutable per-round schema/handler snapshots.

- [ ] **Step 1: Add registry tests**

```python
def test_registry_rejects_duplicate_names():
    registry = ToolRegistry()
    registry.register(tool_schema("bash"), lambda: "one")
    with pytest.raises(ValueError, match="duplicate"):
        registry.register(tool_schema("bash"), lambda: "two")


def test_snapshots_do_not_change_after_later_registration():
    registry = ToolRegistry()
    registry.register(tool_schema("bash"), lambda: "ok")
    tools, handlers = registry.snapshot()
    registry.register(tool_schema("read_file"), lambda: "ok")
    assert [item["name"] for item in tools] == ["bash"]
    assert set(handlers) == {"bash"}
```

- [ ] **Step 2: Verify registry tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_agent_app_tool_registry.py -q
```

Expected: FAIL because the registry does not exist.

- [ ] **Step 3: Implement the registry**

```python
@dataclass(slots=True)
class ToolRegistry:
    _tools: dict[str, dict] = field(default_factory=dict)
    _handlers: dict[str, Callable] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
```

`compact` is registered with `handler=None`; `snapshot()` omits it from handlers.
Return copied schemas and handlers sorted by registration order.
Implement these methods using the behavior asserted in Step 1:

```text
register(schema: dict, handler: Callable | None = None) -> None
snapshot() -> tuple[list[dict], dict[str, Callable]]
```

- [ ] **Step 4: Move MCP state and discovery**

```python
@dataclass(slots=True)
class MCPState:
    clients: dict[str, MCPClient] = field(default_factory=dict)
    metadata: dict[str, dict] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)
```

Move `MCPClient`, mock servers, normalization, connection, and tool discovery. MCP snapshot
building receives the builtin `ToolRegistry` snapshot and never mutates it.

- [ ] **Step 5: Replace static append-time registration**

Create explicit registration functions in the owning modules and call them from temporary
BaseAgent wiring:

```python
register_builtin_tools(registry, builtin_dependencies)
register_todo_tools(registry, session)
register_task_tools(registry, task_store)
register_scheduler_tools(registry, scheduler_state, config)
register_team_tools(registry, team_dependencies)
register_worktree_tools(registry, worktree_state, task_store)
register_subagent_tool(registry, subagent_dependencies)
register_mcp_connection_tool(registry, mcp_state)
```

- [ ] **Step 6: Run registry and contract regressions**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider \
  tests/test_homework_agent_app_tool_registry.py \
  tests/test_homework_baseagent_compact_tool.py \
  tests/test_homework_baseagent_task_system.py \
  tests/test_homework_baseagent_agent_teams.py \
  tests/test_homework_baseagent_background_tasks.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add homework/BaseAgent.py homework/agent_app/features/mcp.py \
  homework/agent_app/tools/registry.py \
  tests/test_homework_agent_app_tool_registry.py \
  tests/test_homework_baseagent_compact_tool.py
git commit -m "refactor: add BaseAgent tool registry"
```

---

### Task 13: Extract Anthropic Adapter, Context, and Prompt

**Files:**
- Create: `homework/agent_app/adapters/__init__.py`
- Create: `homework/agent_app/adapters/anthropic.py`
- Create: `homework/agent_app/core/context.py`
- Create: `homework/agent_app/core/prompt.py`
- Modify: `homework/BaseAgent.py:2754-2858`
- Modify: `homework/BaseAgent.py:3114-3157`
- Create: `tests/test_homework_agent_app_anthropic_adapter.py`
- Create: `tests/test_homework_agent_app_context_prompt.py`

**Interfaces:**
- Consumes: Anthropic SDK client, config, runtime-owned states, and registry snapshots.
- Produces: `AnthropicAdapter`, context dict, prompt builder/cache, and message-block append helper.

- [ ] **Step 1: Write streaming adapter tests**

```python
def test_streaming_adapter_wraps_failure_after_visible_text(capsys):
    cause = RuntimeError("lost")

    class FailingStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        @property
        def text_stream(self):
            def chunks():
                yield "visible"
                raise cause
            return chunks()

        def get_final_message(self):
            raise AssertionError("failed stream has no final message")

    client = SimpleNamespace(
        messages=SimpleNamespace(
            stream=lambda **_kwargs: FailingStream(),
        )
    )
    adapter = AnthropicAdapter(client)

    with pytest.raises(PartialStreamError) as caught:
        adapter.create_streaming(
            system="system",
            messages=[],
            model="model",
            max_tokens=100,
            tools=[],
        )

    assert caught.value.partial_text == "visible"
    assert capsys.readouterr().out == "visible\n"
```

- [ ] **Step 2: Write context and prompt tests**

```python
def test_context_uses_runtime_snapshots(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")
    config = AppConfig.from_env(tmp_path)
    session = SessionState(
        todos=[{"content": "inspect", "status": "in_progress"}]
    )
    tools = ToolRegistry()
    tools.register(tool_schema("echo_tool"), lambda: "ok")
    tool_schemas, _handlers = tools.snapshot()
    runtime_view = SimpleNamespace(
        config=config,
        session=session,
        skills=SkillState(root=config.skills_dir),
        memory=MemoryStore(
            root=config.memory_dir,
            index_path=config.memory_index,
        ),
        team=TeamState(),
        mcp=MCPState(),
    )

    context = build_context(runtime_view, tool_schemas)

    assert context["workspace"] == str(config.workdir)
    assert context["enabled_tools"] == sorted(context["enabled_tools"])
    assert context["todos"] == format_current_todos(session)


def test_prompt_cache_is_instance_owned():
    first = PromptBuilder()
    second = PromptBuilder()
    assert first.build({"enabled_tools": []}) == second.build({"enabled_tools": []})
    assert first is not second
```

- [ ] **Step 3: Verify tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_agent_app_anthropic_adapter.py \
  tests/test_homework_agent_app_context_prompt.py -q
```

Expected: FAIL until the modules exist.

- [ ] **Step 4: Move the SDK boundary**

`AnthropicAdapter` receives an already-created SDK client. It implements these exact methods
using the current non-streaming and streaming request bodies:

```text
create(*, system, messages, model, max_tokens, tools)
create_streaming(*, system, messages, model, max_tokens, tools)
```

Move all stream chunk printing and `PartialStreamError` wrapping into the adapter.

- [ ] **Step 5: Move context and prompt construction**

`build_context(runtime, tools)` reads state without mutating it. `PromptBuilder` owns its
cache fields instead of module globals:

```python
@dataclass(slots=True)
class PromptBuilder:
    last_key: str | None = None
    last_prompt: str | None = None
```

Implement `build(context: dict) -> str` with the existing
`assemble_system_prompt()`/`get_system_prompt()` behavior and instance-owned cache fields.
Move `append_user_text_blocks()` into `core/context.py`.

- [ ] **Step 6: Run adapter, context, recovery, and team tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider \
  tests/test_homework_agent_app_anthropic_adapter.py \
  tests/test_homework_agent_app_context_prompt.py \
  tests/test_homework_baseagent_error_recovery.py \
  tests/test_homework_baseagent_agent_teams.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add homework/BaseAgent.py homework/agent_app/adapters \
  homework/agent_app/core/context.py homework/agent_app/core/prompt.py \
  tests/test_homework_agent_app_anthropic_adapter.py \
  tests/test_homework_agent_app_context_prompt.py
git commit -m "refactor: extract BaseAgent model boundary"
```

---

### Task 14: Build RuntimeContext and Extract the Agent Loop

**Files:**
- Modify: `homework/agent_app/runtime.py`
- Create: `homework/agent_app/core/loop.py`
- Modify: `homework/BaseAgent.py:2860-3112`
- Create: `tests/test_homework_agent_app_loop.py`
- Modify: `tests/test_homework_baseagent_error_recovery.py`
- Modify: `tests/test_homework_baseagent_background_tasks.py`
- Modify: `tests/test_homework_baseagent_agent_teams.py`
- Modify: `tests/test_homework_baseagent_compact_tool.py`

**Interfaces:**
- Consumes: All states and adapters created in Tasks 2-13.
- Produces: Final `RuntimeContext` and `run_agent_loop(runtime) -> None`.

- [ ] **Step 1: Define the final runtime shape**

Add this type-consistent `RuntimeContext`:

```python
@dataclass(slots=True)
class RuntimeContext:
    config: AppConfig
    llm: AnthropicAdapter
    session: SessionState
    prompt_builder: PromptBuilder
    tools: ToolRegistry
    hooks: HookRegistry
    scheduler: SchedulerState
    background: BackgroundState
    tasks: TaskStore
    worktrees: WorktreeState
    skills: SkillState
    memory: MemoryStore
    bus: MessageBus
    protocols: ProtocolStore
    team: TeamState
    mcp: MCPState
    agent_lock: threading.Lock = field(default_factory=threading.Lock)
    stop_event: threading.Event = field(default_factory=threading.Event)
```

Do not add business methods to this dataclass.

- [ ] **Step 2: Write a minimal loop fixture and integration test**

```python
@pytest.fixture
def runtime_factory(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")
    config = AppConfig.from_env(tmp_path)
    config.task_dir.mkdir()
    config.mailbox_dir.mkdir()
    config.worktrees_dir.mkdir()

    def make_runtime(responses):
        task_store = TaskStore(root=config.task_dir)
        return RuntimeContext(
            config=config,
            llm=FakeAdapter(responses),
            session=SessionState(),
            prompt_builder=PromptBuilder(),
            tools=ToolRegistry(),
            hooks=HookRegistry(),
            scheduler=SchedulerState(),
            background=BackgroundState(),
            tasks=task_store,
            worktrees=WorktreeState(
                workdir=config.workdir,
                root=config.worktrees_dir,
                run_git=lambda _args: (True, "ok"),
            ),
            skills=SkillState(root=config.skills_dir),
            memory=MemoryStore(
                root=config.memory_dir,
                index_path=config.memory_index,
            ),
            bus=MessageBus(root=config.mailbox_dir),
            protocols=ProtocolStore(),
            team=TeamState(),
            mcp=MCPState(),
        )

    return make_runtime


def test_loop_executes_registered_tool_and_returns(runtime_factory):
    response_items = [
        tool_response("tool-1", "echo_tool", {"value": "hello"}),
        text_response("done"),
    ]
    runtime = runtime_factory(response_items)
    runtime.tools.register(
        tool_schema("echo_tool"),
        lambda value: f"echo:{value}",
    )
    runtime.session.history.append({"role": "user", "content": "run"})

    run_agent_loop(runtime)

    tool_results = [
        block
        for message in runtime.session.history
        if message["role"] == "user" and isinstance(message["content"], list)
        for block in message["content"]
        if isinstance(block, dict) and block.get("type") == "tool_result"
    ]
    assert tool_results[-1]["content"] == "echo:hello"
```

Add focused tests for compact control flow, notifications, permission denial, max tokens,
partial streams, background dispatch, and final teammate activity.

- [ ] **Step 3: Verify the new loop tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_agent_app_loop.py -q
```

Expected: FAIL because `core.loop` does not exist.

- [ ] **Step 4: Move the Agent Loop without feature internals**

Move the current loop and replace every global dependency with a runtime field or an imported
narrow function. Preserve this order:

```text
drain scheduler/background/team notifications
append notification blocks
apply tool-result, snip, and micro compaction
perform automatic compaction
inject Todo reminder
snapshot tools
build context and prompt
build request messages with memories
call adapter through recovery
handle partial stream and max-token continuation
process compact control action
run pre-tool hooks
dispatch background or synchronous tool
run post-tool hooks
append tool results
run Stop hooks and teammate wait
extract/consolidate memories
return
```

The function signature is `run_agent_loop(runtime: RuntimeContext) -> None`.

Messages and dynamic context live only in `runtime.session`.

- [ ] **Step 5: Delete global-namespace test injection**

Move loop-specific assertions from the four legacy test files into
`test_homework_agent_app_loop.py`. Build runtime fixtures with fake adapters and independent
feature states. Remove all uses of:

```python
namespace["agent_loop"].__globals__
monkeypatch.setitem(baseagent, "dependency", replacement)
```

Feature tests continue importing their owner modules.

- [ ] **Step 6: Run all migrated BaseAgent tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider \
  tests/test_homework_agent_app_*.py \
  tests/test_homework_baseagent_*.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add homework/BaseAgent.py homework/agent_app/runtime.py \
  homework/agent_app/core/loop.py tests/test_homework_agent_app_*.py \
  tests/test_homework_baseagent_*.py
git commit -m "refactor: extract BaseAgent core loop"
```

---

### Task 15: Add Bootstrap and CLI, Then Remove the Compatibility Host

**Files:**
- Create: `homework/agent_app/bootstrap.py`
- Create: `homework/agent_app/cli.py`
- Replace: `homework/BaseAgent.py`
- Create: `tests/test_homework_agent_app_bootstrap.py`
- Create: `tests/test_homework_baseagent_cli.py`

**Interfaces:**
- Consumes: `AppConfig` and an optional prebuilt SDK client for tests.
- Produces: `build_runtime(config, sdk_client) -> RuntimeContext`, runtime thread lifecycle, and CLI `main()`.

- [ ] **Step 1: Write bootstrap side-effect tests**

```python
def test_import_does_not_create_runtime_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import homework.agent_app.bootstrap as bootstrap
    assert bootstrap is not None
    assert list(tmp_path.iterdir()) == []


def test_build_runtime_creates_independent_state(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_ID", "test-model")
    config = AppConfig.from_env(tmp_path)
    sdk_client = FakeSDKClient()
    first = build_runtime(config, sdk_client)
    second = build_runtime(config, sdk_client)
    first.session.todos.append({"content": "one", "status": "pending"})
    assert second.session.todos == []
```

- [ ] **Step 2: Write CLI startup and shutdown tests**

```python
def test_cli_exits_without_agent_turn(monkeypatch):
    runtime = SimpleNamespace(stop_event=threading.Event())
    calls = []
    stopped = []

    def stop_threads(seen_runtime, threads):
        seen_runtime.stop_event.set()
        stopped.append(threads)

    monkeypatch.setattr("builtins.input", lambda _prompt: "q")
    main(
        runtime_factory=lambda: runtime,
        run_turn=lambda _runtime: calls.append("turn"),
        start_threads=lambda _runtime: [],
        stop_threads=stop_threads,
    )
    assert calls == []
    assert runtime.stop_event.is_set()
    assert stopped == [[]]
```

The CLI test injects thread lifecycle callbacks and therefore creates no real thread.

- [ ] **Step 3: Verify bootstrap and CLI tests fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_agent_app_bootstrap.py \
  tests/test_homework_baseagent_cli.py -q
```

Expected: FAIL because bootstrap and CLI modules do not exist.

- [ ] **Step 4: Implement the composition root**

`build_runtime()` performs this exact sequence:

```text
create configured storage roots
create AnthropicAdapter
create SessionState and feature states
create HookRegistry and register default hooks
create ToolRegistry and register every feature
construct RuntimeContext
return RuntimeContext
```

It accepts an injected SDK client:

The exact signature is
`build_runtime(config: AppConfig, sdk_client) -> RuntimeContext`.

`build_default_runtime()` is the only function that loads `.env`, handles
`ANTHROPIC_BASE_URL`, and creates `Anthropic`.

- [ ] **Step 5: Implement explicit runtime thread lifecycle**

In `cli.py`, implement these exact callable contracts:

```text
start_runtime_threads(runtime) -> list[threading.Thread]
stop_runtime_threads(runtime, threads) -> None
run_agent_turn(runtime, user_query: str | None = None) -> None
main(
    runtime_factory=build_default_runtime,
    run_turn=run_agent_turn,
    start_threads=start_runtime_threads,
    stop_threads=stop_runtime_threads,
) -> None
```

The scheduler thread only enqueues cron jobs. The queue processor acquires
`runtime.agent_lock` before invoking a turn. Both threads observe `runtime.stop_event`;
`stop_runtime_threads()` sets that event and joins the threads. `main()` calls it in `finally`.

- [ ] **Step 6: Replace BaseAgent.py with the thin entry point**

The complete final file is:

```python
from agent_app.cli import main


if __name__ == "__main__":
    main()
```

Do not re-export legacy globals or internal functions.

- [ ] **Step 7: Run focused CLI and import tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/test_homework_agent_app_bootstrap.py \
  tests/test_homework_baseagent_cli.py \
  tests/test_homework_agent_app_foundation.py -q
```

Expected: PASS.

- [ ] **Step 8: Run the full Python suite**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q
```

Expected: PASS with no live API request and no thread hang.

- [ ] **Step 9: Verify architecture constraints**

Run:

```bash
rg -n "agent_loop.__globals__|runpy.run_path" tests/test_homework_*.py
rg -n "^client = Anthropic|Thread\\(.*start|mkdir\\(" homework/agent_app
wc -l homework/BaseAgent.py
```

Expected:

- the first command has no matches;
- Anthropic construction appears only inside `build_default_runtime()`;
- directory creation appears only in bootstrap/storage initialization functions;
- `homework/BaseAgent.py` is five lines or fewer excluding blank lines.

- [ ] **Step 10: Review and commit the cutover**

```bash
git diff --check
git status --short
git add homework/BaseAgent.py homework/agent_app/bootstrap.py \
  homework/agent_app/cli.py tests/test_homework_agent_app_bootstrap.py \
  tests/test_homework_baseagent_cli.py
git commit -m "refactor: make BaseAgent a thin CLI entry point"
```

---

## Final Verification

- [ ] Run all BaseAgent-specific tests:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest \
  -p no:cacheprovider \
  tests/test_homework_agent_app_*.py \
  tests/test_homework_baseagent_*.py -q
```

- [ ] Run the full Python suite:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q
```

- [ ] Compile every internal module:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python -m compileall -q \
  homework/BaseAgent.py homework/agent_app
```

- [ ] Inspect the final dependency and public-entry constraints:

```bash
rg -n "from .*core\\.loop import|import .*core\\.loop" homework/agent_app/features
rg -n "RuntimeContext" homework/agent_app/features
rg -n "agent_loop.__globals__|runpy.run_path" tests/test_homework_*.py
```

Expected: no feature imports `core.loop`, no feature imports the full `RuntimeContext`, and no
test reads the legacy module global namespace.

- [ ] Inspect the final diff:

```bash
git diff --check
git status --short
```

Expected: only intentional implementation/test changes remain, with unrelated user files
untouched.
