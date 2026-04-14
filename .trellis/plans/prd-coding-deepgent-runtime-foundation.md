<!-- Recovered on 2026-04-14 from local Codex/OMX session logs after OMX uninstall. High-fidelity reconstruction of the last known "professional domain" revision; not guaranteed byte-identical. -->
# PRD — coding-deepgent Professional Domain Runtime Foundation

Status: final ralplan plan, revised for dependency-injector + professional domain architecture
Scope: `coding-deepgent/` product code only. This planning step does not implement code.
Context snapshot: `.omx/context/coding-deepgent-runtime-foundation-20260412T213209Z.md`
Test spec: `.omx/plans/test-spec-coding-deepgent-runtime-foundation.md`

## 1. RALPLAN-DR Summary

### Principles
1. **Domain-first, LangChain-inside** — cc-haha defines long-term product domains; LangChain/LangGraph defines runtime integration seams.
2. **Explicit dependency graph** — use `dependency-injector` containers to make providers, overrides, and backend selection visible; do not hide business logic in containers.
3. **High cohesion, low coupling by contract** — each domain package owns one cc concept; domain logic depends on ports/protocols or local services, not concrete adapters from other domains.
4. **Functional skeleton, not empty architecture** — Stage 3 must deliver a working app skeleton: typed settings, DI composition, Typer CLI, Rich renderers, strict tools, TodoWrite, sessions, tool guard, local events.
5. **Professional foundations without cc clone drift** — no custom query loop, no LangChain bypass, no file-by-file cc mirror. Future cc features get landing zones and iterative stages.

### Decision Drivers
1. **Long-term cc feature growth** — permissions, hooks, subagents, compact, memory, skills, tasks, MCP, and observability need clear domain homes now.
2. **Replace hidden globals with explicit providers** — current module-global state/app wiring should evolve into container-composed runtime invocation and graph state.
3. **Developer clarity over minimal diffs** — the user explicitly prefers richer architecture if it makes future iteration clearer.

### Viable Options

#### Option A — Professional domain architecture with dependency-injector (favored)
Adopt domain packages plus `dependency-injector` containers, `pydantic-settings`, Typer/Rich CLI shell, and quality tooling. Keep LangChain as runtime and expose cc-like features through domains and adapters.

Pros:
- Clear object graph similar to Spring-style DI while remaining Pythonic.
- Strong testing story through provider override.
- Natural growth path for future cc features.
- High cohesion via domain packages and low coupling via containers/ports.

Cons:
- Adds dependencies and structural migration.
- Requires architecture tests to prevent container/service-locator abuse.
- More initial files than the current small app.

#### Option B — Domain packages with hand-written container only
Keep domain packages but avoid dependency-injector for now.

Pros:
- Fewer dependencies.
- Less framework surface.

Cons:
- Less clear provider graph as backends grow.
- User explicitly wants complex clarity and accepts dependencies.

#### Option C — Flat runtime-spine architecture
Keep most new modules under `runtime/`, `tools/`, and `middleware/`.

Pros:
- Smaller migration.

Cons:
- Lower long-term cohesion; `runtime/` will become a grab bag.
- Less aligned with cc domain evolution.

**Decision:** Choose Option A.

## 2. Accepted Dependency Additions

Stage 3 may add these dependencies to `coding-deepgent/pyproject.toml`.

### Runtime/product dependencies

- `dependency-injector` — composition root, providers, provider overrides, selector/resource providers later.
- `pydantic-settings` — typed settings from environment/dotenv/secrets.
- `typer` — professional CLI command groups.
- `rich` — terminal rendering for todos, sessions, events, diagnostics.
- `structlog` — structured local logging foundation.

### Dev dependencies

- `ruff` — lint/format.
- `mypy` or `pyright` — static typing gate. Prefer one as required; allow the other later.
- `pytest-cov` — optional coverage evidence if execution wants coverage gates.

### Deferred but approved for future stages

- `pluggy` — future hook/plugin stage.
- Python package entry points via `importlib.metadata` — future plugin discovery, no dependency.
- OpenTelemetry Python — future production observability/tracing.
- SQLAlchemy + Alembic — future durable business persistence for tasks/memory/session indexes if LangGraph store/checkpointer is insufficient.
- persistent LangGraph checkpointer package, e.g. sqlite/postgres backend — future persistence ADR.

## 3. Product Stage Definition

Advance product metadata to:

```text
current_product_stage = stage-3-professional-domain-runtime-foundation
compatibility_anchor = professional-domain-runtime-foundation
shape = staged_langchain_cc_product
```

This stage creates a professional functional skeleton, not full cc parity.

## 4. Target Architecture

```text
coding_deepgent/
  app.py                 # create_agent wiring target
  cli.py                 # Typer app entrypoint
  settings.py            # pydantic-settings Settings
  config.py              # compatibility facade during migration
  state.py               # compatibility facade during migration

  containers/
    __init__.py
    app.py               # AppContainer composition root
    runtime.py
    tool_system.py
    filesystem.py
    todo.py
    sessions.py
    cli.py               # optional CLI providers

  runtime/
    __init__.py
    context.py           # RuntimeContext
    state.py             # RuntimeState
    invocation.py        # RuntimeInvocation assembly
    checkpointing.py     # checkpointer/store provider seam
    events.py            # local RuntimeEvent / sink
    logging.py           # structlog config, if implemented

  tool_system/
    __init__.py
    capabilities.py      # authoritative registry
    policy.py            # shared policy decisions/reason codes
    middleware.py        # ToolGuardMiddleware
    results.py           # future tool result refs; may defer
    ports.py             # Protocols only if multiple implementations exist

  filesystem/
    __init__.py
    schemas.py
    tools.py
    discovery.py         # glob/grep
    policy.py            # filesystem-specific policy/backstop if needed

  todo/
    __init__.py
    schemas.py
    state.py
    service.py
    tools.py
    middleware.py
    renderers.py

  sessions/
    __init__.py
    records.py
    ports.py
    store_jsonl.py
    resume.py
    langgraph.py         # thread_id/checkpointer bridge

  renderers/
    __init__.py
    text.py

  permissions/           # future
  hooks/                 # future
  subagents/             # future
  compact/               # future
  memory/                # future
  skills/                # future
  resources/             # future
  tasks/                 # future
  mcp/                   # future
```

## 5. High Cohesion / Low Coupling Reflection

### Current plan strengths

- Domain packages (`todo`, `filesystem`, `sessions`, `tool_system`) are cohesive around cc product concepts.
- LangChain adapters live near domains (`tools.py`, `middleware.py`) instead of centralizing all behavior in `app.py`.
- `containers/` makes dependencies explicit and test-overridable.
- `runtime/` is limited to cross-domain LangGraph spine.

### Coupling risks and mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Containers become service locator | Hidden runtime dependencies can spread everywhere | Domain modules must not import containers; only app/cli/tests compose through containers. |
| Domain packages import each other directly | Todo/filesystem/sessions could form cycles | Cross-domain coordination goes through `tool_system`, `runtime`, or application services. |
| LangChain adapters pollute pure domain logic | Makes service logic hard to test | Keep pure helpers in `service.py`; LangChain `@tool`/middleware in adapter files. |
| Rich/Typer leak into domain | Ties business logic to terminal UI | Rich/Typer only in CLI/renderers, never schemas/state/services. |
| Tool system becomes god module | It could absorb permissions/hooks/MCP/task logic | `tool_system` owns only tool registry/policy/guard/result refs; future domains remain separate. |
| `sessions/` becomes storage for everything | Memory/tasks/compact could collapse into sessions | Sessions owns transcript/resume only; durable tasks/memory/compact get own domains later. |

### Enforceable rules

1. Domain code never imports `containers.*`.
2. Domain `schemas.py` and `state.py` never import LangChain runtime objects except where unavoidable for `AgentState` in state modules.
3. LangChain-specific adapters are named clearly: `tools.py`, `middleware.py`.
4. `containers/*` contains no business rules.
5. Cross-domain references must be one-way through ports/protocols or container wiring.
6. Tests must fail if forbidden mirror files appear: `runtime/query.py`, `tool_executor.py`, `app_state_store.py`.

## 6. cc Source Concepts Projected onto Modules

| cc-haha concept | coding-deepgent domain | LangChain implementation seam |
|---|---|---|
| `query.ts` | `runtime` + `app.py` | `create_agent`, `context=`, `config.thread_id`, middleware |
| `Tool.ts` | `tool_system` | LangChain tools + capability metadata |
| `ToolUseContext` | `runtime/context.py`, `runtime/state.py` | `context_schema`, `state_schema`, `ToolRuntime` when needed |
| `AppStateStore` | runtime state slices + domain state | `AgentState`, checkpointer, store; no monolithic clone |
| `toolExecution` / `toolOrchestration` | `tool_system` | `wrap_tool_call`, shared policy, capability registry |
| `TodoWriteTool/*` | `todo` | Pydantic schema + `@tool` + `Command(update)` + middleware |
| Bash/Read/Write/Edit/Grep/Glob | `filesystem` | strict tools, policy backstop |
| session logs/storage | `sessions` | JSONL store + LangGraph thread bridge |
| hooks | future `hooks` | `AgentMiddleware` lifecycle hooks, later pluggy |
| permissions | future `permissions` | tool guard / HITL interrupt later |
| compact | future `compact` | middleware + tool result refs + summaries |
| memory/skills/resources | future domains | LangGraph store + resource descriptors + middleware |
| durable tasks/background | future `tasks` | store-backed tools/state, distinct from TodoWrite |
| MCP/plugins | future `mcp`/plugins | capability registry + entry points/pluggy later |

## 7. Functional Skeleton in Stage 3

Stage 3 should deliver a working skeleton, not only folders:

1. **Containerized app construction**
   - `AppContainer` can build settings, session store, capability registry, middleware, and LangChain agent.
   - Tests override model/session/event providers.
2. **Typed settings**
   - `Settings` reads environment with `pydantic-settings`.
   - Existing `config.py` remains compatibility facade.
3. **Typer CLI + Rich rendering**
   - Commands: `run`, `sessions list`, `sessions resume`, `config show`, `doctor`.
   - Rich renders todo list, session table, and local runtime events.
4. **Todo domain**
   - Current TodoWrite behavior migrated into `todo/`.
   - Public contract unchanged.
5. **Filesystem domain**
   - Strict schemas for bash/read/write/edit.
   - Add `glob`/`grep` if execution scope permits.
6. **Tool system**
   - Registry drives tool list.
   - Shared policy and guard middleware emit local event evidence.
7. **Sessions domain**
   - JSONL transcript/resume preserved.
   - Session ID flows into RuntimeContext and LangGraph thread config.
8. **Local events/logging**
   - Runtime events testable in memory.
   - `structlog` configured for local structured logs if execution includes logging slice.

## 8. Requirements Summary

### In Scope

- Add accepted dependencies.
- Restructure into domain packages with compatibility facades.
- Add `containers/` and `AppContainer`.
- Add typed settings via `pydantic-settings`.
- Migrate TodoWrite into `todo/`.
- Migrate filesystem tools into `filesystem/` and strict schemas.
- Add `tool_system/` registry/policy/middleware.
- Add `runtime/` context/state/invocation/events/checkpointing spine.
- Split `sessions/` package or keep facade with staged split if vertical churn is too high.
- Upgrade CLI to Typer/Rich skeleton.
- Add local structured logging/events skeleton.
- Update docs/status/tests.

### Out of Scope

- `agents_deepagents/` changes.
- Custom query loop.
- Full cc executor/StreamingToolExecutor.
- Monolithic AppStateStore clone.
- FastAPI server/API layer.
- External plugin runtime with pluggy/entry points.
- Production OpenTelemetry instrumentation.
- SQLAlchemy/Alembic persistence implementation.
- Permissions/hooks/subagents/compact/memory/tasks/MCP implementation beyond package landing zones and roadmap.
- UI/TUI beyond Rich terminal rendering.

## 9. Acceptance Criteria

1. `pyproject.toml` includes approved dependencies and dev dependencies.
2. `AppContainer` is the composition root and supports provider override in tests.
3. Domain modules do not import containers.
4. `app.py` still uses LangChain `create_agent`.
5. `RuntimeContext`/`RuntimeState` are wired via `context_schema`/`state_schema`.
6. `TodoWrite` public contract remains unchanged and cc-aligned.
7. Filesystem tools use explicit strict Pydantic schemas.
8. Capability registry is authoritative for agent tool list.
9. Tool guard uses shared policy and preserves `Command(update=...)` tools.
10. Typer CLI commands work without model credentials for help/config/session listing.
11. Rich renderers are isolated from domain services.
12. JSONL sessions remain backward compatible.
13. No forbidden cc mirror modules are added.
14. Full `cd coding-deepgent && pytest` passes.
15. Ruff and type-check commands are documented and pass if included in execution gate.

## 10. Implementation Plan — Professional Architecture Slices

### Slice 0 — Regression, dependencies, and architecture contract

Files:
- `pyproject.toml`
- `tests/test_structure.py`
- `tests/test_contract.py`

Actions:
- Add dependency/dependency-absence tests.
- Add architecture tests for container/domain boundaries.
- Lock current TodoWrite/session behavior.

### Slice 1 — Settings and containers

Files:
- `settings.py`
- `containers/__init__.py`
- `containers/app.py`
- `containers/runtime.py`
- `containers/sessions.py`
- `containers/todo.py`
- `containers/filesystem.py`
- `containers/tool_system.py`
- `config.py` compatibility facade

Actions:
- Add `Settings` with pydantic-settings.
- Add `AppContainer` and subcontainers.
- Keep domain code container-free.

### Slice 2 — Runtime spine

Files:
- `runtime/context.py`
- `runtime/state.py`
- `runtime/invocation.py`
- `runtime/events.py`
- `runtime/checkpointing.py`

Actions:
- Define context/state/invocation/config.thread_id.
- Add event sink.
- Add checkpointer/store selector seam via DI container.

### Slice 3 — Todo domain migration

Files:
- `todo/schemas.py`
- `todo/state.py`
- `todo/service.py`
- `todo/tools.py`
- `todo/middleware.py`
- `todo/renderers.py`
- compatibility facades from old modules

Actions:
- Move TodoWrite contract.
- Preserve public imports where needed.
- Remove mutable middleware turn state.

### Slice 4 — Filesystem domain migration

Files:
- `filesystem/schemas.py`
- `filesystem/tools.py`
- `filesystem/discovery.py`
- `filesystem/policy.py`
- compatibility facade from old `tools/filesystem.py`

Actions:
- Strict schemas.
- Preserve existing behavior.
- Add glob/grep if included.

### Slice 5 — Tool system domain

Files:
- `tool_system/capabilities.py`
- `tool_system/policy.py`
- `tool_system/middleware.py`
- optional `tool_system/results.py`

Actions:
- Registry drives tool list.
- Shared policy reason codes.
- Guard middleware emits runtime events.

### Slice 6 — Sessions domain

Files:
- `sessions/records.py`
- `sessions/ports.py`
- `sessions/store_jsonl.py`
- `sessions/resume.py`
- `sessions/langgraph.py`
- compatibility facade from old `sessions.py`

Actions:
- Preserve JSONL behavior.
- Add ports/protocols.
- Add LangGraph thread bridge.

### Slice 7 — CLI shell

Files:
- `cli.py`
- optional `containers/cli.py`
- `renderers/text.py`
- Rich renderers in relevant domains

Actions:
- Convert to Typer command groups.
- Use Rich for session/todo/event display.
- Preserve existing command behavior or document migration.

### Slice 8 — Logging/docs/final verification

Files:
- `runtime/logging.py`
- `README.md`
- `PROJECT_PROGRESS.md`
- `project_status.json`
- `docs/runtime-foundation.md`

Actions:
- Configure structlog if included.
- Update docs with architecture and roadmap.
- Run full verification.

## 11. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Too much architecture before behavior | Stage 3 includes functional skeleton: CLI, TodoWrite, filesystem tools, sessions, guard events. |
| Containers become service locator | Forbid domain imports from containers; container is composition-only. |
| Package migration breaks compatibility | Use facades and regression tests. |
| DI framework hides dependencies | Prefer provider construction and explicit container use; avoid widespread `@inject` initially. |
| Rich/Typer leak into domain logic | Keep them in CLI/renderers only. |
| Tool system becomes god module | Keep permissions/hooks/MCP/tasks in future domains. |
| Type/lint burden slows migration | Add tooling but allow staged strictness. |
| New dependencies bloat project | Dependencies are explicitly approved and tested via pyproject checks. |

## 12. Verification Commands

```bash
cd coding-deepgent
pytest
ruff check .
ruff format --check .
mypy src/coding_deepgent tests
python -m coding_deepgent --help
coding-deepgent --help
```

Architecture grep:

```bash
rg -n "agents_deepagents|s[0-9]{2}_" src tests
rg -n "runtime/query.py|tool_executor.py|app_state_store.py|class Tool\(" src tests
rg -n "from coding_deepgent.containers|import coding_deepgent.containers" src/coding_deepgent/todo src/coding_deepgent/filesystem src/coding_deepgent/sessions src/coding_deepgent/tool_system
rg -n "FastAPI|Depends|pluggy|opentelemetry|SQLAlchemy|Alembic" src tests
rg -n "dict\[str, Any\]|normalize_.*\(|fallback|alias|ToolRuntime|InjectedToolCallId" src/coding_deepgent tests
```

## 13. Roadmap Toward cc Parity

1. **Stage 3 — Professional domain runtime foundation**
   - This plan.
2. **Stage 4 — Tool control + permissions MVP**
   - permission modes, allow/deny rules, CLI confirmation seam.
3. **Stage 5 — Hooks MVP**
   - internal pre/post/failure hooks; evaluate pluggy later.
4. **Stage 6 — Subagents / AgentTool**
   - agent identity, sidechain sessions, per-agent todos.
5. **Stage 7 — Context compact / tool result store**
   - compactable tool refs, summaries, active todo preservation.
6. **Stage 8 — Memory / skills / resources**
   - resource descriptors, lazy skill loading, LangGraph store memory.
7. **Stage 9 — Durable task/background runtime**
   - task records, dependencies, background execution slots.
8. **Stage 10 — MCP / plugin system**
   - MCP adapters, entry points/pluggy if needed, capability registry integration.
9. **Stage 11 — Observability and product shell**
   - OpenTelemetry, richer Rich/Textual UI if justified, production logs.

## 14. ADR — Professional Domain Architecture with DI

### Decision
Adopt `dependency-injector`, `pydantic-settings`, Typer, Rich, structlog, and dev tooling as part of a domain-first LangChain cc architecture. Use DI containers for composition, not business logic.

### Drivers
- User prefers professional complexity that clarifies long-term iteration.
- Future cc domains need explicit dependencies and replaceable implementations.
- Python large projects benefit from composition roots, typed settings, ports/adapters, and provider overrides.

### Alternatives Considered
- Hand-written container only: rejected because DI clarity is desired and future provider graph will grow.
- Flat runtime modules: rejected as less cohesive long-term.
- Spring-like magic everywhere: rejected; use containers explicitly and avoid broad wiring initially.

### Why Chosen
This combines cc domain boundaries with LangChain runtime seams and a clear Python dependency graph.

### Consequences
- Initial migration is larger.
- Tests must enforce container/domain separation.
- Dependency management becomes part of architecture.

### Follow-ups
- Consider Pydantic settings strictness and secrets sources.
- Consider persistent checkpointer/store backend.
- Consider pluggy/entry points only during plugin stage.
- Consider OpenTelemetry only during observability stage.

## 15. Staffing Guidance

### Ralph path

```text
$ralph .omx/plans/prd-coding-deepgent-runtime-foundation.md .omx/plans/test-spec-coding-deepgent-runtime-foundation.md
```

Sequence:
1. Dependency/tooling + structure tests.
2. Containers/settings.
3. Runtime spine.
4. Todo/filesystem domains.
5. Tool system/sessions.
6. CLI/Rich/logging.
7. Docs/status + full verification.

### Team path

```text
$team .omx/plans/prd-coding-deepgent-runtime-foundation.md
```

Lanes:
1. **Container/settings/runtime lane** — `containers/*`, `settings.py`, `runtime/*`, app wiring.
2. **Todo/filesystem lane** — `todo/*`, `filesystem/*`, compatibility facades.
3. **Tool-system/sessions lane** — `tool_system/*`, `sessions/*`.
4. **CLI/rendering/logging lane** — Typer/Rich/structlog/docs.
5. **Tests lane** — architecture, schema, container override, CLI, session, full regression.
6. **Verification lane** — pytest, ruff, mypy, grep, final evidence.
