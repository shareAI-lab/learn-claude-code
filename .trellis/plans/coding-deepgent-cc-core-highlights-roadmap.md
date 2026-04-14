<!-- Created on 2026-04-14 during Trellis brainstorm for redefining coding-deepgent final goal. -->
# coding-deepgent CC Core Highlights Roadmap

Status: active canonical dashboard
Scope: `coding-deepgent/` product track only
Evidence policy: every highlight must be source-backed against `/root/claude-code-haha` before implementation

## Purpose

This document replaces a slow per-system approval loop with a source-backed highlight backlog.

The user does not want to review every low-level design item one by one. The working mode is:

1. Maintain a prioritized list of cc-haha core highlights.
2. For each highlight, inspect the relevant cc-haha source deeply before implementation.
3. State the concrete function and the concrete benefit before proposing or making code changes.
4. Translate the functional essence into LangChain/LangGraph-native architecture.
5. Defer or reject cc product details that do not create a concrete local effect.

## Global Target

`coding-deepgent` should become a professional LangChain-native implementation of Claude Code / cc-haha Agent Harness essence.

It should not become:

- a line-by-line cc-haha clone
- a UI/TUI clone
- a tutorial-only demo
- a custom runtime that bypasses LangChain/LangGraph

## Highlight Planning Rules

Every highlight must include:

- Function: what concrete capability or behavior changes for the user/runtime.
- Benefit: user-visible, agent-runtime, safety, reliability, context-efficiency, maintainability, testability, product parity, or observability.
- Source evidence: exact cc-haha files and symbols inspected.
- LangChain expression: official primitive first.
- Architecture shape: product-local modules and boundaries.
- Complexity judgment: why now, why later, or do not copy.
- Verification: local tests or review checks that prove behavior.
- Cross-session memory impact: direct, indirect, or none.

## Canonical MVP Boundary

Chosen finish-line scope: `Approach A: MVP Local Agent Harness Core`

Included in MVP:

* H01-H11
* H15-H19
* H12 minimal local slice only
* H20 minimal local slice only

Explicitly not in MVP:

* H13 Mailbox / SendMessage runtime
* H14 Coordinator runtime
* H21 Bridge / remote / IDE control plane
* H22 Daemon / cron / proactive automation

Stop rule:

* MVP is complete only when every H01-H22 row below has an explicit status.
* Every MVP-included row must be `implemented` or an explicitly accepted `partial`
  with tests/contracts backing the minimal boundary.
* Every non-MVP row must be `deferred` or `do-not-copy`.
* No new stage is valid unless it maps to an existing H row and states a concrete
  benefit.

Status vocabulary:

* `implemented`: sufficient for MVP unless a later audit finds a concrete gap
* `partial`: useful implementation exists, but a source-backed MVP closeout stage remains
* `missing`: should be in MVP, but not implemented enough yet
* `deferred`: valid future work, outside current MVP
* `do-not-copy`: not a local product goal or wrong abstraction

## Canonical Dashboard

This table is the canonical progress view for the MVP. Update this table when a
stage checkpoint materially changes a row.

| ID | Highlight | Current status | MVP boundary | Main modules | Next / remaining stage |
|---|---|---|---|---|---|
| H01 | Tool-first capability runtime | implemented | strict tool schemas, capability metadata, guarded execution for all model-facing capabilities | `tool_system`, domain `tools.py` | closed in Stage 21; keep only regression/audit follow-up |
| H02 | Permission runtime and hard safety | implemented | deterministic local policy, safe defaults, trusted dirs, explicit deny/ask behavior | `permissions`, `tool_system`, `filesystem`, `hooks` | closed in Stage 21; keep only regression/audit follow-up |
| H03 | Layered prompt contract | implemented | stable base prompt plus structured dynamic context; no giant tool manual | `prompting`, `runtime`, `memory`, `compact` | closed in Stage 22; keep only regression/audit follow-up |
| H04 | Dynamic context protocol | implemented | typed/bounded context payload assembly across recovery, memory, todo, and compact flows; skills/resources deferred | `runtime`, `sessions`, `memory`, `compact` | closed in Stage 22 with explicit MVP boundary |
| H05 | Progressive context pressure management | implemented | deterministic projection, compact records, latest valid compact selection, tool-result invariants | `compact`, `sessions`, `runtime` | closed in Stage 23; keep only regression/audit follow-up |
| H06 | Session transcript, evidence, and resume | implemented | JSONL session store, evidence, compacts, recovery brief, compacted resume continuity | `sessions`, `runtime`, `cli_service` | closed in Stage 23; evidence CLI remains optional enhancement |
| H07 | Scoped cross-session memory | implemented | controlled namespace-scoped save/recall with quality policy; no knowledge dumping | `memory`, `runtime`, `sessions` | closed in Stage 24; richer session/agent memory runtime deferred |
| H08 | TodoWrite short-term planning contract | implemented | strict TodoWrite state contract, separate from durable Task | `todo`, `runtime`, `prompting` | closed in Stage 25 |
| H09 | Durable Task graph | implemented | validated graph, readiness, plan artifacts, verification nudge | `tasks`, `tool_system` | closed in Stage 25 |
| H10 | Plan / Execute / Verify workflow discipline | implemented | explicit plan artifact, verifier child execution, persisted verifier evidence | `tasks`, `subagents`, `sessions` | closed in Stage 25; coordinator deferred |
| H11 | Agent as tool and runtime object | implemented | all subagents enter as tools; verifier has bounded child runtime and evidence lineage | `subagents`, `runtime`, `tasks`, `sessions` | closed in Stage 26; full agent-team lifecycle deferred |
| H12 | Fork/cache-aware subagent execution | implemented-minimal | smallest local context/thread propagation needed by H11 only | `subagents`, `runtime`, `compact` | minimal MVP slice closed in Stage 26; rich cache parity deferred |
| H13 | Mailbox / SendMessage | deferred | out of MVP | `tasks`, `subagents` | Stage 29 deferred-boundary ADR |
| H14 | Coordinator keeps synthesis | deferred | out of MVP | `tasks`, `subagents`, `prompting` | Stage 29 deferred-boundary ADR |
| H15 | Skill system packaging | implemented | local skill loader/tool and bounded context injection only | `skills`, `tool_system`, `prompting` | closed in Stage 27 |
| H16 | MCP external capability protocol | implemented | local MCP config/loading seam, tool/resource separation, capability policy | `mcp`, `plugins`, `tool_system` | closed in Stage 27 |
| H17 | Plugin states | implemented-minimal | local manifest/source validation only; install/enable lifecycle deferred | `plugins`, `skills`, `mcp` | local MVP closed in Stage 27; lifecycle deferred |
| H18 | Hooks as middleware | implemented | safe lifecycle hooks through middleware boundaries, not backdoors | `hooks`, `tool_system`, `runtime` | closed in Stage 27 |
| H19 | Observability and evidence ledger | implemented | structured local events plus session evidence and recovery visibility | `runtime`, `sessions`, `tool_system`, `subagents` | closed in Stage 28 |
| H20 | Cost/cache instrumentation | implemented-minimal | local budget/projection/compact counters only; provider-specific cost/cache deferred | `compact`, `runtime`, `sessions` | minimal MVP slice closed in Stage 28 |
| H21 | Bridge / remote / IDE control plane | deferred | out of MVP | future integration boundary | Stage 29 deferred-boundary ADR |
| H22 | Daemon / cron / proactive automation | deferred | out of MVP | future scheduling boundary | Stage 29 deferred-boundary ADR |

## Milestone Groups

### M1: Core Audit And Closeout

* Stage 21: H01/H02 tool + permission closeout
* Stage 22: H03/H04 prompt + dynamic context closeout
* Stage 23: H05/H06 context pressure + session continuity closeout
* Stage 24: H07 scoped memory closeout
* Stage 25: H08/H09/H10 todo/task/plan/verify closeout

Estimate: 5 narrow stages.

### M2: Agent / Evidence Minimal Runtime

* Stage 26: H11 closeout with minimal H12
* Stage 28: H19 closeout with minimal H20

Estimate: 2-4 narrow stages depending on discovered gaps.

### M3: Extension Platform Closeout

* Stage 27: H15/H16/H17/H18 local extension platform closeout

Estimate: 1-3 narrow stages depending on MCP/plugin audit findings.

### M4: Explicit Deferral / Release Boundary

* Stage 29: H13/H14/H21/H22 deferred-boundary ADR + MVP release checklist
* Stage 30-36: reserve only for MVP gaps discovered by prior checkpoints

Estimate: 1-3 documentation/spec stages plus reserve.

## Current Priority Order

### P0 Foundation Highlights

These affect most later systems and should be treated as baseline architecture.

| ID | Highlight | Benefit | cc-haha source to inspect deeply | LangChain-native expression | Initial decision |
|---|---|---|---|---|---|
| H01 | Tool-first capability runtime | safety, reliability, maintainability, product parity | `/root/claude-code-haha/src/Tool.ts`, `/root/claude-code-haha/src/services/tools/*`, `/root/claude-code-haha/src/tools/*Tool/*` | strict Pydantic `@tool`, `Command(update=...)`, `AgentMiddleware.wrap_tool_call`, capability metadata registry | Must align functionally; do not clone TS `Tool` shape |
| H02 | Permission runtime and hard safety | safety, testability, observability | `/root/claude-code-haha/src/types/permissions.ts`, `/root/claude-code-haha/src/utils/permissions/*`, `/root/claude-code-haha/src/hooks/toolPermission/*` | deterministic policy layer, `wrap_tool_call`, `ToolMessage(status="error")`, future HITL interrupts | Must align deterministically; defer auto classifier/UI |
| H03 | Layered prompt contract | reliability, cache-efficiency, maintainability | `/root/claude-code-haha/src/constants/prompts.ts`, `/root/claude-code-haha/src/utils/systemPrompt.ts`, `/root/claude-code-haha/src/utils/queryContext.ts`, `/root/claude-code-haha/src/context.ts` | small `PromptContext`, `system_prompt`, future `dynamic_prompt`, `context_schema` | Must align layered semantics; do not copy giant prompt |
| H04 | Dynamic context protocol | context-efficiency, reliability | `/root/claude-code-haha/src/utils/attachments.ts`, `/root/claude-code-haha/src/utils/messages.ts`, `/root/claude-code-haha/src/utils/queryContext.ts` | context/message assembly middleware, typed context payloads, bounded render helpers | Must align principle; local protocol can be smaller |
| H05 | Progressive context pressure management | context-efficiency, long-session continuity | `/root/claude-code-haha/src/query.ts`, `/root/claude-code-haha/src/services/compact/*`, `/root/claude-code-haha/src/utils/toolResultStorage.ts`, `/root/claude-code-haha/src/utils/messages.ts` | deterministic budget/projector helpers, later summarization middleware, state/message invariant tests | Must align staged pressure handling; avoid custom loop unless needed |

### P1 Runtime Continuity Highlights

These make the product useful for long professional work rather than one-shot demos.

| ID | Highlight | Benefit | cc-haha source to inspect deeply | LangChain-native expression | Initial decision |
|---|---|---|---|---|---|
| H06 | Session transcript, evidence, and resume | reliability, recoverability, testability | `/root/claude-code-haha/src/QueryEngine.ts`, `/root/claude-code-haha/src/utils/sessionStorage.ts`, `/root/claude-code-haha/src/tools/AgentTool/resumeAgent.ts`, `/root/claude-code-haha/src/services/compact/compact.ts` | LangGraph `thread_id`, checkpointer/store where appropriate, JSONL session store, recovery brief | Must align recovery intent; exact storage may differ |
| H07 | Scoped cross-session memory, not knowledge dumping | context-efficiency, reliability, maintainability, cross-session continuity | `/root/claude-code-haha/src/memdir/*`, `/root/claude-code-haha/src/services/SessionMemory/*`, `/root/claude-code-haha/src/tools/AgentTool/agentMemory*` | LangGraph store, explicit memory schemas, bounded recall, controlled save tool, side-agent later | Must align principles; cross-session memory is required, but rich auto extraction can still wait |

### P1 Workflow Highlights

These define how coding work is made explicit and verifiable.

| ID | Highlight | Benefit | cc-haha source to inspect deeply | LangChain-native expression | Initial decision |
|---|---|---|---|---|---|
| H08 | TodoWrite as short-term planning contract | reliability, product parity, model control | `/root/claude-code-haha/src/tools/TodoWriteTool/*`, `/root/claude-code-haha/src/utils/todo/*` | `TodoWrite` strict Pydantic schema, `Command(update=...)`, state middleware | Already mostly aligned; keep separate from durable Task |
| H09 | Durable Task graph as collaboration state | reliability, multi-agent readiness | `/root/claude-code-haha/src/tools/Task*Tool/*`, `/root/claude-code-haha/src/utils/tasks.ts`, `/root/claude-code-haha/src/tasks/*` | domain task store, strict transitions, tool API, later persistence/checkpointer integration | Partial now; deepen after Todo/session boundaries are stable |
| H10 | Plan / Execute / Verify workflow discipline | reliability, testability, product-grade behavior | `/root/claude-code-haha/src/tools/EnterPlanModeTool/*`, `/root/claude-code-haha/src/tools/ExitPlanModeTool/*`, `/root/claude-code-haha/src/coordinator/coordinatorMode.ts`, verification agent sources | mode-aware prompt/context, permission plan mode, future verification subagent/tool | Align as workflow protocol; defer UI-heavy approval |

### P2 Agent Team Highlights

These should be layered after tool/permission/session/task are reliable.

| ID | Highlight | Benefit | cc-haha source to inspect deeply | LangChain-native expression | Initial decision |
|---|---|---|---|---|---|
| H11 | Agent as tool and runtime object | agent-runtime, recoverability, product parity | `/root/claude-code-haha/src/tools/AgentTool/*`, `/root/claude-code-haha/src/tasks/LocalAgentTask/*`, `/root/claude-code-haha/src/services/AgentSummary/*` | subagent tool, state/context isolation, task-backed lifecycle, LangGraph subgraph/tool wrapper where useful | Align as runtime object; not just prompt wrapper |
| H12 | Fork/cache-aware subagent execution | context-efficiency, runtime performance | `/root/claude-code-haha/src/tools/AgentTool/forkSubagent.ts`, `/root/claude-code-haha/src/tools/AgentTool/runAgent.ts`, cache-safe context docs | context snapshot/fork semantics, avoid breaking LangChain runtime, defer provider-specific cache tuning | Defer deep parity until subagent lifecycle is richer |
| H13 | Mailbox / SendMessage multi-agent communication | multi-agent readiness, recoverability | `/root/claude-code-haha/src/tools/SendMessageTool/*`, `/root/claude-code-haha/src/tasks/LocalAgentTask/*`, `/root/claude-code-haha/src/coordinator/coordinatorMode.ts` | task-linked mailbox store, explicit message tool, no prompt-only fake conversation | Defer until durable tasks and subagent lifecycle mature |
| H14 | Coordinator keeps synthesis | reliability, quality, multi-agent correctness | `/root/claude-code-haha/src/coordinator/coordinatorMode.ts`, task workflow docs | product workflow planner, separate research/implementation/verification roles | Align principle; implement only when coordinator mode is a target |

### P2 Extension Platform Highlights

These turn the product from single app into extensible runtime.

| ID | Highlight | Benefit | cc-haha source to inspect deeply | LangChain-native expression | Initial decision |
|---|---|---|---|---|---|
| H15 | Skill system as capability packaging | maintainability, product parity | `/root/claude-code-haha/src/tools/SkillTool/*`, `/root/claude-code-haha/src/skills/*`, `/root/claude-code-haha/src/commands/skills/*` | local skill loader, `load_skill` tool, skill context injection, later forked skill execution | Partial now; keep simple and source-aware |
| H16 | MCP as external capability protocol | extensibility, safety | `/root/claude-code-haha/src/services/mcp/*`, `/root/claude-code-haha/src/tools/ListMcpResourcesTool/*`, `/root/claude-code-haha/src/tools/ReadMcpResourceTool/*` | official `langchain-mcp-adapters`, capabilities, separate resources, strict config | Already Stage 11; audit before expanding |
| H17 | Plugin states: source / install / enable | extensibility, maintainability | `/root/claude-code-haha/src/utils/plugins/*`, `/root/claude-code-haha/src/commands/plugin/*` | local manifest registry first; no marketplace until benefit exists | Defer broad marketplace/install parity |
| H18 | Hooks as programmable middleware, not backdoor | extensibility, safety | `/root/claude-code-haha/src/utils/hooks/*`, `/root/claude-code-haha/src/services/tools/toolHooks.ts`, `/root/claude-code-haha/src/types/hooks.ts` | LangChain middleware + local hook dispatcher | Partial now; expand only around concrete lifecycle events |

### P3 Production Hardening Highlights

These are important, but should follow the core runtime unless a specific need appears.

| ID | Highlight | Benefit | cc-haha source to inspect deeply | LangChain-native expression | Initial decision |
|---|---|---|---|---|---|
| H19 | Observability and evidence ledger | observability, testability | `/root/claude-code-haha/src/query.ts`, `/root/claude-code-haha/src/QueryEngine.ts`, telemetry/logging paths, existing local session evidence | structured local events, JSONL evidence, recovery brief | Partial now; improve alongside each feature |
| H20 | Cost/cache instrumentation | context-efficiency, maintainability | `/root/claude-code-haha/src/services/compact/*`, `/root/claude-code-haha/src/utils/tokens.ts`, cache-safe/fork docs | local metrics first; provider-specific cache later | Defer rich provider-specific work |
| H21 | Bridge / remote / IDE control plane | user-visible, remote collaboration | `/root/claude-code-haha/src/bridge/*`, `/root/claude-code-haha/src/services/mcp/*ide*` | not currently core to `coding-deepgent`; future integration boundary | Do not prioritize without explicit product goal |
| H22 | Daemon / cron / proactive automation | user-visible, automation | `/root/claude-code-haha/src/tools/ScheduleCronTool/*`, `/root/claude-code-haha/src/tasks/*`, trigger docs | LangGraph scheduling only if product need exists | Defer |

## How To Use This Backlog

For any future implementation request:

1. Identify the relevant highlight IDs.
2. Read the listed cc-haha source files, not just the docs.
3. Produce a function summary and expected-effect statement.
4. Produce a source-backed alignment matrix.
5. Apply `langchain-architecture-guard` to choose the smallest official LangChain/LangGraph shape.
6. Implement only the rows whose local benefit is concrete.
7. Update product docs/tests with evidence.

## Immediate Recommendation

Do not continue manually approving every system definition.

Recommended next planning step:

1. Audit current `coding-deepgent` implementation against H01-H10.
2. Mark each highlight as:
   - implemented
   - partial
   - missing
   - intentionally deferred
3. Use that audit to choose the next implementation stage.
