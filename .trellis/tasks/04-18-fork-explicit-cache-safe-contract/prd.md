# Fork explicit cache-safe contract and entrypoint

## Goal

Add the first local fork package as a distinct capability rather than overloading
the normal subagent path. The feature should let the parent conversation spawn a
same-config sibling branch that preserves the rendered prompt and visible tool
surface contract while keeping future continuity/resume seams explicit.

## Requirements

* Add a separate `run_fork` tool instead of extending `run_subagent`.
* Fork must use the parent invocation's rendered system prompt and visible tool
  projection directly.
* Fork must append a thin fixed directive carrying only branch intent.
* Fork must return structured JSON including parent/child thread lineage and
  fork contract fingerprints.
* Fork must emit sidechain transcript entries into the parent session ledger
  with bounded fork continuity metadata.
* Fork must reject nested forks via an explicit recursion guard.

## Acceptance Criteria

* [x] Main tool surface exposes `run_fork`.
* [x] `run_fork` uses a distinct runtime entrypoint and thread suffix.
* [x] Fork payload inherits parent context and exact visible tools.
* [x] Fork output is parseable as structured JSON.
* [x] Parent session ledger records fork sidechain entries with bounded metadata.
* [x] Recursion guard blocks nested fork attempts.

## Technical Approach

* Extend `RuntimeContext` with rendered prompt and visible tool projection
  seams populated by bootstrap/runtime invocation construction.
* Add fork schemas and result envelopes under `subagents/schemas.py`.
* Add fork execution helpers under `subagents/tools.py`.
* Register `run_fork` in the main tool system and capability registry.
* Reuse the parent session ledger as the fork audit surface.

## Out of Scope

* isolated worktrees
* full fork resume
* background lifecycle
* coordinator / mailbox / multi-agent orchestration
