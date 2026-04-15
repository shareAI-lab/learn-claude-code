# Error Handling

> Error handling conventions for the current `coding-deepgent` mainline.

---

## Overview

`coding-deepgent` is a local CLI/product runtime, not a web API service.

Default posture: **mixed but strict**.

Errors should be handled according to boundary:

- schema/domain validation errors should be explicit exceptions
- model-visible tool execution failures may return bounded `"Error: ..."` text
- CLI-facing failures should become `ClickException` / Typer exits
- recoverable middleware failures should fail open only when the contract says so

---

## Error Types

Common current types:

- `ValueError`
  - invalid schema values, invalid transitions, bad compact settings
- `KeyError`
  - missing task/plan/capability lookup
- `RuntimeError`
  - missing required runtime context or store
- `FileNotFoundError` / `NotADirectoryError`
  - missing local skill/plugin roots
- domain-specific runtime errors
  - `SessionLoadError` in `sessions.records`

Use custom error classes only when callers need to distinguish a domain failure
from generic validation/runtime failures.

---

## Boundary Patterns

### Decision Matrix

| Boundary | Default behavior | Reason |
|---|---|---|
| schema / Pydantic validation | raise `ValueError` or validation error | invalid input should fail tests and not be normalized silently |
| pure domain service | raise explicit exception | keeps business invariants enforceable |
| model-visible tool result | return bounded `"Error: ..."` when the error is part of the tool surface | lets the model observe and recover without crashing the whole loop |
| CLI command | convert expected failures to `ClickException` / `typer.Exit` | user-facing command output should be concise |
| middleware guard | deny through structured tool result/event where applicable | policy decisions are runtime facts |
| recoverable runtime pressure helper | fail open only when the relevant contract says so | context pressure helpers should not corrupt execution when optional storage/summarization fails |

### Schema and domain helpers

Raise explicit exceptions.

Examples:

- `todo.service` rejects multiple `in_progress` items with `ValueError`.
- `tasks.store` rejects invalid transitions and dependency cycles.
- `compact.artifacts` rejects invalid compact summaries/settings.

### Model-visible filesystem tools

Return bounded error text when the tool result itself is the model-visible
surface.

Examples:

- filesystem command timeout -> `"Error: Timeout (120s)"`
- missing text during edit -> `"Error: Text not found ..."`
- invalid regex -> `"Error: Invalid regex ..."`

### CLI boundary

Convert expected user-facing failures into `ClickException` or `typer.Exit`.

Examples:

- invalid session resume options
- missing session
- invalid compact option combinations

### Middleware/runtime pressure

Fail open only when explicitly required by contract.

Example:

- large tool-result persistence returns the original `ToolMessage` unchanged if
  file writing raises `OSError`.
- live compact summarization failure returns the original message list if the
  contract says proactive compact is best-effort.

---

## API Error Responses

There is currently no HTTP/API error response contract.

Do not add API-style error envelopes unless an actual API surface is introduced.
For CLI and tool-facing behavior, document the exact return/exception contract
in the relevant backend spec.

---

## Common Mistakes

- Swallowing domain validation errors that should fail tests.
- Returning model-visible `"Error: ..."` strings from pure domain helpers.
- Raising raw exceptions directly through CLI commands instead of converting to
  user-facing CLI errors.
- Failing open in middleware without an explicit contract.
- Adding alias/fallback parsing to hide invalid structured tool inputs.
