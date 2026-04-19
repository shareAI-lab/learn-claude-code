# Frontend Directory Structure

Status: `Active` for `coding-deepgent/frontend/cli`

Current product frontend target:

```text
coding-deepgent/frontend/cli
```

Root `web/` remains reference-only.

## Directory Layout

```text
coding-deepgent/frontend/
├── protocol/                  # renderer-neutral JSONL contract docs
└── cli/                       # React/Ink CLI frontend package
    ├── package.json
    ├── tsconfig.json
    └── src/
        ├── index.tsx          # CLI entrypoint
        ├── app.tsx            # Ink root composition
        ├── bridge/            # Python process bridge, protocol types, reducer
        ├── components/        # presentational Ink components
        └── __tests__/         # TS unit tests
```

Python bridge/backend code belongs in:

```text
coding-deepgent/src/coding_deepgent/frontend/
├── protocol.py                # renderer-neutral event/input models
├── producer.py                # runtime event producer, no transport ownership
├── client.py                  # embedded in-process client for scripts/tests
├── runs.py                    # run lifecycle for future network adapters
├── stream_bridge.py           # replayable event log for SSE/gateway use
├── bridge.py                  # backward-compatible imports only
└── adapters/
    ├── jsonl.py               # stdio JSONL transport for React/Ink CLI
    └── sse.py                 # SSE formatter/consumer for future Web
```

## Rules

- Keep protocol types and event reducers in `src/bridge/`.
- Keep Ink rendering components in `src/components/`.
- Keep runtime/backend behavior in Python `coding_deepgent.frontend`, not in TS UI components.
- Keep runtime event generation in `coding_deepgent.frontend.producer`.
- Keep transport-specific code under `coding_deepgent.frontend.adapters`.
- Do not let runtime/domain packages import `coding_deepgent.frontend.adapters`
  or `coding_deepgent.frontend.bridge`.
- Do not import from root `web/` or tutorial/reference directories.
- Keep `node_modules/` ignored and commit `package-lock.json`.

## Real Examples

- `coding-deepgent/frontend/cli/src/bridge/protocol.ts`
- `coding-deepgent/frontend/cli/src/bridge/reducer.ts`
- `coding-deepgent/frontend/cli/src/components/message-list.tsx`
- `coding-deepgent/src/coding_deepgent/frontend/producer.py`
- `coding-deepgent/src/coding_deepgent/frontend/adapters/jsonl.py`
- `coding-deepgent/src/coding_deepgent/frontend/client.py`
- `coding-deepgent/src/coding_deepgent/frontend/runs.py`
- `coding-deepgent/src/coding_deepgent/frontend/stream_bridge.py`

## Anti-Patterns

- putting Python runtime decisions inside TS components
- parsing Rich terminal output in the frontend
- treating root `web/` tutorial code as product frontend source
- copying large cc React/Ink runtime files wholesale
- making Web depend on the JSONL CLI adapter
