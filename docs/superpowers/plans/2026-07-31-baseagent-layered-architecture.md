# BaseAgent Layered Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `homework/BaseAgent.py` into an internal layered application while preserving its CLI behavior, existing agent capabilities, and testable contracts without turning `BaseAgent.py` into a public API.

**Architecture:** Keep `homework/BaseAgent.py` executable throughout the migration, move one owned capability at a time into `homework/agent_app/`, and pass mutable state explicitly through feature-specific state objects collected by an internal `RuntimeContext`. `bootstrap.py` becomes the only composition root; `core/loop.py` orchestrates narrow feature interfaces; tool and hook registries replace import-time mutation; Anthropic, filesystem, subprocess, and thread side effects remain behind explicit boundaries.

**Tech Stack:** Python 3.13, standard-library dataclasses/threading/pathlib/subprocess, Anthropic Python SDK, PyYAML, python-dotenv, pytest.

## Global Constraints

- Preserve `uv run python homework/BaseAgent.py` at every completed task.
- The final `homework/BaseAgent.py` is a thin CLI entry point and exports no compatibility API.
- Do not restore deprecated `TOOLS` or `TOOL_HANDLERS`; use current `BUILTIN_TOOLS` and `BUILTIN_HANDLERS` until `ToolRegistry` replaces them.
- Preserve the current explicit `compact` schema and special Agent Loop control branch; `compact` has no ordinary handler.
- Move existing function bodies wherever practical; do not regenerate equivalent implementations or combine moves with style rewrites.
- Pure functions remain pure. Stateful feature functions receive their own state, not a global runtime singleton.
- Only `bootstrap.py`, CLI lifecycle code, and the main Agent Loop may receive the complete `RuntimeContext`.
- Importing internal modules must not create runtime directories, load dotenv, create an Anthropic client, register hooks, or start threads.
- Keep all LLM tests offline with fake adapters.
- Keep tool-use/tool-result pairs adjacent and valid through max-token recovery and compaction.
- Scheduler, background, teammate, and CLI threads must not concurrently mutate the lead session history.
- Every task ends with a focused regression command and an independently reviewable commit.
- Preserve unrelated dirty-worktree changes. Before execution, make a user-approved baseline commit containing the current `homework/BaseAgent.py` and BaseAgent tests, then execute from that exact commit.

---

## Target File Map

### Entry and composition

- Modify: `homework/BaseAgent.py` — temporary compatibility host during migration; final thin CLI entry.
- Create: `homework/agent_app/__init__.py` — internal-package marker with no re-exports.
- Create: `homework/agent_app/config.py` — immutable path, model, timeout, retry, and compaction configuration.
- Create: `homework/agent_app/runtime.py` — `SessionState` and internal `RuntimeContext`.
- Create: `homework/agent_app/bootstrap.py` — construct states, adapters, registries, bindings, and runtime.
- Create: `homework/agent_app/cli.py` — input loop and thread lifecycle.

### Core

- Create: `homework/agent_app/core/__init__.py` — package marker.
- Create: `homework/agent_app/core/loop.py` — lead Agent Loop and locked turn entry.
- Create: `homework/agent_app/core/context.py` — dynamic request context and memory injection.
- Create: `homework/agent_app/core/prompt.py` — system prompt assembly and cache.
- Create: `homework/agent_app/core/recovery.py` — retry policy and recovery state.
- Create: `homework/agent_app/core/compaction.py` — message-pair helpers, result budgeting, transcript, and compaction.

### Tools

- Create: `homework/agent_app/tools/__init__.py` — package marker.
- Create: `homework/agent_app/tools/registry.py` — ordered schema/handler registry and snapshots.
- Create: `homework/agent_app/tools/executor.py` — ordinary and background tool dispatch.
- Create: `homework/agent_app/tools/builtin.py` — workspace-safe bash/read/write/edit/glob handlers.
- Create: `homework/agent_app/tools/hooks.py` — hook registry, permissions, audit, and diff preview.

### Features

- Create: `homework/agent_app/features/__init__.py` — package marker.
- Create: `homework/agent_app/features/todos.py` — session Todo state and formatting.
- Create: `homework/agent_app/features/skills.py` — explicit skill catalog scan and load.
- Create: `homework/agent_app/features/memory.py` — memory store, selection, extraction, and consolidation.
- Create: `homework/agent_app/features/tasks.py` — task model and durable task store.
- Create: `homework/agent_app/features/worktrees.py` — worktree state and git operations.
- Create: `homework/agent_app/features/scheduler.py` — cron model, store, queue, and scheduler loop.
- Create: `homework/agent_app/features/background.py` — background registry, workers, and completion drain.
- Create: `homework/agent_app/features/mcp.py` — MCP clients, metadata, and dynamic tool snapshots.
- Create: `homework/agent_app/features/subagents.py` — synchronous one-shot subagent loop.
- Create: `homework/agent_app/features/teams/__init__.py` — package marker.
- Create: `homework/agent_app/features/teams/bus.py` — validated mailbox paths and JSONL message bus.
- Create: `homework/agent_app/features/teams/protocol.py` — permission, shutdown, and plan protocol state.
- Create: `homework/agent_app/features/teams/teammates.py` — teammate lifecycle and idle claiming.

### Adapter

- Create: `homework/agent_app/adapters/__init__.py` — package marker.
- Create: `homework/agent_app/adapters/anthropic.py` — regular and streaming Anthropic calls.

### Tests

- Create: `tests/homework_agent/__init__.py` — test-package marker.
- Create: `tests/homework_agent/conftest.py` — isolated config, fake LLM, registries, and runtime builders.
- Create: `tests/homework_agent/test_imports.py` — import-side-effect tests.
- Create: `tests/homework_agent/test_config_runtime.py` — configuration and state ownership.
- Create: `tests/homework_agent/test_registry.py` — tool/hook registry behavior.
- Create: `tests/homework_agent/test_todos_skills.py` — Todo and skill feature tests.
- Create: `tests/homework_agent/test_tasks_worktrees.py` — durable task and worktree tests.
- Create: `tests/homework_agent/test_scheduler_background.py` — deterministic scheduler/background tests.
- Create: `tests/homework_agent/test_recovery_adapter.py` — retry and streaming tests.
- Create: `tests/homework_agent/test_teams_subagents.py` — team protocol, teammate, and subagent tests.
- Create: `tests/homework_agent/test_memory_compaction.py` — memory and compaction tests.
- Create: `tests/homework_agent/test_mcp.py` — dynamic MCP registration tests.
- Create: `tests/homework_agent/test_loop.py` — lead-loop integration tests.
- Create: `tests/homework_agent/test_cli.py` — thin entry and clean shutdown smoke tests.
- Delete after equivalent coverage is migrated:
  - `tests/test_homework_baseagent_todo_resume.py`
  - `tests/test_homework_baseagent_task_system.py`
  - `tests/test_homework_baseagent_background_tasks.py`
  - `tests/test_homework_baseagent_agent_teams.py`
  - `tests/test_homework_baseagent_error_recovery.py`
  - `tests/test_homework_baseagent_compact_tool.py`

---

### Task 1: Checkpoint and Stabilize the Current BaseAgent Contract

**Files:**
- Modify: `homework/BaseAgent.py:263-264`
- Modify: `homework/BaseAgent.py:2161-2165`
- Modify: `tests/test_homework_baseagent_todo_resume.py`
- Modify: `tests/test_homework_baseagent_task_system.py`
- Modify: `tests/test_homework_baseagent_background_tasks.py`
- Modify: `tests/test_homework_baseagent_agent_teams.py`
- Modify: `tests/test_homework_baseagent_error_recovery.py`

**Interfaces:**
- Consumes: current `BUILTIN_TOOLS`, `BUILTIN_HANDLERS`, `run_agent_turn_locked(user_query=None)`, `start_background_task(block, handlers)`, and `update_context(context, messages, tools=None)`.
- Produces: a green, offline BaseAgent regression baseline that does not require deprecated aliases or real 60-second waits.

- [ ] **Step 1: Create an explicit baseline checkpoint before changing contracts**

Review only the in-scope files:

```bash
git diff -- homework/BaseAgent.py
git status --short -- homework/BaseAgent.py tests/test_homework_baseagent_*.py
```

After the user confirms that these files represent the intended current implementation, commit only them:

```bash
git add homework/BaseAgent.py tests/test_homework_baseagent_todo_resume.py tests/test_homework_baseagent_task_system.py tests/test_homework_baseagent_background_tasks.py tests/test_homework_baseagent_agent_teams.py tests/test_homework_baseagent_error_recovery.py tests/test_homework_baseagent_compact_tool.py
git commit -m "chore: checkpoint BaseAgent implementation"
```

Expected: unrelated working-tree files remain unstaged.

- [ ] **Step 2: Align stale tests with current canonical names and signatures**

Make these exact test-contract changes:

```python
# Registry access
schemas = {
    tool["name"]: tool
    for tool in baseagent["BUILTIN_TOOLS"]
}
handlers = baseagent["BUILTIN_HANDLERS"]

# Agent-loop isolation helpers
def fake_update_context(context, messages, tools=None):
    return context

# Background dispatch
bg_id = baseagent["start_background_task"](
    block,
    baseagent["BUILTIN_HANDLERS"],
)

# Streaming helper calls
result = baseagent["create_message_streaming"](
    system="system",
    request_messages=[{"role": "user", "content": "test"}],
    model="primary-model",
    max_tokens=8_000,
    tools=baseagent["BUILTIN_TOOLS"],
)
```

Update the task dataclass assertion to include the already-supported worktree field:

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

Patch `run_agent_turn_locked`, not removed `run_agent_turn`, in the startup test:

```python
turns = []
monkeypatch.setitem(
    baseagent,
    "run_agent_turn_locked",
    lambda user_query=None: turns.append(user_query),
)
monkeypatch.setattr(builtins, "input", lambda _prompt: "q")
baseagent["main"]()
assert turns == []
```

In the team fixture, replace real idle polling for tests that execute a captured teammate thread:

```python
monkeypatch.setitem(
    globals_,
    "idle_poll",
    lambda *args, **kwargs: "timeout",
)
```

Preserve the newer teammate identity behavior:

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

- [ ] **Step 3: Run the aligned tests and verify remaining production failures**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/test_homework_baseagent_todo_resume.py tests/test_homework_baseagent_error_recovery.py tests/test_homework_baseagent_compact_tool.py tests/test_homework_baseagent_task_system.py tests/test_homework_baseagent_background_tasks.py tests/test_homework_baseagent_agent_teams.py -q
```

Expected: failures no longer mention `TOOLS`, `TOOL_HANDLERS`, missing `run_agent_turn`, missing `handlers`, unexpected `tools`, or a 60-second idle timeout.

- [ ] **Step 4: Fix the two known production contract defects**

Use the required plural mailbox directory:

```python
MAILBOX_DIR = WORKDIR / ".mailboxes"
MAILBOX_DIR.mkdir(exist_ok=True)
```

Return a clear error for corrupt task detail JSON:

```python
def run_get_task(task_id: str) -> str:
    try:
        return get_task(task_id)
    except (OSError, ValueError, TypeError) as exc:
        return f"Error: cannot read task {task_id}: {exc}"
```

- [ ] **Step 5: Verify and commit the green baseline**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/test_homework_baseagent_todo_resume.py tests/test_homework_baseagent_error_recovery.py tests/test_homework_baseagent_compact_tool.py tests/test_homework_baseagent_task_system.py tests/test_homework_baseagent_background_tasks.py tests/test_homework_baseagent_agent_teams.py -q
```

Expected: all selected tests pass without a live API call or long wait.

Commit:

```bash
git add homework/BaseAgent.py tests/test_homework_baseagent_todo_resume.py tests/test_homework_baseagent_task_system.py tests/test_homework_baseagent_background_tasks.py tests/test_homework_baseagent_agent_teams.py tests/test_homework_baseagent_error_recovery.py
git commit -m "test: stabilize BaseAgent refactor baseline"
```

---

### Task 2: Add the Internal Package, Configuration, and Runtime Types

**Files:**
- Create: `homework/agent_app/__init__.py`
- Create: `homework/agent_app/config.py`
- Create: `homework/agent_app/runtime.py`
- Create: `tests/homework_agent/__init__.py`
- Create: `tests/homework_agent/conftest.py`
- Create: `tests/homework_agent/test_config_runtime.py`
- Create: `tests/homework_agent/test_imports.py`

**Interfaces:**
- Consumes: environment keys `MODEL_ID`, `FALLBACK_MODEL_ID`, and repository-root path conventions.
- Produces: `AppConfig.from_env(repo_root=None, environ=None)`, `SessionState`, and `RuntimeContext` without import-time side effects.

- [ ] **Step 1: Write configuration and runtime tests**

Add:

```python
def test_config_derives_all_runtime_paths(tmp_path):
    config = AppConfig.from_env(
        repo_root=tmp_path,
        environ={"MODEL_ID": "test-model"},
    )
    assert config.workdir == tmp_path
    assert config.skills_dir == tmp_path / "skills"
    assert config.memory_dir == tmp_path / ".memory"
    assert config.task_dir == tmp_path / ".tasks"
    assert config.mailbox_dir == tmp_path / ".mailboxes"
    assert config.worktrees_dir == tmp_path / ".worktrees"
    assert config.primary_model == "test-model"
    assert config.fallback_model is None


def test_config_requires_model_id(tmp_path):
    with pytest.raises(RuntimeError, match="MODEL_ID"):
        AppConfig.from_env(repo_root=tmp_path, environ={})


def test_session_state_has_no_shared_mutable_defaults():
    first = SessionState()
    second = SessionState()
    first.history.append({"role": "user", "content": "one"})
    first.todos.append({"content": "step", "status": "pending"})
    assert second.history == []
    assert second.todos == []
```

Add an import-side-effect assertion using an empty temporary root and a subprocess that imports `homework.agent_app.config` and `homework.agent_app.runtime`; assert no runtime directories appear.

- [ ] **Step 2: Run tests to verify the package does not exist**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_config_runtime.py tests/homework_agent/test_imports.py -q
```

Expected: collection fails because `homework.agent_app` does not exist.

- [ ] **Step 3: Implement immutable configuration**

Create `config.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import os


@dataclass(frozen=True, slots=True)
class AppConfig:
    repo_root: Path
    workdir: Path
    primary_model: str
    fallback_model: str | None
    anthropic_base_url: str | None
    skills_dir: Path
    memory_dir: Path
    memory_index: Path
    transcripts_dir: Path
    tool_result_dir: Path
    task_dir: Path
    mailbox_dir: Path
    worktrees_dir: Path
    durable_jobs_path: Path
    default_max_tokens: int = 8_000
    escalated_max_tokens: int = 64_000
    max_continuations: int = 3
    max_transient_retries: int = 10
    max_reactive_compacts: int = 1
    context_limit: int = 50_000
    keep_recent_tool_results: int = 3
    persist_threshold: int = 20_000
    idle_poll_interval: float = 5.0
    idle_timeout: float = 60.0

    @classmethod
    def from_env(
        cls,
        *,
        repo_root: Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> "AppConfig":
        env = os.environ if environ is None else environ
        root = (
            Path(__file__).resolve().parents[2]
            if repo_root is None
            else Path(repo_root)
        ).resolve()
        model = env.get("MODEL_ID")
        if not model:
            raise RuntimeError("MODEL_ID is required")
        workdir = root
        memory_dir = workdir / ".memory"
        tool_result_dir = workdir / ".task_outputs" / "tool-results"
        return cls(
            repo_root=root,
            workdir=workdir,
            primary_model=model,
            fallback_model=env.get("FALLBACK_MODEL_ID"),
            anthropic_base_url=env.get("ANTHROPIC_BASE_URL"),
            skills_dir=workdir / "skills",
            memory_dir=memory_dir,
            memory_index=memory_dir / "MEMORY.md",
            transcripts_dir=workdir / ".transcripts",
            tool_result_dir=tool_result_dir,
            task_dir=workdir / ".tasks",
            mailbox_dir=workdir / ".mailboxes",
            worktrees_dir=workdir / ".worktrees",
            durable_jobs_path=workdir / ".scheduled_tasks.json",
        )


def load_config(
    *,
    repo_root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    from dotenv import load_dotenv

    if environ is None:
        load_dotenv(override=True)
        if os.getenv("ANTHROPIC_BASE_URL"):
            os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
        env = os.environ
    else:
        env = environ
    return AppConfig.from_env(
        repo_root=repo_root,
        environ=env,
    )
```

- [ ] **Step 4: Implement runtime state containers**

Create `runtime.py` with postponed annotations and `TYPE_CHECKING` imports so importing it does not import or construct every feature:

```python
from __future__ import annotations

from dataclasses import dataclass, field
import threading
from typing import TYPE_CHECKING

from .config import AppConfig

if TYPE_CHECKING:
    from .adapters.anthropic import AnthropicAdapter
    from .features.background import BackgroundState
    from .features.memory import MemoryStore
    from .features.mcp import MCPState
    from .features.scheduler import SchedulerState
    from .features.skills import SkillCatalog
    from .features.tasks import TaskStore
    from .features.teams.teammates import TeamState
    from .features.worktrees import WorktreeState
    from .core.compaction import CompactionState
    from .core.prompt import PromptCache
    from .tools.hooks import HookRegistry
    from .tools.registry import ToolRegistry


@dataclass(slots=True)
class SessionState:
    history: list[dict] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    todos: list[dict] = field(default_factory=list)
    rounds_since_todo: int = 0
    agent_lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass(slots=True)
class RuntimeContext:
    config: AppConfig
    llm: AnthropicAdapter
    session: SessionState
    tools: ToolRegistry
    hooks: HookRegistry
    scheduler: SchedulerState
    background: BackgroundState
    tasks: TaskStore
    teams: TeamState
    mcp: MCPState
    skills: SkillCatalog
    memory: MemoryStore
    worktrees: WorktreeState
    compaction: CompactionState
    prompt_cache: PromptCache
```

Keep every `__init__.py` empty except for an internal-package docstring.

- [ ] **Step 5: Verify and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_config_runtime.py tests/homework_agent/test_imports.py -q
```

Expected: all tests pass and no `.memory`, `.tasks`, `.mailboxes`, or `.worktrees` directory is created by imports.

Commit:

```bash
git add homework/agent_app tests/homework_agent
git commit -m "refactor: add BaseAgent internal runtime types"
```

---

### Task 3: Introduce Tool and Hook Registries

**Files:**
- Create: `homework/agent_app/tools/__init__.py`
- Create: `homework/agent_app/tools/registry.py`
- Create: `homework/agent_app/tools/hooks.py`
- Create: `tests/homework_agent/test_registry.py`
- Modify: `homework/BaseAgent.py:2214-2468`

**Interfaces:**
- Consumes: current tool schema dictionaries, handler callables, and hook callback signatures.
- Produces: `ToolRegistry.register(schema, handler=None)`, `ToolRegistry.snapshot()`, `HookRegistry.register(event, callback)`, and `HookRegistry.trigger(event, *args)`.

- [ ] **Step 1: Write registry behavior tests**

Cover ordered registration, duplicate rejection, special tools without handlers, immutable snapshots, and hook short-circuiting:

```python
def test_tool_registry_keeps_special_tool_without_handler():
    registry = ToolRegistry()
    registry.register(
        {
            "name": "compact",
            "description": "Compact context",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }
    )
    tools, handlers = registry.snapshot()
    assert [tool["name"] for tool in tools] == ["compact"]
    assert handlers == {}


def test_tool_registry_rejects_duplicate_name():
    registry = ToolRegistry()
    schema = {
        "name": "bash",
        "description": "Run",
        "input_schema": {"type": "object", "properties": {}},
    }
    registry.register(schema, lambda: "one")
    with pytest.raises(ValueError, match="bash"):
        registry.register(schema, lambda: "two")


def test_hook_registry_returns_first_non_none_result():
    hooks = HookRegistry(("PreToolUse",))
    seen = []
    hooks.register("PreToolUse", lambda block: seen.append("first"))
    hooks.register("PreToolUse", lambda block: "denied")
    hooks.register("PreToolUse", lambda block: seen.append("third"))
    assert hooks.trigger("PreToolUse", object()) == "denied"
    assert seen == ["first"]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_registry.py -q
```

Expected: imports fail because registry modules do not exist.

- [ ] **Step 3: Implement ToolRegistry**

Create:

```python
from __future__ import annotations

import copy
from collections.abc import Callable, Iterable, Mapping


class ToolRegistry:
    def __init__(self) -> None:
        self._schemas: dict[str, dict] = {}
        self._handlers: dict[str, Callable[..., str]] = {}

    def register(
        self,
        schema: Mapping,
        handler: Callable[..., str] | None = None,
    ) -> None:
        name = str(schema["name"])
        if name in self._schemas:
            raise ValueError(f"Tool already registered: {name}")
        self._schemas[name] = copy.deepcopy(dict(schema))
        if handler is not None:
            self._handlers[name] = handler

    def register_many(
        self,
        entries: Iterable[
            tuple[Mapping, Callable[..., str] | None]
        ],
    ) -> None:
        for schema, handler in entries:
            self.register(schema, handler)

    def snapshot(self) -> tuple[list[dict], dict[str, Callable[..., str]]]:
        return (
            [copy.deepcopy(schema) for schema in self._schemas.values()],
            dict(self._handlers),
        )
```

In the same module, define `BASE_TOOL_SCHEMAS` as an ordered tuple containing
the current schema dictionaries in their existing order: the present
`BUILTIN_TOOLS` entries followed by the current `task` schema. Keep the schema
dictionary contents byte-for-byte equivalent apart from formatting.

- [ ] **Step 4: Implement HookRegistry and migrate default hook storage**

Create:

```python
from __future__ import annotations

from collections.abc import Callable, Iterable


class HookRegistry:
    def __init__(self, events: Iterable[str]) -> None:
        self._hooks = {event: [] for event in events}

    def register(self, event: str, callback: Callable) -> None:
        if event not in self._hooks:
            raise ValueError(f"Unknown hook event: {event}")
        self._hooks[event].append(callback)

    def trigger(self, event: str, *args):
        if event not in self._hooks:
            raise ValueError(f"Unknown hook event: {event}")
        for callback in self._hooks[event]:
            result = callback(*args)
            if result is not None:
                return result
        return None
```

In `BaseAgent.py`, after all current handlers including `spawn_subagent` have
been defined, instantiate a temporary registry and register each schema from
`BASE_TOOL_SCHEMAS` with the matching current handler. Register `compact`
with `handler=None`. Set the compatibility-era canonical snapshots with:

```python
TOOL_REGISTRY = ToolRegistry()
for schema in BASE_TOOL_SCHEMAS:
    name = schema["name"]
    TOOL_REGISTRY.register(
        schema,
        None if name == "compact" else BUILTIN_HANDLERS[name],
    )
BUILTIN_TOOLS, BUILTIN_HANDLERS = TOOL_REGISTRY.snapshot()
```

Retain thin local hook wrappers so the still-local Agent Loop continues to
call `trigger_hook(...)`. Do not create `TOOLS` or `TOOL_HANDLERS` aliases.

- [ ] **Step 5: Verify tool contracts and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_registry.py tests/test_homework_baseagent_todo_resume.py tests/test_homework_baseagent_compact_tool.py tests/test_homework_baseagent_task_system.py -q
```

Expected: tool names, required properties, handlers, and compact special handling remain unchanged.

Commit:

```bash
git add homework/BaseAgent.py homework/agent_app/tools tests/homework_agent/test_registry.py
git commit -m "refactor: centralize BaseAgent registries"
```

---

### Task 4: Extract Todo and Skill Features

**Files:**
- Create: `homework/agent_app/features/__init__.py`
- Create: `homework/agent_app/features/todos.py`
- Create: `homework/agent_app/features/skills.py`
- Create: `tests/homework_agent/test_todos_skills.py`
- Modify: `homework/BaseAgent.py:1988-2031`
- Modify: `homework/BaseAgent.py:2101-2139`

**Interfaces:**
- Produces: `TodoState`, `normalize_todos`, `update_todos`, `format_todos`, `SkillCatalog.scan()`, `SkillCatalog.list()`, and `SkillCatalog.load(name)`.

- [ ] **Step 1: Write isolated feature tests**

Use these contracts:

```python
def test_todo_update_mutates_owned_list_in_place():
    items = []
    state = TodoState(items=items)
    result = update_todos(
        state,
        [{"content": "inspect", "status": "in_progress"}],
    )
    assert result == "Updated 1 tasks"
    assert state.items is items
    assert format_todos(state) == "- [in_progress] inspect"


def test_invalid_todo_update_preserves_state():
    state = TodoState(
        items=[{"content": "keep", "status": "pending"}]
    )
    result = update_todos(
        state,
        [{"content": "bad", "status": "unknown"}],
    )
    assert result.startswith("Error:")
    assert state.items == [{"content": "keep", "status": "pending"}]


def test_skill_catalog_scans_only_when_called(tmp_path):
    skill_dir = tmp_path / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo skill\n---\nBody",
        encoding="utf-8",
    )
    catalog = SkillCatalog(tmp_path / "skills")
    assert catalog.entries == {}
    catalog.scan()
    assert "demo" in catalog.list()
    assert "Body" in catalog.load("demo")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_todos_skills.py -q
```

Expected: feature imports fail.

- [ ] **Step 3: Move Todo code with explicit state**

Implement:

```python
@dataclass(slots=True)
class TodoState:
    items: list[dict] = field(default_factory=list)


def update_todos(state: TodoState, todos: list | str) -> str:
    normalized, error = normalize_todos(todos)
    if error:
        return error
    state.items[:] = normalized
    lines = ["\n\033[33m## Current Tasks\033[0m"]
    for todo in state.items:
        icon = {
            "pending": " ",
            "in_progress": "\033[36m▸\033[0m",
            "completed": "\033[32m✓\033[0m",
        }[todo["status"]]
        lines.append(f"  [{icon}] {todo['content']}")
    print("\n".join(lines))
    return f"Updated {len(state.items)} tasks"


def format_todos(state: TodoState) -> str:
    return "\n".join(
        f"- [{todo['status']}] {todo['content']}"
        for todo in state.items
    )
```

Move the existing parsing body into `normalize_todos()` unchanged. Use in-place mutation so the temporary `CURRENT_TODOS` alias in `BaseAgent.py` stays synchronized.

- [ ] **Step 4: Move skill parsing and scanning**

Implement `SkillCatalog` with `skills_dir` and `entries` fields. Move `_parse_skill_frontmatter`, `_scan_skills`, `list_skills`, and `load_skill` bodies into methods or state-taking functions. Do not scan from module import. During the compatibility phase, `BaseAgent.py` explicitly calls `catalog.scan()` once after constructing the catalog.

- [ ] **Step 5: Verify and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_todos_skills.py tests/test_homework_baseagent_todo_resume.py tests/test_homework_baseagent_task_system.py -q
```

Expected: session-only Todo behavior and skill catalog output are unchanged.

Commit:

```bash
git add homework/BaseAgent.py homework/agent_app/features tests/homework_agent/test_todos_skills.py
git commit -m "refactor: extract Todo and skill features"
```

---

### Task 5: Extract the Durable Task Store

**Files:**
- Create: `homework/agent_app/features/tasks.py`
- Create: `tests/homework_agent/test_tasks_worktrees.py`
- Modify: `homework/BaseAgent.py:1136-1261`
- Modify: `homework/BaseAgent.py:2141-2177`

**Interfaces:**
- Produces: `Task`, `TaskStore(root, lock)`, `create_task(store, subject, description="", blockedBy=None)`, `load_task(store, task_id)`, `list_tasks(store)`, `claim_task(store, task_id, owner)`, `complete_task(store, task_id)`, and handler wrappers.

- [ ] **Step 1: Port task tests to an explicit TaskStore**

Build the store directly:

```python
@pytest.fixture
def task_store(tmp_path):
    root = tmp_path / ".tasks"
    root.mkdir()
    return TaskStore(root=root)


def test_task_store_isolated_from_process_globals(task_store):
    task = create_task(task_store, "inspect parser")
    assert task_path(task_store, task.id).parent == task_store.root
    assert load_task(task_store, task.id).subject == "inspect parser"
```

Port all state-machine, UTF-8, corruption, path traversal, and simultaneous claim assertions from `test_homework_baseagent_task_system.py`. The simultaneous claim test must still assert exactly one `"Claimed"` result.

- [ ] **Step 2: Run tests to verify missing feature**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_tasks_worktrees.py -k task -q
```

Expected: import failure for `features.tasks`.

- [ ] **Step 3: Move the task model and persistence functions**

Use:

```python
@dataclass(slots=True)
class TaskStore:
    root: Path
    lock: threading.RLock = field(default_factory=threading.RLock)

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
```

Retain the current `Task` fields including `worktree`. Replace every `TASK_DIR` reference with `store.root` and every `TASK_LOCK` reference with `store.lock`. Use `RLock` because claim and dependency checks compose store operations.

Keep atomic temp-file replacement and task-id validation unchanged.

- [ ] **Step 4: Add handler functions and temporary BaseAgent delegation**

The feature owns:

```python
def run_create_task(
    store: TaskStore,
    subject: str,
    description: str = "",
    blockedBy: list[str] | None = None,
) -> str:
    task = create_task(store, subject, description, blockedBy)
    deps = (
        f" (blocked by: {', '.join(blockedBy)})"
        if blockedBy
        else ""
    )
    print(f"  \033[34m[create] {task.subject}{deps}\033[0m")
    return f"Created {task.id}: {task.subject}{deps}"


def run_list_tasks(store: TaskStore) -> str:
    tasks = list_tasks(store)
    if not tasks:
        return "No tasks. Use create_task to add some."
    lines = []
    for task in tasks:
        icon = {
            "pending": "○",
            "in_progress": "●",
            "completed": "✓",
        }.get(task.status, "?")
        deps = f" (blocked by: {', '.join(task.blockedBy)})"
        owner = f"[{task.owner}]" if task.owner else ""
        lines.append(
            f"  {icon} {task.id}: {task.subject} "
            f"[{task.status}]{owner}{deps}"
        )
    return "\n".join(lines)


def run_get_task(store: TaskStore, task_id: str) -> str:
    try:
        return get_task(store, task_id)
    except (OSError, ValueError, TypeError) as exc:
        return f"Error: cannot read task {task_id}: {exc}"


def run_claim_task(store: TaskStore, task_id: str) -> str:
    try:
        return claim_task(store, task_id, owner="agent")
    except (OSError, ValueError, TypeError) as exc:
        return f"Error: cannot claim task {task_id}: {exc}"


def run_complete_task(store: TaskStore, task_id: str) -> str:
    try:
        return complete_task(store, task_id)
    except (OSError, ValueError, TypeError) as exc:
        return f"Error: cannot complete task {task_id}: {exc}"
```

In `BaseAgent.py`, construct and initialize one temporary store, then expose same-signature wrappers that delegate to it. Rebind task tool handlers to those wrappers.

- [ ] **Step 5: Verify and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_tasks_worktrees.py -k task tests/test_homework_baseagent_task_system.py -q
```

Expected: all task persistence and concurrency tests pass.

Commit:

```bash
git add homework/BaseAgent.py homework/agent_app/features/tasks.py tests/homework_agent/test_tasks_worktrees.py
git commit -m "refactor: extract durable task store"
```

---

### Task 6: Extract Worktree Management

**Files:**
- Create: `homework/agent_app/features/worktrees.py`
- Modify: `tests/homework_agent/test_tasks_worktrees.py`
- Modify: `homework/BaseAgent.py:1434-1544`
- Modify: `homework/BaseAgent.py:2202-2209`

**Interfaces:**
- Produces: `WorktreeState(workdir, root)`, `validate_worktree_name(name)`, `run_git(workdir, args)`, `create_worktree(state, name, task_id, bind_task)`, `remove_worktree(state, name, discard_changes=False)`, and `keep_worktree(state, name)`.
- Consumes: a narrow `bind_task(task_id, worktree_name)` callback instead of importing the task feature.

- [ ] **Step 1: Add worktree tests with a fake git runner**

```python
def test_create_worktree_uses_binding_callback(tmp_path):
    calls = []
    bindings = []
    state = WorktreeState(
        workdir=tmp_path,
        root=tmp_path / ".worktrees",
        git_runner=lambda args: calls.append(args) or (True, "ok"),
    )
    result = create_worktree(
        state,
        "parser-fix",
        task_id="task_one",
        bind_task=lambda task_id, name: bindings.append(
            (task_id, name)
        ),
    )
    assert "parser-fix" in result
    assert bindings == [("task_one", "parser-fix")]
```

Also port name validation, dirty removal refusal, explicit discard, and keep behavior from the current requirements.

- [ ] **Step 2: Run worktree tests to verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_tasks_worktrees.py -k worktree -q
```

Expected: import failure for `features.worktrees`.

- [ ] **Step 3: Move existing worktree functions**

Use:

```python
@dataclass(slots=True)
class WorktreeState:
    workdir: Path
    root: Path
    git_runner: Callable[[list[str]], tuple[bool, str]]
    events: list[dict] = field(default_factory=list)

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
```

Move current validation, git invocation, change counting, event logging, create/remove/keep bodies. Replace direct `bind_task_to_worktree` calls with the injected callback.

- [ ] **Step 4: Delegate from BaseAgent and verify**

Construct one temporary state and bind the callback to the extracted `TaskStore`. Preserve existing tool handler signatures.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_tasks_worktrees.py tests/test_homework_baseagent_task_system.py -q
```

Expected: task worktree binding remains persisted and all tests pass.

- [ ] **Step 5: Commit**

```bash
git add homework/BaseAgent.py homework/agent_app/features/worktrees.py tests/homework_agent/test_tasks_worktrees.py
git commit -m "refactor: extract worktree management"
```

---

### Task 7: Extract Cron Scheduling

**Files:**
- Create: `homework/agent_app/features/scheduler.py`
- Create: `tests/homework_agent/test_scheduler_background.py`
- Modify: `homework/BaseAgent.py:63-260`
- Modify: `homework/BaseAgent.py:2179-2200`
- Modify: `homework/BaseAgent.py:3163-3200`

**Interfaces:**
- Produces: `CronJob`, `SchedulerState`, `validate_cron`, `cron_matches`, schedule/list/cancel operations, `scheduler_loop(state, stop_event)`, `has_pending_jobs(state)`, and `drain_jobs(state)`.

- [ ] **Step 1: Write deterministic scheduler tests**

```python
def test_scheduler_enqueues_one_job_per_minute(tmp_path):
    state = SchedulerState(
        durable_path=tmp_path / ".scheduled_tasks.json"
    )
    job = schedule_job(
        state,
        "* * * * *",
        "run checks",
        recurring=True,
        durable=False,
    )
    now = datetime(2026, 7, 31, 12, 30)
    fire_due_jobs(state, now)
    fire_due_jobs(state, now)
    assert [item.id for item in drain_jobs(state)] == [job.id]
    assert drain_jobs(state) == []
```

Cover validation, day-of-month/day-of-week semantics, durable load/save, one-shot removal, cancellation, and corrupt durable storage.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_scheduler_background.py -k scheduler -q
```

Expected: import failure for scheduler feature.

- [ ] **Step 3: Move scheduler code behind SchedulerState**

Implement:

```python
@dataclass(slots=True)
class SchedulerState:
    durable_path: Path
    jobs: dict[str, CronJob] = field(default_factory=dict)
    queue: list[CronJob] = field(default_factory=list)
    last_fired: dict[str, str] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)
```

Extract the current match/validate bodies unchanged. Split the loop so `fire_due_jobs(state, now)` is deterministic and `scheduler_loop` only supplies time and waiting.

- [ ] **Step 4: Delegate current handlers and queue processor**

In `BaseAgent.py`, temporary wrappers delegate schedule/list/cancel/drain operations to one state. The existing queue processor continues to own the lead `agent_lock`; the scheduler feature never calls the LLM.

- [ ] **Step 5: Verify and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_scheduler_background.py -k scheduler tests/test_homework_baseagent_agent_teams.py -q
```

Expected: scheduler tests pass and lead-loop tests show no concurrent history writer.

Commit:

```bash
git add homework/BaseAgent.py homework/agent_app/features/scheduler.py tests/homework_agent/test_scheduler_background.py
git commit -m "refactor: extract cron scheduler"
```

---

### Task 8: Extract Background Execution

**Files:**
- Create: `homework/agent_app/features/background.py`
- Create: `homework/agent_app/tools/executor.py`
- Modify: `tests/homework_agent/test_scheduler_background.py`
- Modify: `homework/BaseAgent.py:1036-1133`
- Modify: `homework/BaseAgent.py:3042-3098`

**Interfaces:**
- Produces: `BackgroundState`, `is_slow_operation`, `should_run_background`, `start_background_task(state, block, handlers, execute, post_hook, persist)`, `drain_background_results(state)`, and `execute_tool(block, handlers)`.

- [ ] **Step 1: Port background tests to explicit dependencies**

```python
def test_background_failure_becomes_one_notification(tmp_path):
    state = BackgroundState()
    block = tool_block("tool-failure", "pytest")
    bg_id = start_background_task(
        state,
        block,
        {"bash": lambda command: (_ for _ in ()).throw(
            RuntimeError("worker boom")
        )},
        execute=execute_tool,
        post_hook=lambda *args: None,
        persist=lambda tool_id, output: output,
    )
    wait_until_finished(state, bg_id)
    notifications = drain_background_results(state)
    assert len(notifications) == 1
    assert "<status>failed</status>" in notifications[0]
    assert "worker boom" in notifications[0]
    assert drain_background_results(state) == []
```

Port success, failure, daemon, multiple workers, persisted output, XML escaping, denied dispatch, and one-result pairing tests.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_scheduler_background.py -k background -q
```

Expected: imports fail for background/executor.

- [ ] **Step 3: Implement owned background state**

```python
@dataclass(slots=True)
class BackgroundState:
    counter: int = 0
    tasks: dict[str, dict] = field(default_factory=dict)
    results: dict[str, str] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
```

Move existing logic and keep handler snapshotting before thread start. The worker invokes only the supplied `execute`, `post_hook`, and `persist` callables.

- [ ] **Step 4: Extract ordinary executor and delegate from BaseAgent**

Create:

```python
def execute_tool(block, handlers: Mapping[str, Callable]) -> str:
    handler = handlers.get(block.name)
    if handler is None:
        return f"Unknown tool: {block.name}"
    return str(handler(**block.input))
```

Update the still-local Agent Loop to pass the current handler snapshot explicitly to ordinary and background execution.

- [ ] **Step 5: Verify and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_scheduler_background.py tests/test_homework_baseagent_background_tasks.py -q
```

Expected: all background tests pass without registry corruption or repeated notifications.

Commit:

```bash
git add homework/BaseAgent.py homework/agent_app/features/background.py homework/agent_app/tools/executor.py tests/homework_agent/test_scheduler_background.py
git commit -m "refactor: extract background execution"
```

---

### Task 9: Extract Anthropic Adapter and Recovery

**Files:**
- Create: `homework/agent_app/adapters/__init__.py`
- Create: `homework/agent_app/adapters/anthropic.py`
- Create: `homework/agent_app/core/__init__.py`
- Create: `homework/agent_app/core/recovery.py`
- Create: `tests/homework_agent/test_recovery_adapter.py`
- Modify: `homework/BaseAgent.py:1546-1694`
- Modify: `homework/BaseAgent.py:3114-3136`

**Interfaces:**
- Produces: `PartialStreamError`, `AnthropicAdapter.create(**request)`, `AnthropicAdapter.stream(system, messages, model, max_tokens, tools)`, `RecoveryState`, and `with_retry(call, state, config)`.

- [ ] **Step 1: Port recovery and streaming tests**

Use a fake SDK client passed to the adapter:

```python
def test_stream_wraps_failure_after_visible_text(capsys):
    cause = FakeAPIError(529, "overloaded")
    client = fake_client_with_stream(["visible-part"], cause)
    adapter = AnthropicAdapter(client)
    with pytest.raises(PartialStreamError) as raised:
        adapter.stream(
            system="system",
            messages=[{"role": "user", "content": "test"}],
            model="primary",
            max_tokens=8_000,
            tools=[],
        )
    assert raised.value.partial_text == "visible-part"
    assert raised.value.cause is cause
    assert capsys.readouterr().out == "visible-part\n"
```

Port 429 retry-after, bounded retry, 529 fallback, prompt-too-long classification, partial-stream no-replay, and max-token continuation behavior.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_recovery_adapter.py -q
```

Expected: adapter and recovery imports fail.

- [ ] **Step 3: Move streaming into AnthropicAdapter**

Implement:

```python
class PartialStreamError(Exception):
    def __init__(self, partial_text: str, cause: Exception):
        super().__init__(str(cause))
        self.partial_text = partial_text
        self.cause = cause


class AnthropicAdapter:
    def __init__(self, client):
        self.client = client

    def create(self, **kwargs):
        return self.client.messages.create(**kwargs)

    def stream(
        self,
        *,
        system,
        messages,
        model,
        max_tokens,
        tools,
    ):
        chunks = []
        try:
            with self.client.messages.stream(
                model=model,
                system=system,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
            ) as stream:
                for chunk in stream.text_stream:
                    if chunk:
                        chunks.append(chunk)
                        print(chunk, end="", flush=True)
                return stream.get_final_message()
        except Exception as exc:
            if chunks:
                raise PartialStreamError(
                    "".join(chunks),
                    exc,
                ) from exc
            raise
        finally:
            if chunks and not chunks[-1].endswith("\n"):
                print()


def build_anthropic_adapter(config: AppConfig) -> AnthropicAdapter:
    from anthropic import Anthropic

    client = Anthropic(base_url=config.anthropic_base_url)
    return AnthropicAdapter(client)
```

- [ ] **Step 4: Move recovery policy and delegate**

Move error inspection and backoff bodies unchanged. Replace model globals with `AppConfig` fields. `with_retry` must immediately re-raise `PartialStreamError` so visible text is never replayed.

Keep temporary BaseAgent wrappers using the current client and config.

- [ ] **Step 5: Verify and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_recovery_adapter.py tests/test_homework_baseagent_error_recovery.py -q
```

Expected: all recovery and streaming tests pass.

Commit:

```bash
git add homework/BaseAgent.py homework/agent_app/adapters homework/agent_app/core tests/homework_agent/test_recovery_adapter.py
git commit -m "refactor: isolate Anthropic recovery adapter"
```

---

### Task 10: Extract Team Bus, Protocol, Teammates, and Subagents

**Files:**
- Create: `homework/agent_app/features/teams/__init__.py`
- Create: `homework/agent_app/features/teams/bus.py`
- Create: `homework/agent_app/features/teams/protocol.py`
- Create: `homework/agent_app/features/teams/teammates.py`
- Create: `homework/agent_app/features/subagents.py`
- Create: `tests/homework_agent/test_teams_subagents.py`
- Modify: `homework/BaseAgent.py:262-1034`
- Modify: `homework/BaseAgent.py:2367-2468`

**Interfaces:**
- Produces: `MessageBus(root, lock)`, `ProtocolState`, `ProtocolRegistry`, `TeamState`, teammate operations, and `run_subagent(description, llm, retry, hooks, tools, handlers, config)`.
- Consumes: explicit task, worktree, LLM, recovery, hook, and tool dependencies.

- [ ] **Step 1: Port bus and protocol tests**

Construct bus/state directly:

```python
def test_bus_consumes_valid_lines_once(tmp_path):
    bus = MessageBus(tmp_path / ".mailboxes")
    bus.initialize()
    bus.send("researcher", "lead", "first")
    assert [item["content"] for item in bus.read_inbox("lead")] == [
        "first"
    ]
    assert bus.read_inbox("lead") == []


def test_team_state_has_isolated_registries(tmp_path):
    first = TeamState(bus=MessageBus(tmp_path / "one"))
    second = TeamState(bus=MessageBus(tmp_path / "two"))
    first.active_teammates["researcher"] = {"status": "running"}
    assert second.active_teammates == {}
```

Port name validation, corrupt JSON tolerance, concurrent send, permission correlation, shutdown, plan approve/reject, registry cleanup, nonrecursive tools, independent history, result delivery, and lead inbox drain tests.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_teams_subagents.py -q
```

Expected: team feature imports fail.

- [ ] **Step 3: Move MessageBus and protocol state**

`MessageBus` owns its root and lock:

```python
@dataclass(slots=True)
class MessageBus:
    root: Path
    lock: threading.RLock = field(
        default_factory=threading.RLock
    )

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
```

Move path validation and JSONL send/read bodies unchanged. Move pending requests and protocol matching into:

```python
@dataclass(slots=True)
class ProtocolRegistry:
    pending: dict[str, ProtocolState] = field(default_factory=dict)
    lock: threading.RLock = field(
        default_factory=threading.RLock
    )
```

- [ ] **Step 4: Move teammate and subagent loops with explicit dependencies**

Use:

```python
@dataclass(slots=True)
class TeamState:
    bus: MessageBus
    protocol: ProtocolRegistry = field(
        default_factory=ProtocolRegistry
    )
    active_teammates: dict[str, dict] = field(
        default_factory=dict
    )
    lock: threading.Lock = field(default_factory=threading.Lock)
    idle_poll_interval: float = 5.0
    idle_timeout: float = 60.0
```

`spawn_teammate(state, name, role, prompt, llm, retry, tools, handlers, hooks, scan_tasks, claim_task, can_start, worktree_path)` receives all cross-feature dependencies explicitly. `idle_poll(state, agent_name, messages, wait, scan_tasks, claim_task, can_start, worktree_path)` receives a `wait` callable so tests do not sleep.

`run_subagent(description, llm, retry, hooks, tools, handlers, config)` receives its nonrecursive tool snapshot. Neither module imports the lead Agent Loop.

- [ ] **Step 5: Verify and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_teams_subagents.py tests/test_homework_baseagent_agent_teams.py tests/test_homework_baseagent_error_recovery.py -q
```

Expected: team/subagent tests pass with no real wait, no lead-history mutation, and no recursive delegation tools.

Commit:

```bash
git add homework/BaseAgent.py homework/agent_app/features/teams homework/agent_app/features/subagents.py tests/homework_agent/test_teams_subagents.py
git commit -m "refactor: extract team and subagent runtimes"
```

---

### Task 11: Extract Memory and Compaction

**Files:**
- Create: `homework/agent_app/features/memory.py`
- Create: `homework/agent_app/core/compaction.py`
- Create: `tests/homework_agent/test_memory_compaction.py`
- Modify: `homework/BaseAgent.py:1696-1986`
- Modify: `homework/BaseAgent.py:2470-2629`

**Interfaces:**
- Produces: `MemoryStore`, memory operations, message-pair helpers, `CompactionState`, budgeting functions, transcript writing, normal compact, and reactive compact.
- Consumes: injected LLM summarizer instead of a global client.

- [ ] **Step 1: Port memory and compaction tests**

Use explicit stores:

```python
def test_reactive_compact_summarizes_only_old_history(tmp_path):
    captured = []
    state = CompactionState(
        transcripts_dir=tmp_path / ".transcripts",
        tool_results_dir=tmp_path / "tool-results",
        keep_recent=3,
        persist_threshold=20_000,
    )
    messages = conversation_with_tail_tool_pair()
    compacted = reactive_compact(
        state,
        messages,
        summarize=lambda old: captured.extend(old) or "summary",
    )
    assert captured == messages[:3]
    assert compacted[1:] == messages[3:]
```

Port all tool-pair tests, persistence budget tests, memory selection, internal reminder exclusion, frontmatter parsing, extraction, and consolidation tests.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_memory_compaction.py -q
```

Expected: memory and compaction imports fail.

- [ ] **Step 3: Move memory operations behind MemoryStore**

```python
@dataclass(slots=True)
class MemoryStore:
    root: Path
    index: Path

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
```

Replace path globals with store fields. Pass LLM extraction/consolidation callables explicitly. Keep relevance and internal-reminder rules unchanged.

- [ ] **Step 4: Move compaction operations behind CompactionState**

```python
@dataclass(frozen=True, slots=True)
class CompactionState:
    transcripts_dir: Path
    tool_results_dir: Path
    keep_recent: int
    persist_threshold: int
```

Move all current block helpers and algorithms unchanged. `summarize_history`, `compact_history`, and `reactive_compact` receive a `summarize` callable. File creation occurs only when the operation is called.

- [ ] **Step 5: Verify and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_memory_compaction.py tests/test_homework_baseagent_compact_tool.py tests/test_compaction_tool_pairs.py -q
```

Expected: all memory/compaction tests pass and no orphan tool results are produced.

Commit:

```bash
git add homework/BaseAgent.py homework/agent_app/features/memory.py homework/agent_app/core/compaction.py tests/homework_agent/test_memory_compaction.py
git commit -m "refactor: extract memory and compaction"
```

---

### Task 12: Extract Builtin Tools, Hooks, and MCP

**Files:**
- Create: `homework/agent_app/tools/builtin.py`
- Create: `homework/agent_app/features/mcp.py`
- Create: `tests/homework_agent/test_mcp.py`
- Modify: `homework/agent_app/tools/hooks.py`
- Modify: `homework/BaseAgent.py:1263-1432`
- Modify: `homework/BaseAgent.py:2034-2100`
- Modify: `homework/BaseAgent.py:2633-2752`

**Interfaces:**
- Produces: workspace-safe builtin handlers, registered default hooks, `MCPState`, `connect_mcp`, and `assemble_tool_pool(base_registry, mcp_state)`.

- [ ] **Step 1: Write builtin, hook, and MCP tests**

```python
def test_builtin_path_cannot_escape_workdir(tmp_path):
    with pytest.raises(ValueError, match="escapes"):
        safe_path(tmp_path, "../outside")


def test_mcp_pool_is_dynamic_and_collision_safe():
    base = ToolRegistry()
    register_builtin_schemas(base, fake_handlers())
    state = MCPState()
    assert connect_mcp(state, "docs").startswith("Connected")
    tools, handlers = assemble_tool_pool(base, state)
    names = {tool["name"] for tool in tools}
    assert "mcp__docs__search" in names
    assert "mcp__docs__search" in handlers
```

Cover destructive MCP permission metadata, name normalization, duplicate connection, unknown server, and handler snapshot stability.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_mcp.py -q
```

Expected: builtin/MCP imports fail.

- [ ] **Step 3: Move builtin tools**

Move `resolve_tool_cwd`, `safe_path`, bash/read/write/edit/glob bodies. Use `workdir` as an explicit first argument:

```python
def run_read(
    workdir: Path,
    path: str,
    offset: int = 0,
    limit: int | None = None,
    cwd: str | Path | None = None,
) -> str:
    try:
        lines = safe_path(workdir, path, cwd=cwd).read_text(
            encoding="utf-8"
        ).splitlines()
        offset = max(0, offset)
        bounded_limit = (
            1000
            if limit is None
            else max(1, min(limit, 1000))
        )
        end = min(offset + bounded_limit, len(lines))
        result = lines[offset:end]
        if end < len(lines):
            result.append(
                f"... ({len(lines) - end} more lines);"
                f"continue with offset={end}"
            )
        return "\n".join(result)
    except Exception as exc:
        return f"Error: {exc}"
```

Bind `workdir` with `functools.partial` in bootstrap and in temporary BaseAgent registration.

- [ ] **Step 4: Finish default hooks and MCP extraction**

Move permission, log, large-output, context injection, summary, and diff-preview callbacks. Provide:

```python
def register_default_hooks(
    registry: HookRegistry,
    *,
    workdir: Path,
    mcp_state: MCPState,
    input_fn: Callable[[str], str] = input,
) -> None:
    registry.register(
        "UserPromptSubmit",
        partial(context_inject_hook, workdir),
    )
    registry.register(
        "PreToolUse",
        partial(
            permission_hook,
            mcp_state=mcp_state,
            input_fn=input_fn,
        ),
    )
    registry.register("PreToolUse", log_hook)
    registry.register(
        "PreToolUse",
        partial(
            diff_preview_hook,
            workdir=workdir,
            input_fn=input_fn,
        ),
    )
    registry.register("PostToolUse", large_output_hook)
    registry.register("Stop", summary_hook)
```

Create:

```python
@dataclass(slots=True)
class MCPState:
    clients: dict[str, MCPClient] = field(default_factory=dict)
    metadata: dict[str, dict] = field(default_factory=dict)
    lock: threading.RLock = field(
        default_factory=threading.RLock
    )
```

`assemble_tool_pool` starts from `base_registry.snapshot()`, adds MCP tools to copies, and updates only `state.metadata`.

- [ ] **Step 5: Verify and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_registry.py tests/homework_agent/test_mcp.py tests/test_homework_baseagent_background_tasks.py tests/test_homework_baseagent_agent_teams.py -q
```

Expected: schemas and handlers match, MCP tools appear only after connection, and permission hooks use current metadata.

Commit:

```bash
git add homework/BaseAgent.py homework/agent_app/tools homework/agent_app/features/mcp.py tests/homework_agent/test_mcp.py
git commit -m "refactor: extract builtin tools hooks and MCP"
```

---

### Task 13: Extract Context, Prompt, Agent Loop, Bootstrap, and CLI

**Files:**
- Create: `homework/agent_app/core/context.py`
- Create: `homework/agent_app/core/prompt.py`
- Create: `homework/agent_app/core/loop.py`
- Create: `homework/agent_app/bootstrap.py`
- Create: `homework/agent_app/cli.py`
- Create: `tests/homework_agent/test_loop.py`
- Create: `tests/homework_agent/test_cli.py`
- Modify: `homework/agent_app/runtime.py`
- Replace: `homework/BaseAgent.py`

**Interfaces:**
- Produces: `build_runtime(config=None, llm=None)`, `run_agent_loop(runtime)`, `run_agent_turn(runtime, user_query=None)`, `start_runtime_threads(runtime, stop_event)`, and `cli.main(runtime_factory=build_runtime, input_fn=input, start_threads=start_runtime_threads)`.

- [ ] **Step 1: Write runtime composition and Agent Loop integration tests**

Build an isolated runtime from fake dependencies:

```python
def test_loop_uses_runtime_owned_session(runtime, text_response):
    runtime.llm.responses.append(text_response("done"))
    runtime.session.history.append(
        {"role": "user", "content": "inspect"}
    )
    run_agent_loop(runtime)
    assert runtime.session.history[-1]["role"] == "assistant"
    assert runtime.llm.requests[0]["messages"][0] == {
        "role": "user",
        "content": "inspect",
    }


def test_explicit_compact_skips_later_tools(runtime):
    runtime.llm.responses.extend(
        [compact_then_bash_response(), text_response("continued")]
    )
    run_agent_turn(runtime, "compact now")
    assert runtime.fake_bash_calls == []
    assert len(runtime.llm.requests) == 2
```

Port all existing loop-level tests for notification collection, context refresh, max tokens, partial stream, permission denial, background dispatch, tool-result pairing, stop hooks, team late messages, and explicit compact.

- [ ] **Step 2: Write CLI lifecycle tests**

```python
def test_cli_exit_stops_threads(fake_runtime):
    stop_events = []
    main(
        runtime_factory=lambda: fake_runtime,
        input_fn=lambda _prompt: "q",
        start_threads=lambda runtime, stop: (
            stop_events.append(stop) or []
        ),
    )
    assert len(stop_events) == 1
    assert stop_events[0].is_set()


def test_baseagent_file_is_thin():
    tree = ast.parse(BASE_AGENT.read_text(encoding="utf-8"))
    definitions = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    ]
    assert definitions == []
```

- [ ] **Step 3: Run new tests to verify missing core**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_loop.py tests/homework_agent/test_cli.py -q
```

Expected: core loop/bootstrap/CLI imports fail.

- [ ] **Step 4: Move context and prompt code**

`build_request_messages_with_memories` receives a `MemoryStore`; `update_context` receives runtime and a current tool snapshot. Prompt cache becomes instance-owned:

```python
@dataclass(slots=True)
class PromptCache:
    key: str | None = None
    prompt: str | None = None
```

`build_system_prompt(context)` remains pure. `get_system_prompt(cache, context)` owns caching.

- [ ] **Step 5: Move the lead Agent Loop**

Use the exact entry signatures `run_agent_loop(runtime: RuntimeContext) -> None` and `run_agent_turn(runtime: RuntimeContext, user_query: str | None = None) -> None`. `run_agent_turn` is:

```python
def run_agent_turn(
    runtime: RuntimeContext,
    user_query: str | None = None,
) -> None:
    if user_query:
        runtime.session.history.append(
            {"role": "user", "content": user_query}
        )
    run_agent_loop(runtime)
    runtime.session.context = update_context(runtime)
```

Move the existing loop body rather than recreating it. Replace each global access with the owning runtime/state call:

```text
session_history/session_context/rounds_since_todo → runtime.session
consume_cron_queue                           → drain_jobs(runtime.scheduler)
collect_background_results                  → drain_background_results(runtime.background)
collect_lead_inbox                          → collect_lead_inbox(runtime.teams)
assemble_tool_pool                          → assemble_tool_pool(runtime.tools, runtime.mcp)
trigger_hook                                → runtime.hooks.trigger
create_message_streaming                    → runtime.llm.stream
tool_result_budget/compact_history           → runtime.compaction operations
list_skills/load_skill                       → runtime.skills
load/extract/consolidate memories            → runtime.memory
get_system_prompt                            → runtime.prompt_cache
```

Keep the explicit `compact` branch before ordinary tool execution.

- [ ] **Step 6: Build the composition root**

`build_runtime` performs all initialization in order:

```python
def build_runtime(
    config: AppConfig | None = None,
    llm: AnthropicAdapter | None = None,
) -> RuntimeContext:
    config = config or load_config()
    llm = llm or build_anthropic_adapter(config)
    session = SessionState()
    tasks = TaskStore(config.task_dir)
    scheduler = SchedulerState(config.durable_jobs_path)
    background = BackgroundState()
    skills = SkillCatalog(config.skills_dir)
    memory = MemoryStore(config.memory_dir, config.memory_index)
    worktrees = WorktreeState(
        workdir=config.workdir,
        root=config.worktrees_dir,
        git_runner=partial(run_git, config.workdir),
    )
    compaction = CompactionState(
        transcripts_dir=config.transcripts_dir,
        tool_results_dir=config.tool_result_dir,
        keep_recent=config.keep_recent_tool_results,
        persist_threshold=config.persist_threshold,
    )
    prompt_cache = PromptCache()
    teams = TeamState(
        bus=MessageBus(config.mailbox_dir),
        idle_poll_interval=config.idle_poll_interval,
        idle_timeout=config.idle_timeout,
    )
    mcp = MCPState()
    tools = ToolRegistry()
    hooks = HookRegistry(
        ("UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop")
    )

    tasks.initialize()
    teams.bus.initialize()
    skills.scan()
    memory.initialize()
    worktrees.initialize()
    register_all_tools(
        tools,
        config=config,
        session=session,
        tasks=tasks,
        scheduler=scheduler,
        background=background,
        teams=teams,
        mcp=mcp,
        skills=skills,
        worktrees=worktrees,
        llm=llm,
        hooks=hooks,
    )
    register_default_hooks(
        hooks,
        workdir=config.workdir,
        mcp_state=mcp,
    )
    return RuntimeContext(
        config=config,
        llm=llm,
        session=session,
        tools=tools,
        hooks=hooks,
        scheduler=scheduler,
        background=background,
        tasks=tasks,
        teams=teams,
        mcp=mcp,
        skills=skills,
        memory=memory,
        worktrees=worktrees,
        compaction=compaction,
        prompt_cache=prompt_cache,
    )
```

In the same file, implement the exact composition signature:

```python
def register_all_tools(
    registry: ToolRegistry,
    *,
    config: AppConfig,
    session: SessionState,
    tasks: TaskStore,
    scheduler: SchedulerState,
    background: BackgroundState,
    teams: TeamState,
    mcp: MCPState,
    skills: SkillCatalog,
    worktrees: WorktreeState,
    llm: AnthropicAdapter,
    hooks: HookRegistry,
) -> None:
    handlers = build_bound_handlers(
        config=config,
        session=session,
        tasks=tasks,
        scheduler=scheduler,
        background=background,
        teams=teams,
        mcp=mcp,
        skills=skills,
        worktrees=worktrees,
        llm=llm,
        hooks=hooks,
    )
    for schema in BASE_TOOL_SCHEMAS:
        registry.register(
            schema,
            None
            if schema["name"] == "compact"
            else handlers[schema["name"]],
        )
```

`BASE_TOOL_SCHEMAS` is the ordered schema tuple moved from `BaseAgent.py` in
Task 3. `build_bound_handlers(...)` returns exactly these ordinary handler
names:

```text
bash, read_file, write_file, edit_file, glob, todo_write, load_skill,
create_task, list_tasks, get_task, claim_task, complete_task,
spawn_teammate, send_message, check_inbox, schedule_cron, list_crons,
cancel_cron, request_shutdown, request_plan, review_plan,
create_worktree, remove_worktree, keep_worktree, connect_mcp, task
```

The ordered schema tuple additionally contains `compact`, which deliberately
has no entry in the handler map.

`load_config()` is the only function that calls `load_dotenv(override=True)` and applies the current `ANTHROPIC_BASE_URL` token behavior. `build_anthropic_adapter()` is the only place that constructs `Anthropic`.

- [ ] **Step 7: Implement CLI and replace BaseAgent**

Implement the queue processor, thread startup, and injectable CLI lifecycle:

```python
def queue_processor_loop(
    runtime: RuntimeContext,
    stop_event: threading.Event,
) -> None:
    while not stop_event.wait(0.2):
        if not has_pending_jobs(runtime.scheduler):
            continue
        if not runtime.session.agent_lock.acquire(blocking=False):
            continue
        try:
            if has_pending_jobs(runtime.scheduler):
                run_agent_turn(runtime)
        finally:
            runtime.session.agent_lock.release()


def start_runtime_threads(
    runtime: RuntimeContext,
    stop_event: threading.Event,
) -> list[threading.Thread]:
    threads = [
        threading.Thread(
            target=scheduler_loop,
            args=(runtime.scheduler, stop_event),
            daemon=True,
            name="cron-scheduler",
        ),
        threading.Thread(
            target=queue_processor_loop,
            args=(runtime, stop_event),
            daemon=True,
            name="cron-queue-processor",
        ),
    ]
    for thread in threads:
        thread.start()
    return threads


def main(
    runtime_factory: Callable[[], RuntimeContext] = build_runtime,
    input_fn: Callable[[str], str] = input,
    start_threads: Callable[
        [RuntimeContext, threading.Event],
        list[threading.Thread],
    ] = start_runtime_threads,
) -> None:
    runtime = runtime_factory()
    print(
        "开拓者终于等到你了！欢迎使用Pamu帕！"
        "你可以输入 'q'，'exit'或 '空格符' 退出帕！。"
    )
    load_durable_jobs(runtime.scheduler)
    stop_event = threading.Event()
    threads = start_threads(runtime, stop_event)
    try:
        while True:
            try:
                query = input_fn("\033[36m>> \033[0m")
            except (EOFError, KeyboardInterrupt):
                break
            if query.strip().lower() in ("q", "exit", ""):
                break
            runtime.hooks.trigger("UserPromptSubmit", query)
            with runtime.session.agent_lock:
                run_agent_turn(runtime, query)
    finally:
        stop_event.set()
        for thread in threads:
            thread.join(timeout=1.0)
```

Replace `BaseAgent.py` with:

```python
if __package__:
    from .agent_app.cli import main
else:
    from agent_app.cli import main


if __name__ == "__main__":
    main()
```

Do not re-export any old functions, classes, registries, or state.

- [ ] **Step 8: Verify and commit the cutover**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent/test_loop.py tests/homework_agent/test_cli.py tests/homework_agent/test_recovery_adapter.py tests/homework_agent/test_scheduler_background.py tests/homework_agent/test_teams_subagents.py tests/homework_agent/test_memory_compaction.py tests/homework_agent/test_mcp.py -q
```

Expected: all new internal tests pass.

Run:

```bash
MODEL_ID=dummy uv run python -m py_compile homework/BaseAgent.py homework/agent_app/cli.py homework/agent_app/bootstrap.py homework/agent_app/core/loop.py
```

Expected: no output and exit code 0.

Commit:

```bash
git add homework/BaseAgent.py homework/agent_app tests/homework_agent
git commit -m "refactor: cut BaseAgent over to layered runtime"
```

---

### Task 14: Retire Global-Namespace Tests and Run Full Verification

**Files:**
- Delete:
  - `tests/test_homework_baseagent_todo_resume.py`
  - `tests/test_homework_baseagent_task_system.py`
  - `tests/test_homework_baseagent_background_tasks.py`
  - `tests/test_homework_baseagent_agent_teams.py`
  - `tests/test_homework_baseagent_error_recovery.py`
  - `tests/test_homework_baseagent_compact_tool.py`
- Modify: `tests/homework_agent/*.py` only if an old assertion has not yet been transferred.
- Verify: `homework/BaseAgent.py`
- Verify: `homework/agent_app/`

**Interfaces:**
- Consumes: all new feature/core/CLI tests.
- Produces: no test references `runpy.run_path(BaseAgent.py)`, `agent_loop.__globals__`, deprecated registries, or process-global state.

- [ ] **Step 1: Prove old coverage has an internal owner**

List every old test:

```bash
rg -n '^def test_' tests/test_homework_baseagent_todo_resume.py tests/test_homework_baseagent_task_system.py tests/test_homework_baseagent_background_tasks.py tests/test_homework_baseagent_agent_teams.py tests/test_homework_baseagent_error_recovery.py tests/test_homework_baseagent_compact_tool.py
```

For each behavior, confirm a corresponding test exists under `tests/homework_agent/`. Preserve every safety, concurrency, recovery, tool-pair, and persistence assertion; remove only loader/global-namespace mechanics.

- [ ] **Step 2: Delete obsolete tests and scan for forbidden coupling**

Delete the six old test modules, then run:

```bash
rg -n 'agent_loop.__globals__|runpy.run_path|\\["TOOLS"\\]|\\["TOOL_HANDLERS"\\]' tests homework/agent_app
```

Expected: no matches.

- [ ] **Step 3: Verify import and entry-point boundaries**

Run:

```bash
rg -n '^from .*BaseAgent|^import .*BaseAgent|from homework\\.BaseAgent' homework tests
```

Expected: no internal module imports `BaseAgent.py`.

Run:

```bash
rg -n 'Anthropic\\(|load_dotenv\\(|Thread\\(' homework/agent_app
```

Expected:

- `Anthropic(` appears only in adapter/bootstrap construction.
- `load_dotenv(` appears only in config loading.
- `Thread(` appears only in explicit runtime, background, and teammate lifecycle functions.

- [ ] **Step 4: Run focused and full verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider tests/homework_agent -q
```

Expected: all new layered BaseAgent tests pass.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pyyaml pytest -p no:cacheprovider -q
```

Expected: the entire repository test suite passes.

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; status contains only the intended test retirement and any pre-existing unrelated user files.

- [ ] **Step 5: Commit final test migration**

```bash
git add homework/BaseAgent.py homework/agent_app tests/homework_agent tests/test_homework_baseagent_todo_resume.py tests/test_homework_baseagent_task_system.py tests/test_homework_baseagent_background_tasks.py tests/test_homework_baseagent_agent_teams.py tests/test_homework_baseagent_error_recovery.py tests/test_homework_baseagent_compact_tool.py
git commit -m "test: migrate BaseAgent tests to internal modules"
```

## Final Review Checklist

- [ ] `BaseAgent.py` contains no function or class definitions.
- [ ] `agent_app/__init__.py` contains no re-exports.
- [ ] No feature imports `core.loop`.
- [ ] No feature reads a module-level runtime singleton.
- [ ] Every mutable registry, queue, lock, and session collection has one owner.
- [ ] No internal module creates directories or clients during import.
- [ ] Tool schema names and handler names match, except special `compact`.
- [ ] MCP tools are included in the current request immediately after connection.
- [ ] Scheduler/background/team notifications are drained only by the lead loop.
- [ ] Thread tests use deterministic events or injected waits.
- [ ] No test uses `agent_loop.__globals__`.
- [ ] Focused tests and the full repository suite pass.
