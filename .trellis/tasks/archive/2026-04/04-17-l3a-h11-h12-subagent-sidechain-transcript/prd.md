# L3-a: H11/H12 subagent sidechain transcript

## Goal

Implement H11/H12-B: persist subagent sidechain transcript entries into the parent session JSONL with parent/child linkage.

## Requirements

* Add `parent_message_id` and `subagent_thread_id` linkage for child transcript entries.
* Write sidechain child messages into the parent session ledger rather than a separate per-agent directory.
* Preserve raw transcript compatibility and existing resume behavior.
* Ensure verifier/general child evidence can be traced back to parent invocation context.

## Acceptance Criteria

* [x] Child transcript entries roundtrip through `JsonlSessionStore`.
* [x] Loaded sessions can distinguish parent messages from subagent sidechain messages.
* [x] Existing compact/collapse/session projections do not accidentally expose sidechain records to the main model context.
* [x] Verifier evidence lineage remains compatible.

## Dependencies

* Depends on `L2-a`.

## Context Sources

* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md`
* `.trellis/spec/backend/session-compact-contracts.md`
* `.trellis/spec/backend/task-workflow-contracts.md`

## Out of Scope

* Per-agent directories.
* Subagent resume.
* Background/async lifecycle.
