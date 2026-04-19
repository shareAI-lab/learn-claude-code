# Frontend Quality Guidelines

Status: `Active` for `coding-deepgent/frontend/cli`

## Required Checks

Run from `coding-deepgent/frontend/cli`:

```bash
npm run typecheck
npm test
```

For repo-local product smoke, run from `coding-deepgent`:

```bash
PYTHONPATH=src python3 -m coding_deepgent ui-bridge --fake
PYTHONPATH=src python3 -m coding_deepgent ui --fake
```

Run focused Python tests from `coding-deepgent` when bridge/protocol behavior changes:

```bash
pytest -q tests/frontend/test_frontend_protocol.py tests/frontend/test_frontend_bridge.py tests/frontend/test_frontend_event_mapping.py
```

When frontend HITL / permission pause-resume behavior changes, also include:

```bash
pytest -q tests/tool_system/test_tool_system_middleware.py
```

## Test Expectations

- TS tests should cover protocol parsing and reducer behavior.
- Python tests should cover strict protocol validation, bridge event order,
  streaming deltas, and event mapping.
- For interrupt-backed permission flows, Python tests should cover
  `permission_requested` emission, `permission_decision` resume, and bounded
  reject behavior.
- Smoke test the fake interactive CLI in a TTY when changing input/exit behavior.

## Anti-Patterns

- relying only on manual terminal testing
- changing protocol payloads without updating both Python and TS tests
- adding unbounded terminal output snapshots as tests
