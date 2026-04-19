# Frontend Type Safety

Status: `Active` for `coding-deepgent/frontend/cli`

## Type Ownership

- Python protocol validation lives in `coding_deepgent.frontend.protocol`.
- TypeScript protocol types live in `frontend/cli/src/bridge/protocol.ts`.
- TS state types live in `frontend/cli/src/bridge/reducer.ts`.

## Rules

- `FrontendEvent` and `FrontendInput` should be discriminated unions by `type`.
- Keep `strict`, `noUncheckedIndexedAccess`, and `exactOptionalPropertyTypes` enabled.
- Python protocol models should reject extra fields.
- Runtime payload changes require Python protocol tests and TS reducer/protocol tests.
- Optional props should explicitly include `undefined` when passed through from state.
- Streaming payloads must use the same `message_id` across `assistant_delta`
  and the final `assistant_message`.
- Runtime visibility snapshots must be typed on both sides of the bridge:
  `context_snapshot` carries bounded projection counters and
  `subagent_snapshot` carries bounded recent sidechain activity.
  `background_subagent_snapshot` carries bounded live background-run status.
  Do not pass raw transcript records through the TUI protocol.
- Bridge control inputs such as `refresh_snapshots`, `run_background_subagent`,
  `subagent_send_input`, and `subagent_stop` must be added on both the Python
  and TS sides together.
- HITL payloads must preserve `permission_requested.request_id` end-to-end:
  for LangGraph interrupt-backed frontend flows, this id is the interrupt id and
  `permission_decision.request_id` must echo it unchanged on resume.

## Real Examples

- `coding-deepgent/frontend/cli/src/bridge/protocol.ts`
- `coding-deepgent/frontend/cli/src/bridge/reducer.ts`
- `coding-deepgent/src/coding_deepgent/frontend/protocol.py`

## Anti-Patterns

- `any` payloads crossing the bridge without validation
- adding event types only on one side of the Python/TS boundary
- permissive alias/fallback parsing for protocol fields
- rewriting or regenerating interrupt-backed `request_id` values in the UI layer
