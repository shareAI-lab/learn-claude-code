# coding-deepgent Tests

Product tests are grouped by domain so focused validation can match the
implementation boundary being changed.

## Layout

- `runtime/` - agent construction, app wiring, runtime events, runtime state.
- `subagents/` - subagent, fork, resume, background run, and verifier contracts.
- `tool_system/` - capability registry, tool policy middleware, deferred tools,
  and large tool-result storage.
- `sessions/` - JSONL session, recovery, evidence, contributions, and session
  memory continuity.
- `compact/` - compact artifacts, message projection, runtime pressure, and
  summarization support.
- `frontend/` - Python frontend protocol, JSONL bridge, and event mapping.
- `memory/` - long-term memory store, tools, middleware, CLI, and integration.
- `tasks/` - durable task graph, plan artifacts, TodoWrite, and planning renderers.
- `extensions/` - MCP, plugin, skill, and hook extension surfaces.
- `filesystem/` - workspace filesystem tools and path safety.
- `permissions/` - permission modes, rules, and filesystem policy integration.
- `cli/` - Typer/Rich CLI, renderer, resume, compact, doctor, and UI command paths.
- `config/` - settings, logging, prompting, rules, and context payload rendering.
- `structure/` - architecture, package shape, and tutorial/reference isolation.

## Command Groups

Run commands from `coding-deepgent/` unless noted otherwise.

Release smoke:

```bash
pytest -q tests/runtime tests/subagents tests/tool_system tests/sessions tests/frontend
npm --prefix frontend/cli run typecheck
npm --prefix frontend/cli test
```

Domain focused examples:

```bash
pytest -q tests/subagents
pytest -q tests/tool_system tests/permissions tests/filesystem
pytest -q tests/sessions tests/compact
pytest -q tests/frontend
pytest -q tests/memory
pytest -q tests/tasks
pytest -q tests/extensions
pytest -q tests/cli
pytest -q tests/config tests/structure
```

Deep regression:

```bash
pytest -q tests
npm --prefix frontend/cli run typecheck
npm --prefix frontend/cli test
```

## Cleanup Rules

- Do not delete contract coverage just to reduce test count.
- When merging or deleting a test, identify the replacement coverage first.
- Keep tests deterministic and no-network.
- Prefer shared fixtures only when they remove real duplication without hiding
  the boundary being asserted.
