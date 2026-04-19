# R3: Background Run Service Hardening

## Goal

将 background subagent/fork runtime 从“线程闭包持有 live `ToolRuntime`”整理为更清晰的 background run service：持久 run record、可序列化 runtime snapshot、process-local worker handle 分离，为后续 mailbox delivery、stopped-worker resume、notification protocol 打底。

## Dependencies

* Depends on R1 runtime role and agent factory seam.
* Prefer after R2 split if R2 has already stabilized execution/resume modules.

## Requirements

* 明确区分 persistent background run record 与 process-local worker thread handle。
* 减少 background worker 对 live `ToolRuntime` 的长期闭包依赖。
* 保持现有 `run_subagent_background`、`subagent_status`、`subagent_send_input`、`subagent_stop` 行为不变。
* 不声称 mailbox/coordinator/team runtime semantics。

## Acceptance Targets

* [ ] Background worker execution can be reconstructed from a bounded runtime snapshot/factory seam.
* [ ] Store-backed run record remains source of truth for status/progress/pending inputs/latest result.
* [ ] Process-local worker handles are clearly non-durable.
* [ ] Existing background subagent/fork tests pass.

## Planned Features

* Introduce a `BackgroundRunContext` / `BackgroundRuntimeSnapshot` style contract if needed.
* Refactor `BackgroundSubagentManager` around record mutation + worker execution boundaries.
* Update tests for send-input, stop, status, background fork reuse.

## Detailed Implementation Plan

### Target Design

Background execution should have three explicit layers:

* Durable run record
  * Existing `BackgroundSubagentRun` remains the store-backed source of truth for status, pending inputs, latest result, usage counters, child thread id, and terminal notification status.
* Serializable runtime snapshot
  * A bounded record of execution facts needed to reconstruct invocation context for the worker.
  * Should include only safe, durable identifiers and configuration-derived values, not arbitrary live objects.
* Process-local worker handle
  * The thread object and in-memory active-run map are explicitly non-durable.
  * They may optimize active execution but must not be treated as source of truth.

### Required Code Changes

* Refactor `BackgroundSubagentManager` so record mutation and worker execution are separate responsibilities.
* Reduce long-lived closure dependence on live `ToolRuntime`.
* Ensure queued follow-up input still reuses the same background run id and child thread id.
* Preserve terminal notification evidence behavior.
* Preserve stop/cancel semantics at safe invoke boundaries.
* Preserve background fork first-run vs resume behavior.

### Runtime Snapshot Constraints

* The snapshot must not include raw prompt text beyond existing fork fingerprints/metadata contracts.
* The snapshot must not include full `ToolRuntime`, arbitrary state dicts, or model objects.
* The snapshot may reference store/session/workdir/thread ids through bounded fields.
* If complete ToolRuntime removal is too broad for this stage, split a smaller prerequisite task instead of adding a fake serializable wrapper.

### Focused Verification

* Background tests in `coding-deepgent/tests/subagents/test_subagents.py`:
  * background subagent start/status.
  * background fork start/status.
  * send_input reactivates finished run.
  * background fork send_input reuses same thread and continuity.
  * subagent_stop cancels running background run.
  * subagent_stop cancels running background fork.
* Session evidence tests if `_append_notification` or evidence metadata changes.
* `ruff check <touched background/schema/test files>`
* `mypy <touched background/schema/test files>` where practical.

### Checkpoint Requirements

At R3 checkpoint, record:

* Which runtime facts are durable and which remain process-local.
* Whether live `ToolRuntime` is still held by worker threads and why.
* Whether H13 mailbox can later route messages through the service boundary instead of `subagent_send_input` semantics.
* Whether any cross-process/daemon behavior was deferred.

## Planned Extensions

* H13 mailbox message delivery.
* Stopped-worker wake/resume through SendMessage.
* Coordinator task notification protocol.

## Definition of Done

* Focused background tests pass.
* Ruff/mypy pass for touched files.
* Checkpoint documents durability boundary.

## Out of Scope

* 不实现 mailbox / SendMessage。
* 不实现 cross-process worker execution.
* 不 introduce daemon/remote bridge.
* 不 add TeamCreate/TeamDelete or coordinator tools.
* 不 change public background tool schemas unless a blocking bug is discovered and documented.

## Technical Notes

* Parent: `.trellis/tasks/04-19-runtime-architecture-refactor-plan/prd.md`
* Key files likely touched:
  * `coding-deepgent/src/coding_deepgent/subagents/background.py`
  * `coding-deepgent/src/coding_deepgent/subagents/schemas.py`
  * `coding-deepgent/tests/subagents/test_subagents.py`

## Checkpoint: R3

State:
* verifying

Verdict:
* APPROVE

Implemented:
* Added `BackgroundRuntimeSnapshot` to durable background run records.
* Added process-local `BackgroundWorkerHandle` to make thread handles explicit non-durable runtime state.
* Background run records now carry bounded runtime facts such as parent thread id, workdir, entrypoint, agent name, session-context availability, and prompt/tool fingerprints when available.
* Background notification evidence includes the bounded runtime snapshot.

Verification:
* `pytest -q coding-deepgent/tests/subagents/test_subagents.py coding-deepgent/tests/tool_system/test_tool_system_registry.py coding-deepgent/tests/tool_system/test_tool_search.py`
* Result: `59 passed`

Architecture:
* primitive used: explicit Pydantic run snapshot plus process-local handle dataclass.
* why no heavier abstraction: R3 documents and separates durable/process-local facts without introducing cross-process execution or a daemon.

Boundary findings:
* Active background workers still receive live `ToolRuntime` for the current LangChain invoke. Full reconstruction without live runtime is deferred because it would require new execution ownership and is not needed before H13 planning.
* Store-backed `BackgroundSubagentRun` remains the source of truth.
* No mailbox, SendMessage, team, daemon, or remote bridge behavior was introduced.

Decision:
* continue

Reason:
* Durable/process-local background boundaries are now explicit enough for R4 to define H13/H14 readiness criteria.
