# Database Guidelines

> Persistence guidance for the current `coding-deepgent` mainline.

---

## Current Status

`coding-deepgent` currently does **not** use a relational database, ORM, or
migration system.

Current durable/stateful surfaces are:

- LangGraph store/checkpointer seams in `coding_deepgent.runtime.checkpointing`
- JSONL session transcripts in `coding_deepgent.sessions.store_jsonl`
- LangGraph store-backed memory/task/plan records in `memory/` and `tasks/`
- workspace-local persisted tool outputs under `.coding-deepgent/tool-results/`

Do not introduce SQL/ORM/migration infrastructure unless a Trellis PRD states
the concrete product benefit and target contract.

---

## Store Patterns

Preferred current patterns:

- Use LangGraph `InMemoryStore` / store-compatible APIs for product-domain
  records such as memory, durable tasks, and plan artifacts.
- Keep namespace ownership inside the owning domain.
- Store Pydantic `model_dump()` payloads for typed records.
- Validate records before writing and when reconstructing from storage.

Examples:

- `coding_deepgent.memory.store`
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

There are currently no database migrations.

If a future task introduces SQL or another schema-migrated persistence layer, it
must first define:

- target storage backend
- schema ownership
- migration command surface
- rollback strategy
- validation and error matrix
- tests proving old records are handled safely

---

## Common Mistakes

- Treating `sessions/` as generic durable storage for unrelated domains.
- Adding SQLite/SQLAlchemy just because a structure is durable.
- Hiding task/memory schema evolution in ad hoc dict writes.
- Reusing one store namespace for multiple domain concepts.
