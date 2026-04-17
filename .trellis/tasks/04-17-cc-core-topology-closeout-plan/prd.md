# cc core topology closeout plan

## Goal

还原并固化 2026-04-17 cc-highlight alignment 讨论后拍板的拓扑执行计划，把散落在 H01、H11/H12、H19 research notes 中的待办拆成可执行 Trellis tasks。

## Restored Source

本计划来自与另一个 agent 的聊天记录，并以仓库中已有材料校验：

* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/prd.md`
* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h11-h12-alignment-research.md`
* `.trellis/tasks/04-16-cc-highlight-alignment-discussion/h19-observability-alignment-research.md`
* `.trellis/plans/coding-deepgent-h01-tool-module-alignment-plan.md`
* `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`

## Canonical Single-Line Status

Current source of truth:

* Parent task: this task.
* Done: H19 vertical closeout (`L1-b`, `L2-b`, `L3-b`) and H01 five-factor audit (`L1-c`).
* Next: `L2-a H11/H12 AgentDefinition + real read-only general runtime`.
* Then: `L2-c` / `L3-c` H01 role projection and dynamic tool pool.
* Then: `L3-a` sidechain transcript, `L4` H01 research/tests/audits, `L5-a` only if LangChain research proves an adapter is needed.
* Docs-only tail: `L5-b` deferred-boundary ADR refresh and `L5-c` dashboard refresh.

## Topology

### Layer 1

* `L1-a`: task ledger cleanup. Status: completed during restoration; old completed/planning tasks were archived with `--no-commit`.
* `L1-b`: H19-A queued-until-sink event sink + agent-scoped logger helper.
* `L1-c`: H01-#1 five-factor capability audit.

### Layer 2

* `L2-a`: H11/H12-A AgentDefinition schema, general+verifier catalog, real general child runtime, structured result envelope, fallback text scan. Depends on `L1-c`.
* `L2-b`: H19-B compact observability trio: B2 split, B3 canary, B4 orphan tombstoned. Depends on `L1-b`.
* `L2-c`: H01-#2 role-based tool projection foundation. Depends on `L1-c` and `L2-a`.

### Layer 3

* `L3-a`: H11/H12-B subagent sidechain transcript with `parent_message_id` and `subagent_thread_id`. Depends on `L2-a`.
* `L3-b`: H19-C structured `query_error`, per-turn `token_budget`, env-gated API dump. Depends on `L1-b` and `L2-b`.
* `L3-c`: H01-#3 dynamic tool pool foundation. Depends on `L2-c`.

### Layer 4

* `L4-a`: H01-#4 LangChain parallel tool-call research spike. Depends on `L2-c`.
* `L4-b`: H01-#5 tool_use/tool_result pairing and protocol-correct failure tests. Depends on `L2-c` and `L3-c`.
* `L4-c`: H01-#6 result persistence / microcompact eligibility review. Depends on `L3-c`.

### Layer 5

* `L5-a`: conditional non-streaming partition adapter, only if `L4-a` proves LangChain behavior is insufficient.
* `L5-b`: deferred boundary ADR refresh for H11/H12 + H13/H14/H21/H22 + H19 deferred items.
* `L5-c`: canonical dashboard refresh for H11/H12/H19 after closeout.

## Execution Rules

* H19 closeout is no longer on the critical path; `L1-b`, `L2-b`, and `L3-b` are complete.
* H01 five-factor audit is no longer on the critical path; `L1-c` is complete.
* Start next with `L2-a`; do not create another H01 or H11/H12 parent task.
* `L2-c` should wait for `L2-a` so role-based projection can validate against the real general child runtime.
* Keep H01 tool work LangChain-native: prefer strict Pydantic tool schemas, `ToolCapability`, middleware, and existing `create_agent` surfaces before adding custom orchestration.
* Keep H19 observability local and bounded: no external analytics backend, Perfetto, or streaming event system in this closeout.
* Keep H11/H12 bounded: read-only general subagent, `general=25` / `verifier=5`, no background agent lifecycle, no mailbox, no full fork/cache parity.

## Acceptance Criteria

* [x] Old completed/planning tasks from L1-a no longer remain active.
* [x] Parent Trellis task exists with child task links for remaining topology items.
* [x] Each child task has a PRD with dependencies and acceptance criteria.
* [x] H19 vertical closeout is represented as done, not as the next planning blocker.
* [x] `L1-c` is represented as done, not as the next planning blocker.
* [x] `L2-a` is documented as the only next implementation entry point.
* [ ] `L2-a` has been executed through normal Trellis task workflow.

## Checkpoint: H19 Closeout

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- `L1-b`: queued `RuntimeEventSink` with ordered drain semantics and agent-scoped logger helper.
- `L2-b`: AutoCompact attempted/succeeded events, `post_autocompact_turn` canary metrics, and bounded `orphan_tombstoned` projection repair.
- `L3-b`: structured `query_error` evidence, per-response `token_budget` event, and env-gated `CODING_DEEPGENT_DUMP_PROMPTS=1` model request dump.

Verification:
- Focused `coding-deepgent` tests for runtime pressure, sessions, CLI, app wiring, and new H19 event/projection/logger coverage passed.
- `ruff check` passed on modified Python files.
- `mypy` passed on modified source modules and new H19-focused tests.

Boundary:
- No external analytics backend, Perfetto, streaming/TTFT, provider cache/cost, or CLI dump flag was added.
- `L5-b` remains open for deferred-boundary ADR refresh; `L5-c` dashboard cleanup is complete.
- This checkpoint does not claim H11/H12 completion.

Decision:
- continue

## Checkpoint: H01 L1-c Capability Audit

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- `L1-c`: `ToolCapability` now carries explicit five-factor metadata, including `rendering_result`.
- Registry construction validates capability name/tool name match, schema presence, non-unknown metadata, exposure values, and large-output/microcompact opt-in consistency.
- Focused tests cover builtin capability metadata, safe opt-ins, MCP extension metadata, and invalid registry entries.

Verification:
- Focused H01 tests for registry, middleware, tools, tasks, subagents, MCP, tool-result storage, runtime pressure, app wiring, and permissions passed.
- `ruff check` passed on modified H01 Python files.
- `mypy` passed on modified H01 source/test files.

Boundary:
- No role-based projection behavior, dynamic tool pool, parallel tool orchestration, or streaming runtime was added.
- Downstream H01 `L2-c`, `L3-c`, and `L4-*` tasks remain open.

Decision:
- continue

## Checkpoint: H11/H12 L2-a Agent Definition Runtime

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- `L2-a`: added `AgentDefinition` catalog for `general` and `verifier`.
- Replaced the `general` stub with a real read-only child `create_agent` invocation.
- Routed verifier allowlist/max-turn settings through definitions while preserving plan-bound verifier behavior.
- Added structured subagent result envelopes with local input/output/total token estimates, duration, and tool-use count.
- Added fallback text extraction when the final child assistant message is tool-only.

Verification:
- Focused subagent/task/tool/app/runtime tests passed in the integrated bundle.
- `ruff check` passed on modified files.
- `mypy` passed on modified source/test files.

Boundary:
- Sidechain transcript persistence, background agents, mailbox, write-capable coder agents, and fork/cache parity remain out of scope.

Decision:
- continue

## Checkpoint: H01 L2-c Role-Based Projection

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- `L2-c`: centralized role projection helpers for `main`, `child`, `extension`, and reserved `deferred` surfaces.
- Added deferred projection as an explicit empty/future boundary without ToolSearch or runtime hot-swap.
- Routed general/verifier child tools through `AgentDefinition` plus child capability metadata.
- Added tests for deterministic main/child/extension/deferred projections and extension metadata preservation.

Verification:
- Focused registry/subagent checks passed.
- Included in the integrated focused validation bundle.
- `ruff check` and `mypy` passed on modified files.

Boundary:
- No dynamic tool pool hot-swap, deferred schema discovery, or parallel tool-call orchestration was added.

Decision:
- continue

## Checkpoint: H11/H12 L3-a Sidechain Transcript

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- `L3-a`: persisted bounded subagent sidechain transcript entries into the parent session JSONL ledger.
- Added `parent_message_id`, `parent_thread_id`, and `subagent_thread_id` linkage for child transcript entries.
- Loaded sidechain transcript through `LoadedSession.sidechain_messages` without exposing it to main resume/compact/collapse projections.

Verification:
- Focused sessions/subagent tests passed.
- Included in the integrated focused validation bundle.
- `ruff check` and `mypy` passed on modified files.

Boundary:
- No per-agent transcript directories, subagent resume, or background lifecycle were added.

Decision:
- continue

## Checkpoint: H01 L3-c Dynamic Tool Pool Foundation

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- `L3-c`: added explicit `ToolPoolProjection` seam and `registry.project(...)` API for `main`, `child`, `extension`, and reserved `deferred` surfaces.
- Preserved extension source/trust metadata through projection and kept startup/runtime simple.
- Added deterministic projection validation and tests for invalid projection states.

Verification:
- Focused registry/subagent/app/CLI/session tests passed.
- Included in the integrated focused validation bundle.
- `ruff check` and `mypy` passed on modified files.

Boundary:
- No hot-swap runtime, ToolSearch, or streaming tool execution was added.

Decision:
- continue

## Checkpoint: H01 L4-a Parallel Tool-Call Research

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- `L4-a`: completed a source-backed research spike on LangChain parallel tool-call behavior.
- Confirmed from official docs and local installed source that `ToolNode` already parallelizes non-streaming multi-tool execution and preserves original tool-call order.
- Recorded recommendation to keep `L5-a` conditional/spec-only unless `L4-b` / `L4-c` expose a concrete capability-aware partitioning failure.

Verification:
- Research note captured under the task directory.
- No product runtime code changes were introduced for this task.

Boundary:
- No partition adapter or streaming executor was added.

Decision:
- continue

## Checkpoint: H01 L4-b Pairing And Failure Tests

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- `L4-b`: added focused protocol-failure tests for unknown tool, permission denial, hook block, and tool exception behavior.
- Added minimal hardening so tool handler exceptions return bounded `ToolMessage(status="error")` with the original `tool_call_id`.
- Added pairing tests proving tool-use/tool-result matching remains id-based across dynamic/projection tool names.

Verification:
- Focused middleware/projection/compact/planning tests passed.
- `ruff check` and `mypy` passed on touched files.

Boundary:
- No custom execution engine, streaming repair, or runtime partition adapter was added.

Decision:
- continue

## Checkpoint: H01 L4-c Result Persistence Audit

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- `L4-c`: completed the result persistence / microcompact eligibility audit.
- Confirmed current opt-ins remain valid for `bash`, `read_file`, `glob`, and `grep`.
- Clarified the contract that microcompact eligibility is still valid when old
  output is recoverable through persisted-output paths even if replaying the
  original tool call is unsafe.

Verification:
- Focused tool-result-storage / registry / runtime-pressure tests passed.
- `ruff check` passed on touched files.
- `mypy` passed on touched source/test files; broader `test_runtime_pressure.py`
  mypy noise remains the pre-existing fake-ModelRequest issue outside this task.

Boundary:
- No capability metadata changes, new persistence backend, or provider-specific
  instrumentation were added.

Decision:
- continue

## Checkpoint: L5-b Deferred Boundary ADR Refresh

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- `L5-b`: added a refreshed deferred-boundary ADR at
  `.trellis/plans/coding-deepgent-deferred-boundary-refresh-adr.md`
- merged old Stage 29 deferrals with the concrete deferred boundaries established
  by H01/H11/H12/H19 closeout work
- updated `project-handoff.md` so resume context points at the current tail and
  no longer suggests already-completed implementation tasks

Verification:
- ADR links back to the old Stage 29 deferred note and current source-backed
  research notes
- touched JSON/task metadata remains valid

Boundary:
- no deferred runtime feature was implemented

Decision:
- continue

## Checkpoint: L5-c Dashboard Refresh

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- `L5-c`: refreshed the canonical roadmap/dashboard rows for H01, H11, H12, and H19
- aligned roadmap wording with the now-completed H01/H11/H12/H19 topology work
- moved deferred/full-lifecycle wording to the refreshed deferred-boundary ADR so the dashboard reads as implemented vs deferred, not accidentally missing

Verification:
- touched task JSON remains valid
- roadmap and handoff now point to the current post-closeout tail correctly

Boundary:
- no product/runtime code changed

Decision:
- terminal

## Out of Scope

* Implementing product code in this parent planning task.
* Reopening H13/H14/H21/H22 implementation.
* Treating historical Stage 30A/30B as canonical current baseline.
