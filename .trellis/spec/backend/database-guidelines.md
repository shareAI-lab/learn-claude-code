# Database Guidelines

> Persistence guidance for the current `coding-deepgent` mainline.

---

## Current Status

`coding-deepgent` now uses a mixed persistence model:

- JSONL transcript ledger for session history / evidence / compact / resume
- relational storage for long-term memory backend
- queue-backed background processing for memory jobs
- object storage for snapshot/archive payloads

Current relational/object-backed surfaces:

- durable long-term memory records
- memory versions / audit history
- memory extraction job state
- agent memory scope metadata
- snapshot/archive objects

Recommended long-term memory table family:

- `memory_records`
- `memory_versions`
- `memory_extraction_jobs`
- `agent_memory_scopes`

Current durable/stateful surfaces are:

- LangGraph store/checkpointer seams in `coding_deepgent.runtime.checkpointing`
- JSONL session transcripts in `coding_deepgent.sessions.store_jsonl`
- database-backed long-term memory records in `memory/`
- LangGraph store-backed task/plan records in `tasks/`
- workspace-local persisted tool outputs under `.coding-deepgent/tool-results/`

SQL/ORM/migration infrastructure is now allowed only for the long-term memory
backend and explicitly approved future domains. It is still not the default for
sessions/transcript storage.

---

## Store Patterns

Preferred patterns:

- Use relational storage for durable long-term memory backend records that need:
  - process-surviving persistence
  - audit/version history
  - job status tracking
  - agent memory scope metadata
- Use queue-backed background jobs for automatic extraction and snapshot refresh
  rather than blocking the main prompt loop.
- Keep large snapshot/archive payloads in object storage instead of the main
  relational tables.
- Continue to use LangGraph store-compatible APIs where a lighter-weight store
  seam is still sufficient, such as durable task/plan records.
- Keep namespace ownership inside the owning domain.
- Store Pydantic `model_dump()` payloads for typed records.
- Validate records before writing and when reconstructing from storage.

Examples:

- `coding_deepgent.memory.backend`
- `coding_deepgent.memory.service`
- `coding_deepgent.tasks.store`
- `coding_deepgent.runtime.checkpointing`

---

## Session Persistence

Session transcript persistence belongs to `sessions/`.

Rules:

- Use `JsonlSessionStore` for local transcript, evidence, compact, and state
  snapshot records.
- Keep session storage append-oriented unless a Trellis contract explicitly says
  otherwise.
- Keep session evidence, compact records, and state snapshots distinct instead
  of merging them into one generic blob.

Examples:

- `coding_deepgent.sessions.store_jsonl`
- `coding_deepgent.sessions.records`
- `coding_deepgent.sessions.evidence_events`

---

## Migrations

The long-term memory backend must define:

- target storage backend
- schema ownership
- migration command surface
- rollback strategy
- validation and error matrix
- tests proving old records are handled safely

Transcript/session migration remains a separate future project and must not be
folded into ordinary memory-backend changes.

---

## Common Mistakes

- Treating `sessions/` as generic durable storage for unrelated domains.
- Moving transcript/session ledger into SQL just because JSON can be stored there.
- Hiding task/memory schema evolution in ad hoc dict writes.
- Reusing one store namespace for multiple domain concepts.
