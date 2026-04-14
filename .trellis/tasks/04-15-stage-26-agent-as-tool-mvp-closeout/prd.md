# Stage 26: Agent As Tool MVP Closeout

## Goal

Close H11 and the minimal H12 MVP boundary by tightening the current agent-as-tool runtime contract without adding mailbox, coordinator, background worker execution, or full agent-team lifecycle.

## Function Summary

This stage should define and verify the MVP-bounded agent-as-tool behavior: subagents enter through `run_subagent`, verifier execution is a real bounded child-agent path, general subagent remains explicitly synchronous/minimal, and minimal fork/context semantics are documented or tested if needed.

## Expected Benefit

* Agent-runtime reliability: subagent behavior has a clear MVP boundary.
* Recoverability: verifier child execution remains traceable through evidence lineage.
* Maintainability: future H13/H14 agent-team features cannot leak into MVP unintentionally.

## Corresponding Highlights

* `H11 Agent as tool and runtime object`
* `H12 Fork/cache-aware subagent execution` minimal local slice only

## Corresponding Modules

* `coding_deepgent.subagents`
* `coding_deepgent.runtime`
* `coding_deepgent.tasks`
* `coding_deepgent.sessions`
* `coding_deepgent.tool_system`

## Out Of Scope

* mailbox / SendMessage
* coordinator runtime
* background worker execution
* general task-backed agent lifecycle
* provider-specific prompt-cache parity

## Acceptance Criteria

* [x] cc-haha source mapping for H11/minimal H12 is recorded in this stage PRD.
* [x] local H11/H12 MVP closeout slices are explicit.
* [x] focused tests, targeted ruff, and targeted mypy pass for changed files.
* [x] checkpoint records whether H11 becomes implemented and H12 remains minimal/deferred with an explicit boundary.

## cc-haha Alignment

### Expected Effect

Aligning this behavior should improve agent-runtime reliability and recoverability. The local runtime effect is: subagent execution remains a model-visible tool boundary, verifier child execution remains traceable, and minimal context/thread propagation is pinned without adding a full agent-team runtime.

### Source-backed alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Agent as tool | `AgentTool` is the runtime entrypoint for child agents | local subagents must enter through `run_subagent`, not prompt-only calls | strict `run_subagent` tool schema, allowlists, verifier child runtime | partial | Close MVP boundary now |
| Runtime object identity | upstream `LocalAgentTask` gives spawned agents durable identity | local verifier needs traceable child identity, but not full task-backed lifecycle | thread id, agent name, session evidence lineage | partial | Align minimal lineage now |
| Fork/cache-aware execution | upstream preserves parent prefix via cache-safe params and fork context messages | local MVP needs stable context/thread propagation only | `session_context` and runtime invocation threading tests | minimal | Defer provider-specific cache parity |
| Agent-team runtime | upstream supports background agents, notifications, SendMessage, teammate flows | valid future work but outside MVP | none | defer | Keep out of Stage 26 |

### Source files inspected

Explorer A inspected:

* `/root/claude-code-haha/src/tools/AgentTool/AgentTool.tsx`
* `/root/claude-code-haha/src/tools/AgentTool/forkSubagent.ts`
* `/root/claude-code-haha/src/tools/AgentTool/runAgent.ts`
* `/root/claude-code-haha/src/tasks/LocalAgentTask/LocalAgentTask.tsx`
* `/root/claude-code-haha/src/Task.ts`
* `/root/claude-code-haha/src/tasks.ts`
* `/root/claude-code-haha/src/utils/forkedAgent.ts`
* `/root/claude-code-haha/src/utils/queryContext.ts`
* `/root/claude-code-haha/src/context.ts`
* `/root/claude-code-haha/src/utils/systemPrompt.ts`
* `/root/claude-code-haha/src/query.ts`

## Technical Approach

* Close H11 by relying on existing verifier child-agent execution, fixed read-only allowlists, structured verifier result, and evidence lineage.
* Close minimal H12 by adding runtime/session-context propagation tests across direct runtime invocation and `agent_loop` invocation.
* Explicitly defer provider-specific fork/cache parity, background agents, mailbox, and coordinator runtime.

## Checkpoint: Stage 26

State:
- checkpoint

Verdict:
- APPROVE

Implemented:
- Added direct `build_runtime_invocation(session_context=...)` regression coverage.
- Added `agent_loop(..., session_context=...)` threading regression coverage.
- Confirmed existing subagent/verifier tests still cover allowlists, child thread id, structured verifier result, and evidence metadata.

Corresponding highlights:
- `H11 Agent as tool and runtime object`
- `H12 Fork/cache-aware subagent execution` minimal local slice

Corresponding modules:
- `coding_deepgent.subagents`
- `coding_deepgent.runtime`
- `coding_deepgent.app`
- `coding_deepgent.agent_loop_service`
- `coding_deepgent.sessions`

Tradeoff / complexity:
- Chosen: MVP-bounded agent-as-tool contract and minimal runtime/session-context propagation.
- Deferred: full `LocalAgentTask` lifecycle, background agents, mailbox/SendMessage, coordinator runtime, provider-specific cache-safe fork parity.
- Why this complexity is worth it now: H11/H12 were at risk of scope creep; this pins the useful local runtime boundary without dragging in agent-team runtime.

Verification:
- `pytest -q coding-deepgent/tests/test_subagents.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_tool_system_registry.py`
- `ruff check coding-deepgent/tests/test_app.py`
- `mypy coding-deepgent/src/coding_deepgent/runtime/invocation.py coding-deepgent/src/coding_deepgent/agent_loop_service.py coding-deepgent/src/coding_deepgent/app.py coding-deepgent/src/coding_deepgent/subagents/tools.py coding-deepgent/tests/test_app.py coding-deepgent/tests/test_subagents.py`

Boundary findings:
- H11 is complete for MVP as a bounded `run_subagent` tool surface with real verifier child execution.
- H12 is complete only as a minimal local context/thread propagation slice; rich fork/cache parity is explicitly deferred.

Decision:
- continue

Reason:
- Stage 26 is complete and Stage 27 (H15-H18 local extension platform closeout) remains the next milestone from the canonical dashboard.
