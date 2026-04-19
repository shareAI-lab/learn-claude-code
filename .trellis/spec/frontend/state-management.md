# Frontend State Management

Status: `Active` for `coding-deepgent/frontend/cli`

## State Ownership

- Python owns runtime/session/tool/todo facts.
- TypeScript owns display state derived from `FrontendEvent` payloads.
- `src/bridge/reducer.ts` is the canonical event-to-UI-state reducer.
- Components may own small local interaction state, such as the current prompt input.

## Rules

- Use `useReducer(reduceFrontendEvent, initialUiState)` for bridge events.
- Do not mutate `UiState` in place.
- Do not store Python subprocess handles in React state; keep them in bridge classes.
- Keep reducer behavior deterministic and covered by TS tests.
- Keep long-term/session persistence in Python, not frontend local storage.
- Local-only UI actions such as `/help` and `/clear` may use reducer actions,
  but Python runtime facts must still arrive through `FrontendEvent`.

## Real Examples

- `coding-deepgent/frontend/cli/src/bridge/reducer.ts`
- `coding-deepgent/frontend/cli/src/app.tsx`
- `coding-deepgent/frontend/cli/src/components/prompt-input.tsx`

## Anti-Patterns

- components directly editing `messages`, `todos`, or `pendingPermissions`
- deriving product truth from terminal text
- duplicating Python session persistence in TS state
