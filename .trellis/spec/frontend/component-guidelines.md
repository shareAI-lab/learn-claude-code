# Frontend Component Guidelines

Status: `Active` for `coding-deepgent/frontend/cli`

## Component Rules

- Components are small React functions that return `React.ReactNode`.
- Props should be explicit object types near the component unless shared.
- Components consume already-reduced UI state; they should not parse JSONL or spawn Python.
- Presentational components live in `src/components/`.
- Bridge/process/protocol logic lives in `src/bridge/`.
- Prefer clear terminal affordances over heavy styling.

## Current Component Examples

- `PromptInput` owns local text-entry state and calls `onSubmit`.
- `MessageList` renders the bounded message window and delegates rows to `MessageRow`.
- `TodoPanel` renders a snapshot created by the reducer; it does not know Python state shape.

## Anti-Patterns

- reading process stdout directly inside components
- mutating shared UI state outside the reducer
- importing root `web/` components into product CLI
- copying cc components that require cc AppState or feature flags
