# Runtime Context And Compaction Contracts

> Index for `coding-deepgent` runtime context, session continuity, compact, and pressure-management contracts.

This file is intentionally an overview. The executable contracts are split into focused docs so future agents can load only the relevant contract surface.

## Contract Files

| Contract | Scope | Read when changing |
|---|---|---|
| [Tool Result Storage Contracts](./tool-result-storage-contracts.md) | Large tool-result persistence, preview references, model-visible persisted output markers | `tool_system`, large-output tools, persisted tool-output previews |
| [Session Compact Contracts](./session-compact-contracts.md) | Session resume, manual/generated compact, compact transcript records, session memory, memory quality | `sessions`, CLI resume, compact artifacts, memory quality/session-memory continuity |
| [Runtime Pressure Contracts](./runtime-pressure-contracts.md) | Live microcompact, auto/reactive compact, restoration messages, runtime pressure events/evidence | `compact.runtime_pressure`, model-call middleware, runtime pressure settings/events |

## Maintenance Rules

- Keep contract details in the focused files above.
- Add new runtime/compact scenarios to the narrowest file that owns the behavior.
- If a new scenario crosses all three surfaces, add a short coordination note here and detailed rules in each focused contract.
- Use `coding-deepgent/tests/...` and `coding-deepgent/src/...` paths in new test/implementation references.
