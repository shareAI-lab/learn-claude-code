<!-- Created on 2026-04-14 during Trellis brainstorm for redefining coding-deepgent final goal. -->
# coding-deepgent CC Core Highlights Roadmap

Status: planning backlog
Scope: `coding-deepgent/` product track only
Evidence policy: every highlight must be source-backed against `/root/claude-code-haha` before implementation

## Purpose

This document replaces a slow per-system approval loop with a source-backed highlight backlog.

The user does not want to review every low-level design item one by one. The working mode is:

1. Maintain a prioritized list of cc-haha core highlights.
2. For each highlight, inspect the relevant cc-haha source deeply before implementation.
3. State the concrete benefit before proposing or making code changes.
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

- Benefit: user-visible, agent-runtime, safety, reliability, context-efficiency, maintainability, testability, product parity, or observability.
- Source evidence: exact cc-haha files and symbols inspected.
- LangChain expression: official primitive first.
- Architecture shape: product-local modules and boundaries.
- Complexity judgment: why now, why later, or do not copy.
- Verification: local tests or review checks that prove behavior.

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
| H07 | Scoped memory, not knowledge dumping | context-efficiency, reliability, maintainability | `/root/claude-code-haha/src/memdir/*`, `/root/claude-code-haha/src/services/SessionMemory/*`, `/root/claude-code-haha/src/tools/AgentTool/agentMemory*` | LangGraph store, explicit memory schemas, bounded recall, controlled save tool, side-agent later | Must align principles; defer rich auto extraction until foundation is strong |

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
3. Produce an expected-effect statement.
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
