<!-- Recovered on 2026-04-14 from local Codex/OMX session logs after OMX uninstall. High-confidence recovery of the final "professional domain" test spec. -->
# Test Specification — coding-deepgent Professional Domain Runtime Foundation

Status: final test spec for dependency-injector + domain-first architecture
Scope: no-network verification for `.trellis/plans/prd-coding-deepgent-runtime-foundation.md`.

## 1. Test Strategy

Tests must prove high cohesion, low coupling, dependency clarity, LangChain-native runtime behavior, and functional skeleton behavior. Tests should run without live model credentials.

Primary gates:

```bash
cd coding-deepgent
pytest
ruff check .
ruff format --check .
mypy coding-deepgent/src/coding_deepgent coding-deepgent/tests
```

## 2. Dependency and Tooling Tests

Files:
- `pyproject.toml`
- `coding-deepgent/tests/structure/test_structure.py`

Required cases:
1. Runtime dependencies include `dependency-injector`, `pydantic-settings`, `typer`, `rich`, `structlog`.
2. Dev dependencies include `ruff` and one type checker (`mypy` preferred or `pyright`).
3. No unplanned runtime dependencies are added.
4. `dependency-injector` is used only in `containers/`, `app.py`, `cli.py`, and tests; domain packages do not import containers.
5. `pydantic-settings` is used by `settings.py`, not scattered across domains.

## 3. Container Tests

Files:
- Add `coding-deepgent/tests/runtime/test_container.py`

Required cases:
1. `AppContainer` can instantiate settings, session store, capability registry, middleware list, and agent.
2. Providers can be overridden in tests for fake model/session store/event sink.
3. Container does not contain business rules: no tool execution helpers, no TodoWrite update logic, no session JSONL parsing.
4. Subcontainers exist for runtime, todo, filesystem, tool_system, sessions.
5. Container supports backend selectors for checkpointer/store/session where implemented.

## 4. Settings Tests

Files:
- Add/update `coding-deepgent/tests/config/test_settings.py`
- Update `coding-deepgent/tests/config/test_config.py`

Required cases:
1. `Settings` loads defaults.
2. Environment variables override expected settings.
3. Workdir/session dir/model/checkpointer/store/permission settings are typed.
4. Existing `load_settings()` compatibility behavior remains or is intentionally migrated.
5. Secrets/API keys are not printed in config output.

## 5. Architecture / Cohesion / Coupling Tests

Files:
- Update `coding-deepgent/tests/structure/test_structure.py`
- Update `coding-deepgent/tests/structure/test_contract.py`

Required cases:
1. Required domain packages exist: `runtime`, `tool_system`, `filesystem`, `todo`, `sessions`, `containers`.
2. No forbidden cc mirror modules: `runtime/query.py`, `tool_executor.py`, `app_state_store.py`, custom `Tool` base class.
3. Domain packages do not import `containers`.
4. CLI/Rich imports do not appear in domain `schemas.py`, `state.py`, or `service.py`.
5. Session domain does not import future memory/task/compact/subagent/MCP domains.
6. Tool system does not import permissions/hooks/MCP/tasks future domains.
7. `app.py` uses `create_agent`.
8. No `agents_deepagents` imports and no public `sNN` modules.

## 6. Runtime Spine Tests

Files:
- `coding-deepgent/tests/runtime/test_runtime_context.py`
- `coding-deepgent/tests/runtime/test_runtime_state.py`
- `coding-deepgent/tests/runtime/test_app.py`

Required cases:
1. `RuntimeContext` carries session/workdir/entrypoint/agent identity/event sink.
2. `RuntimeState` extends `AgentState` and contains todos/rounds.
3. Runtime invocation maps session id to LangGraph `thread_id`.
4. `agent_loop()` passes `context=` and `config=` to fake compiled agent.
5. Module-global runtime state is not the source of truth.
6. Checkpointer/store providers can be none/memory according to settings.

## 7. Todo Domain Tests

Files:
- `coding-deepgent/tests/tasks/test_todo_domain.py` or existing planning tests

Required cases:
1. Todo schemas are strict Pydantic models.
2. `TodoWrite` tool name/schema remains unchanged.
3. `Command(update=...)` shape remains correct.
4. Middleware injects current todos, stale reminders, and rejects parallel TodoWrite.
5. Renderer output remains stable.
6. Todo domain does not import filesystem/sessions/container directly.

## 8. Filesystem Domain Tests

Files:
- `coding-deepgent/tests/filesystem/test_filesystem_domain.py`
- `coding-deepgent/tests/tool_system/test_tool_schemas.py`

Required cases:
1. bash/read/write/edit schemas are explicit and strict.
2. Extra fields and aliases fail.
3. Dangerous command and workspace escape behavior preserved.
4. glob/grep, if included, are read-only strict tools.
5. Filesystem domain does not import Todo/session/container.

## 9. Tool System Tests

Files:
- `coding-deepgent/tests/tool_system/test_tool_system_capabilities.py`
- `coding-deepgent/tests/tool_system/test_tool_system_policy.py`
- `coding-deepgent/tests/tool_system/test_tool_system_middleware.py`

Required cases:
1. Capability registry is authoritative for agent tool list.
2. Registry metadata is present for all current tools.
3. Shared policy reason codes are stable.
4. Guard middleware allows safe calls and blocks/records unsafe calls.
5. Guard preserves handler return values and `Command(update=...)`.
6. Runtime events emitted through event sink when guard allows/blocks.

## 10. Sessions Tests

Files:
- `coding-deepgent/tests/sessions/test_sessions.py`
- optional `coding-deepgent/tests/sessions/test_sessions_domain.py`

Required cases:
1. JSONL transcript roundtrip remains stable.
2. Resume restores state snapshots.
3. Same-workdir filtering works.
4. Session ID flows into RuntimeContext and LangGraph `thread_id`.
5. Compatibility imports remain if `sessions.py` becomes facade.
6. Session domain remains transcript/resume only.

## 11. CLI / Rich Tests

Files:
- `coding-deepgent/tests/cli/test_cli.py`
- optional `coding-deepgent/tests/cli/test_renderers.py`

Required cases:
1. Typer CLI help works with no credentials.
2. Commands exist: `run`, `sessions list`, `sessions resume`, `config show`, `doctor` or documented subset.
3. Existing CLI behavior remains available or migration is documented.
4. Rich renderers produce stable text/table output in tests.
5. CLI uses container providers and can override fake agent/session store.

## 12. Logging / Events Tests

Files:
- `coding-deepgent/tests/runtime/test_runtime_events.py`
- optional `coding-deepgent/tests/config/test_logging.py`

Required cases:
1. Runtime event sink records ordered local events.
2. structlog config can initialize without external services.
3. No secrets/API keys appear in rendered logs/config output.
4. Events are local and not graph state by default.

## 13. Local Smoke Checks

```bash
cd coding-deepgent
python -m coding_deepgent --help
coding-deepgent --help
coding-deepgent config show
coding-deepgent sessions list
pytest coding-deepgent/tests/cli/test_cli.py coding-deepgent/tests/runtime/test_app.py coding-deepgent/tests/sessions/test_sessions.py
```

No live model call is required.

## 14. Review / Grep Checks

```bash
rg -n "agents_deepagents|s[0-9]{2}_" src tests
rg -n "runtime/query.py|tool_executor.py|app_state_store.py|class Tool\(" src tests
rg -n "from coding_deepgent.containers|import coding_deepgent.containers" coding-deepgent/src/coding_deepgent/todo coding-deepgent/src/coding_deepgent/filesystem coding-deepgent/src/coding_deepgent/sessions coding-deepgent/src/coding_deepgent/tool_system
rg -n "FastAPI|Depends|pluggy|opentelemetry|SQLAlchemy|Alembic" src tests
rg -n "dict\[str, Any\]|normalize_.*\(|fallback|alias|ToolRuntime|InjectedToolCallId" coding-deepgent/src/coding_deepgent tests
```

Expected interpretation:
- `InjectedToolCallId` expected for TodoWrite only.
- `FastAPI`, `pluggy`, `opentelemetry`, `SQLAlchemy`, `Alembic` may appear only in docs/roadmap for this stage.
- `dict[str, Any]` allowed in message/session plumbing, not structured tool-input fallback.

## 15. Exit Criteria

1. All focused tests pass.
2. Full `pytest` passes.
3. Ruff check and format check pass.
4. Type-check command passes or documented initial strictness baseline is accepted.
5. CLI smoke passes without credentials.
6. No forbidden imports/modules are present.
7. Container/domain boundaries are enforced by tests.
8. Docs/status reflect `stage-3-professional-domain-runtime-foundation`.
9. No live network/model call is required for verification.
