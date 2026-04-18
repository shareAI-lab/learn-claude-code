# coding-deepgent H01 Tool Module Alignment Plan

Status: draft
Scope: `coding-deepgent/` H01 Tool-first capability runtime
Created: 2026-04-17

## Purpose

This plan consolidates the H01 tool-module discussion into an implementation
roadmap. It translates cc-haha tool-system highlights into a LangChain/LangGraph
native `coding-deepgent` direction without copying cc-haha's TypeScript runtime
objects, React rendering surface, or streaming tool executor.

The goal is to make the local tool system strong enough to support later cc
highlights, especially:

* H11/H12 agent-as-tool and subagent execution
* H15/H16/H17 skills, MCP, and plugins
* H08/H09/H10 task, plan, and verifier tools
* H05/H06 context pressure and session continuity around tool results

## Source Anchors

cc-haha source and docs used for this plan:

* `/root/claude-code-haha/src/Tool.ts`
* `/root/claude-code-haha/src/tools.ts`
* `/root/claude-code-haha/src/constants/tools.ts`
* `/root/claude-code-haha/src/services/tools/toolExecution.ts`
* `/root/claude-code-haha/src/services/tools/toolOrchestration.ts`
* `/root/claude-code-haha/src/services/tools/StreamingToolExecutor.ts`
* `/root/claude-code-haha/src/tools/ToolSearchTool/ToolSearchTool.ts`
* `/root/claude-code-haha/src/tools/ToolSearchTool/prompt.ts`
* `/root/claude-code-haha/src/utils/toolResultStorage.ts`
* `/root/claude-code-haha/src/utils/groupToolUses.ts`
* `/root/claude-code-haha/docs/must-read/01-execution-engine.md`
* `/root/claude-code-haha/docs/modules/01-execution-engine-deep-dive.md`

Local source/spec anchors:

* `coding-deepgent/src/coding_deepgent/tool_system/capabilities.py`
* `coding-deepgent/src/coding_deepgent/tool_system/middleware.py`
* `coding-deepgent/src/coding_deepgent/tool_system/policy.py`
* `.trellis/spec/backend/tool-capability-contracts.md`
* `.trellis/spec/backend/tool-result-storage-contracts.md`
* `.trellis/spec/backend/langchain-native-guidelines.md`

## Current Decisions

### Adopt

* Adopt the five-factor tool protocol:
  * `name`
  * `schema`
  * `permission`
  * `execution`
  * `rendering_result`
* Use `ToolCapability` as the local carrier for cc harness metadata not encoded
  by LangChain tools.
* Keep defaults conservative:
  * not read-only unless proven
  * not concurrency-safe unless proven
  * not trusted unless validated
  * not large-output/microcompact eligible unless explicitly opted in
* Keep capability-driven middleware/projection instead of tool-name special
  cases.
* Keep LangChain `@tool`, `ToolRuntime`, middleware, `ToolMessage`, and
  `Command(update=...)` as the primary runtime expression.

### Defer

* Full `StreamingToolExecutor` parity.
* Partial `tool_use` execution while model output is still streaming.
* UI grouped rendering parity.
* Full ToolSearch/deferred schema loading implementation.
* Complex Bash/PowerShell safety parity.
* Classifier, sandbox, and interactive permission dialog.
* Bun dead-code elimination mechanics.
* Embedded search tool replacement.

## Near-Term Implementation Package

Recommended package name:

```text
H01 tool capability and execution contract hardening
```

This package should be planned and implemented as one high-cohesion batch after
the broader highlight planning is complete.

### Included Subplans

#### 1. Five-Factor Capability Audit

Expected effect:

* Every registered model-facing tool is explainable through
  `name/schema/permission/execution/rendering_result`.
* Future skills/MCP/plugins/subagents can register tools without bypassing the
  core capability protocol.

Local target:

* Audit all current `ToolCapability` entries.
* Add tests that capability name equals actual LangChain tool name.
* Add tests that every main/child/extension tool has capability metadata.
* Keep `.trellis/spec/backend/tool-capability-contracts.md` as the owning spec.

Do not:

* Recreate cc-haha's TS `Tool` interface.
* Add speculative fields that no local behavior consumes.

#### 2. Role-Based Tool Projection

Expected effect:

* Main agent, verifier child, general child, future coordinator, and extension
  surfaces can receive different tool sets through one projection mechanism.
* Recursive or privileged tools can be blocked from child contexts without
  ad hoc allowlists.

Local target:

* Define stable projection categories:
  * `main`
  * `child_only`
  * `extension`
  * future `deferred`
* Review and test:
  * main tool surface
  * verifier child allowlist
  * general child allowlist
  * extension declarable names
* Ensure projection consumes `ToolCapability` metadata.

Do not:

* Hard-code future coordinator/mailbox behavior before H13/H14 are reopened.

#### 3. Dynamic Tool Pool Foundation

Expected effect:

* The local runtime treats tool availability as a projected capability surface,
  not as a fixed global list.
* Later MCP/plugin/skill/subagent work can change visible tools without
  reworking agent wiring.

Local target:

* Keep the initial implementation as projection and validation, not runtime
  hot-swapping.
* Make tool source/trust/exposure visible through registry metadata.
* Document future ToolSearch/deferred schema as an explicit extension of this
  foundation.

Do not:

* Implement full ToolSearch in this package.
* Implement prompt-cache-aware schema layout here.

#### 4. Non-Streaming Concurrent Tool Partitioning

Expected effect:

* When multiple complete tool calls are available in one model response,
  concurrency-safe tools may run concurrently and unsafe tools run serially or
  exclusively.
* Results are emitted in original tool-call order.
* The orchestration layer consumes `ToolCapability.concurrency_safe` and
  mutation metadata, not hard-coded tool names.

Local target:

* First run a LangChain research spike:
  * confirm current `create_agent` / tool node behavior for parallel tool calls
  * confirm whether middleware order, `Command(update=...)`, and result order are
    controllable without custom execution
* If LangChain already satisfies the requirement, add tests/spec only.
* If not, design a thin adapter that preserves:
  * `ToolGuardMiddleware`
  * permissions
  * hooks
  * large-output persistence
  * runtime events/evidence

Do not:

* Implement streaming tool-use execution.
* Bypass LangChain tool runtime with a custom query loop.

#### 5. Tool Use / Tool Result Pairing Contract

Expected effect:

* Every tool result remains paired with the originating tool call.
* Compact, resume, runtime pressure, and future orchestration cannot orphan
  `tool_use` or `tool_result` messages.

Local target:

* Promote pairing as an H01 invariant in tests/spec.
* Reuse existing compact tool-pair preservation logic.
* Add focused tests for result ordering if a concurrency adapter is introduced.

Do not:

* Implement complete orphan/duplicate/fallback repair unless a concrete runtime
  failure appears.

#### 6. Protocol-Correct Tool Failures

Expected effect:

* Tool failure remains model-consumable and does not corrupt the runtime loop.
* Unknown tool, schema failure, permission denial, hook block, and tool exception
  produce a bounded, protocol-correct result.

Local target:

* Keep failure results as `ToolMessage` or documented `Command(update=...)`.
* Ensure failures can emit bounded runtime/session evidence where appropriate.
* Avoid raw traceback or unbounded tool output in model-visible results.

Do not:

* Implement interactive permission approval in this package.

#### 7. Tool Result / Context Pressure Continuity

Expected effect:

* Large tool results, preview paths, and microcompact eligibility remain driven
  by capability metadata.
* Future context pressure work can hide old tool output without losing important
  restoration paths.

Local target:

* Keep `persist_large_output`, `max_inline_result_chars`, and
  `microcompact_eligible` tied to `ToolCapability`.
* Preserve existing large-output persistence tests.
* Add review checks when new tools opt into persistence or microcompact.

Do not:

* Rework context compression in this H01 package.

## Deferred Backlog

### Deferred: Streaming Tool Execution

cc-haha's `StreamingToolExecutor` is a real runtime highlight, but it is too
large for the current implementation package.

Documented future constraints:

* Do not design the non-streaming orchestration adapter in a way that makes
  streaming impossible later.
* Future streaming work must preserve:
  * progress
  * cancellation
  * sibling failure handling
  * ordered result yielding
  * middleware and permission boundaries

Reopen only when:

* there is a concrete latency/product need
* LangChain cannot satisfy it through official runtime surfaces

### Deferred: Full ToolSearch / Deferred Schema Loading

ToolSearch is important for MCP/plugin-heavy futures, but not required before
tool protocol, role projection, and extension source/trust metadata are stable.

Reopen when:

* model-visible tool schemas become large enough to pressure prompts/cache
* MCP/plugin tool count materially increases
* dynamic tool discovery becomes a user-visible need

### Deferred: Full Shell Permission Parity

The current direction is simple safety plus extensible permission seams.

Reopen when:

* subagent or MCP execution substantially increases shell risk
* Bash tool usage becomes a primary product path
* explicit user requirement raises permission hardening priority

### Deferred: Renderer / Grouped Tool UI

Grouped rendering and React-specific render surfaces are UI concerns. The local
backend should keep result contracts bounded and renderer-friendly, but does not
need cc UI parity.

## Suggested Task Decomposition

When implementation begins, create one parent Trellis task and child tasks:

```text
Parent: H01 tool capability and execution contract hardening

Child 1: capability audit and projection tests
Child 2: role-based tool projection foundation
Child 3: LangChain parallel tool-call research spike
Child 4: non-streaming concurrency partition adapter, only if research requires it
Child 5: tool-use/result pairing and protocol-correct failure tests
Child 6: result persistence/microcompact eligibility review
```

Recommended order:

1. Child 1
2. Child 2
3. Child 3
4. Child 4 only if needed
5. Child 5
6. Child 6

## Verification Matrix

| Area | Required proof |
|---|---|
| capability protocol | every registered tool has correct five-factor metadata |
| safe defaults | unsafe/unknown/untrusted tools do not get read/concurrent/persist privileges |
| projection | main/child/verifier/extension tool surfaces are stable |
| concurrency | concurrent-safe tools can run without order corruption; unsafe tools remain exclusive |
| pairing | `tool_use` / `tool_result` relationship is preserved under projection/compact/orchestration |
| failures | unknown/schema/permission/hook/tool failures return bounded model-consumable results |
| result pressure | persistence and microcompact are metadata-driven and opt-in |

Focused test families:

* `coding-deepgent/tests/test_tool_system_registry.py`
* `coding-deepgent/tests/test_tool_system_middleware.py`
* `coding-deepgent/tests/test_tools.py`
* `coding-deepgent/tests/test_tasks.py`
* `coding-deepgent/tests/test_subagents.py`
* `coding-deepgent/tests/test_mcp.py`
* `coding-deepgent/tests/test_tool_result_storage.py`
* `coding-deepgent/tests/test_runtime_pressure.py`

## Discussion Status

This recommendation has already been consumed by the 2026-04-17 alignment
discussion.

Historical next module after H01:

```text
H15/H16/H17: Skill / MCP / Plugin extension platform
```

Why:

* It directly consumes the H01 tool capability protocol.
* It stress-tests source/trust/exposure metadata.
* It determines whether dynamic tool pool and deferred ToolSearch are real near
  term needs or only future options.
* It should be resolved before deeper H11/H12 subagent work, because subagents
  need a clear answer for which external capabilities they can see and trust.

Suggested discussion order:

1. H15/H16/H17 Skills, MCP, Plugin extension platform
2. H11/H12 Agent-as-tool and subagent context/fork model
3. H08/H09/H10 Todo, Task, Plan, Verify workflow
4. H03-H07/H20 Context, session, memory, compact, cost/cache revisit

Current execution handoff:

* H15/H16/H17 are resolved as baseline-only.
* H11/H12 requirements are resolved enough for the current implementation line.
* Do not create another H01 parent task.
* Use `.trellis/tasks/04-17-cc-core-topology-closeout-plan/` as the parent.
* H01 child 1, `04-17-l1c-h01-five-factor-capability-audit`, is complete.
* Next H01-specific entry point is `04-17-l2c-h01-role-based-tool-projection`, after the `L2-a` subagent dependency lands.

## Implementation Gate

Status: **cleared 2026-04-17**.

Previously blocked on:

* H15/H16/H17 confirm whether tool protocol needs additional fields → **resolved**: user decision is "baseline only", no additional fields required.
* H11/H12 confirm subagent tool-protocol needs → **resolved**: H11/H12 alignment research finalized sidechain + result envelope; tool protocol does not need additional fields beyond current `ToolCapability` five-factor set.
* LangChain parallel tool-call research scoped → **remaining**: child 3 (research spike) is now the entry point for that scoping.
* Implementation package has Trellis PRD, spec context, and focused test matrix → **resolved**: child task `04-17-l1c-h01-five-factor-capability-audit` is complete; downstream H01 work resumes at `L2-c` after `L2-a`.

Gate lifted. Do not create another parent task. The topology's next overall
entry point is `04-17-l2a-h11-h12-agent-definition-general-runtime`; the next
H01-specific entry point is `04-17-l2c-h01-role-based-tool-projection` after
`L2-a` lands.
