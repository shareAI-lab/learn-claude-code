# Tests

Run the full suite:

```bash
bun test
```

Run by category:

```bash
bun test tests/unit
bun test tests/integration
bun test tests/e2e
```

Notes:

- Real API tests are gated and skipped by default (see `tests/integration/production`).
- Tests write temporary data under the OS temp directory and/or short-lived temp dirs under the repo root, and should not leave artifacts after completion.
