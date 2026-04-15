<!-- Created on 2026-04-14 from source reading, before implementation work. -->
# coding-deepgent H01-H10 Target Design

Status: source-backed target design draft
Scope: `coding-deepgent/` product track only
Source anchor: `/root/claude-code-haha` at commit `d166eb8`
Planning input: `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`

## Purpose

This document answers the user's request to read source and design now, before opening implementation work.

It converts the first ten cc core highlights into target goals for `coding-deepgent`.

This is not an implementation plan yet. It is the design target that later implementation tasks should align against.

## Operating Constraints

- Use cc-haha source as primary behavior evidence.
- Use `claude-code-book` and `cc-haha/docs` only as orientation and architecture analysis.
- Keep LangChain/LangGraph as the runtime boundary.
- Prefer official LangChain primitives:
  - `create_agent`
  - strict Pydantic `@tool(..., args_schema=...)`
  - `Command(update=...)`
  - `AgentMiddleware`
  - `ToolRuntime`
  - state/context schema
  - store/checkpointer
  - dynamic prompt/context middleware where appropriate
- Do not copy cc-haha TypeScript architecture line-by-line.
- Each upgrade must state benefit before work starts.

## H01 — Tool-First Capability Runtime

### Source evidence

- `/root/claude-code-haha/src/Tool.ts`
- `/root/claude-code-haha/src/services/tools/toolExecution.ts`
- `/root/claude-code-haha/src/services/tools/toolOrchestration.ts`
- `/root/claude-code-haha/src/services/tools/StreamingToolExecutor.ts`
- `/root/claude-code-haha/docs/must-read/01-execution-engine.md`
- `/root/claude-code-haha/docs/modules/01-execution-engine-deep-dive.md`

### Current local state

Implemented / partial:

- `coding_deepgent.tool_system.capabilities.ToolCapability`
- `coding_deepgent.tool_system.capabilities.CapabilityRegistry`
- `coding_deepgent.tool_system.policy.ToolPolicy`
- `coding_deepgent.tool_system.middleware.ToolGuardMiddleware`
- domain-owned LangChain tools exist in `filesystem`, `todo`, `memory`, `skills`, `tasks`, and `subagents`

### Target design

The tool system should be the model-facing action contract. Every executable capability exposed to the model enters through LangChain tools and the `ToolGuardMiddleware` path.

Do:

- Keep `CapabilityRegistry` as metadata complement to LangChain tools, not as a replacement tool framework.
- Extend capability metadata only when it supports policy, observability, tool-pool filtering, or extension trust.
- Require strict Pydantic schemas for all model-visible tools.
- Route stateful tool updates through `Command(update=...)`.
- Make runtime-only fields hidden via official LangChain runtime injection where possible.

Do not:

- Create a Python clone of cc-haha's TypeScript `Tool` interface.
- Put UI rendering hooks in the core tool contract.
- Add alias/fallback parsing to tolerate wrong model inputs.
- Build a custom executor before proving LangChain middleware is insufficient.

### Benefit

- Safety: prevents model-facing capabilities from bypassing guardrails.
- Maintainability: all capabilities share one contract.
- Testability: schemas, state updates, and policy decisions are separately testable.
- Product parity: aligns with cc-haha's tool-first runtime without copying provider-specific shape.

### Status

Partial. The local design direction is correct; future work should deepen metadata, dynamic tool-pool policy, and result/evidence invariants.

## H02 — Permission Runtime and Hard Safety

### Source evidence

- `/root/claude-code-haha/src/types/permissions.ts`
- `/root/claude-code-haha/src/utils/permissions/permissions.ts`
- `/root/claude-code-haha/src/utils/permissions/filesystem.ts`
- `/root/claude-code-haha/src/utils/permissions/pathValidation.ts`
- `/root/claude-code-haha/src/utils/permissions/permissionSetup.ts`
- `/root/claude-code-haha/src/utils/permissions/yoloClassifier.ts`
- `/root/claude-code-haha/docs/must-read/05-permission-security.md`
- `/root/claude-code-haha/docs/modules/05-permission-security-deep-dive.md`

### Current local state

Implemented / partial:

- `PermissionManager` supports mode, rules, hard command/path safety, trusted workdirs, extension trust, and `dontAsk` conversion.
- `PermissionRule` supports behavior, tool name, content, domain, capability source, trusted, source.
- `ToolGuardMiddleware` integrates permission policy with LangChain `wrap_tool_call`, emits events, and dispatches hooks.

### Target design

Permission is a runtime layer, not a per-tool helper.

Do:

- Keep deterministic guard behavior as the current foundation.
- Preserve hard safety before normal mode/allow decisions.
- Treat extension/untrusted destructive capabilities conservatively.
- Keep all decisions structured with code, behavior, message, and metadata.
- Model plan mode as read/research mode, not as a prompt-only convention.
- Return protocol-safe `ToolMessage(status="error")` when approval is unavailable or denied.
- Add LangGraph HITL interrupts only when interactive approval is a concrete target.

Do not:

- Implement auto classifier before deterministic policy has enough surface and tests.
- Copy cc-haha React permission UI.
- Allow bypass mode to skip hard safety.
- Let hooks override hard safety.

### Benefit

- Safety: prevents unsafe tool execution in filesystem/MCP/plugin/subagent paths.
- Reliability: headless/background contexts do not hang on impossible approvals.
- Observability: decisions can be logged, tested, and explained.
- Product parity: aligns with cc-haha's permission runtime framing.

### Status

Partial but strong. Immediate work should harden tests, metadata, and decision observability before adding classifier/HITL.

## H03 — Layered Prompt Contract

### Source evidence

- `/root/claude-code-haha/src/utils/queryContext.ts`
- `/root/claude-code-haha/src/context.ts`
- `/root/claude-code-haha/docs/must-read/03-prompt-context-memory.md`
- `/root/claude-code-haha/docs/modules/03-prompt-context-memory-deep-dive.md`

### Current local state

Implemented / partial:

- `PromptContext` separates default prompt, user context, system context, append prompt, and memory context.
- `build_default_system_prompt()` encodes product identity and LangChain-native behavior.
- Tests assert stale tool wording is not in the prompt.

### Target design

The prompt system defines stable model operating contract.

Do:

- Keep the base prompt short, stable, and product-specific.
- Keep custom prompt and append prompt separate.
- Keep user/system context structured even if not all fields are model-visible yet.
- Add role/mode overlays only when the runtime mode exists.
- Use LangChain `dynamic_prompt` middleware only when prompt truly depends on runtime state/context.

Do not:

- Copy cc-haha's full prompt text.
- Put dynamic task/memory/tool state in the base prompt.
- Put tool manuals in the system prompt.
- Add provider-specific cache blocks without measured benefit.

### Benefit

- Reliability: stable instructions reduce prompt drift.
- Cache efficiency: volatile state stays out of base prompt.
- Maintainability: prompts become testable contracts.

### Status

Partial. Current builder is intentionally small; target is to preserve structure and add overlays only when needed.

## H04 — Dynamic Context Protocol

### Source evidence

- `/root/claude-code-haha/src/utils/attachments.ts`
- `/root/claude-code-haha/src/utils/messages.ts`
- `/root/claude-code-haha/src/context.ts`
- `/root/claude-code-haha/src/utils/queryContext.ts`
- `/root/claude-code-haha/docs/must-read/03-prompt-context-memory.md`

### Current local state

Implemented / partial:

- `MemoryContextMiddleware` injects rendered memories into `SystemMessage` content blocks.
- `PlanContextMiddleware` injects current todos and reminders into `SystemMessage` content blocks.
- `RuntimeContext` carries session/workdir/trusted_workdirs/entrypoint/agent_name/skill_dir/event_sink/hook_registry.

Missing:

- No general typed context attachment/delta protocol.
- No explicit context lifecycle taxonomy.
- No context projection/message assembly layer.

### Target design

Context decides what dynamic information enters the model window, where it enters, and how long it should remain.

Do:

- Introduce a small typed context payload model before adding many ad hoc system blocks.
- Keep dynamic state separate from prompt base.
- Treat todos, memories, task status, skill availability, and future subagent/mailbox state as context payloads with bounded renderers.
- Make context injection fail-soft.
- Add tests that context payload rendering remains bounded and non-duplicative.

Do not:

- Build full cc-haha attachment protocol before local needs exist.
- Turn every runtime event into model context.
- Let memory/task/session systems write arbitrary system prompt text directly.

### Benefit

- Context-efficiency: only relevant dynamic data enters the window.
- Maintainability: new dynamic context has one shape rather than ad hoc prompt fragments.
- Reliability: dynamic context is testable and bounded.

### Status

Partial. Current middleware proves the pattern but needs a small shared protocol before more context types are added.

## H05 — Progressive Context Pressure Management

### Source evidence

- `/root/claude-code-haha/src/query.ts`
- `/root/claude-code-haha/src/services/compact/microCompact.ts`
- `/root/claude-code-haha/src/services/compact/autoCompact.ts`
- `/root/claude-code-haha/src/services/compact/compact.ts`
- `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
- `/root/claude-code-haha/src/utils/toolResultStorage.ts`
- `/root/claude-code-haha/src/utils/messages.ts`
- `/root/claude-code-haha/docs/must-read/01-execution-engine.md`
- `/root/claude-code-haha/docs/must-read/03-prompt-context-memory.md`

### Current local state

Implemented / partial:

- `compact.budget.apply_tool_result_budget()` truncates oversized text deterministically.

Missing:

- No message projection layer.
- No compact boundary state.
- No micro/auto/reactive compact.
- No tool-result persistence or restore reference.
- No invariant tests for tool-call/result pairing across projection/compaction.

### Target design

Context pressure management should be progressive and invariant-preserving.

Do:

- Start with deterministic tool-result budget and message projection invariants.
- Add a context pressure status model before adding summarization.
- Preserve tool call/result and state update semantics.
- Treat compaction as runtime correctness, not just cost optimization.
- Add tests for projected/compacted history invariants.

Do not:

- Implement LLM summarization first.
- Replace LangChain's message/runtime model with a custom query loop.
- Copy every cc-haha compaction strategy without local pressure evidence.

### Benefit

- Long-session continuity: large outputs do not kill the run.
- Reliability: projection/compaction does not corrupt protocol state.
- Testability: deterministic budget/projection can be proven before LLM summarization.

### Status

Early partial. Current budget helper is useful but not enough for cc-level context management.

## H06 — Session Transcript, Evidence, and Resume

### Source evidence

- `/root/claude-code-haha/src/QueryEngine.ts`
- `/root/claude-code-haha/src/tools/AgentTool/resumeAgent.ts`
- `/root/claude-code-haha/src/services/compact/compact.ts`
- `/root/claude-code-haha/docs/must-read/02-agent-runtime.md`
- `/root/claude-code-haha/docs/must-read/01-execution-engine.md`

### Current local state

Implemented / partial:

- `JsonlSessionStore`
- `SessionContext`
- `SessionSummary`
- `SessionEvidence`
- `LoadedSession`
- message records
- state snapshot records
- evidence records
- resume state loading
- `sessions.langgraph` helper exists

### Target design

Session should be recoverable execution evidence, not just chat history.

Do:

- Keep JSONL transcript as local evidence layer.
- Preserve latest valid runtime state snapshot.
- Keep evidence separate from UI.
- Map session id to LangGraph `thread_id`.
- Add recovery brief target for continuation.
- Keep transcript store independent from memory/task stores.

Do not:

- Pretend resume is full cc agent runtime recovery yet.
- Store unrelated memory/task state in session transcript directly.
- Add database persistence until local JSONL limits are concrete.

### Benefit

- Recoverability: resume has messages, state, and evidence.
- Testability: transcript/evidence records can be loaded deterministically.
- Product parity: aligns with cc-haha's transcript/metadata/resume premise.

### Status

Partial and strong. Next target is audit: confirm runtime invocation actually uses loaded state/evidence where expected.

## H07 — Scoped Memory, Not Knowledge Dumping

### Source evidence

- `/root/claude-code-haha/src/memdir/*`
- `/root/claude-code-haha/src/services/SessionMemory/*`
- `/root/claude-code-haha/src/tools/AgentTool/agentMemory.ts`
- `/root/claude-code-haha/src/tools/AgentTool/agentMemorySnapshot.ts`
- `/root/claude-code-haha/docs/must-read/03-prompt-context-memory.md`
- `/tmp/claude-code-book/第二部分-核心系统篇/06-记忆系统-Agent的长期记忆.md`

### Current local state

Implemented / partial:

- `MemoryRecord`
- `SaveMemoryInput`
- namespace: project/user/local
- store-backed save/list/recall
- `save_memory` tool
- `MemoryContextMiddleware`

Missing:

- No explicit "do not save derivable facts" enforcement beyond tool description.
- No memory freshness or richer relevance.
- No side-agent memory writing.
- No session memory compact integration.

### Target design

Memory stores durable, reusable, non-derivable knowledge and preferences.

Do:

- Keep namespaces explicit.
- Add validation/review around memory quality before auto-extraction.
- Keep memory separate from todo/task/session state.
- Use LangGraph store seam.
- Keep recall bounded and explainable.

Do not:

- Store code structure that can be re-read.
- Store current todo/task status as memory.
- Add embeddings/vector recall before deterministic recall quality is known.
- Add auto-extraction before save/recall semantics are reliable.

### Benefit

- Context-efficiency: durable facts survive without flooding prompts.
- Reliability: avoids memory pollution.
- Maintainability: memory/task/session boundaries stay separate.

### Status

Partial foundation. Next target is memory quality policy and tests.

## H08 — TodoWrite as Short-Term Planning Contract

### Source evidence

- `/root/claude-code-haha/src/tools/TodoWriteTool/TodoWriteTool.ts`
- `/root/claude-code-haha/src/tools/TodoWriteTool/prompt.ts`
- `/root/claude-code-haha/src/tools/TodoWriteTool/constants.ts`
- `/root/claude-code-haha/docs/must-read/04-task-workflow.md`

### Current local state

Implemented:

- public tool name `TodoWrite`
- strict Pydantic schema with `todos`
- required `content`, `status`, `activeForm`
- injected `tool_call_id`
- max 12 todos
- exactly one `in_progress`
- `Command(update=...)` state update
- `PlanContextMiddleware` current todo rendering, stale reminders, and parallel-call rejection

### Target design

TodoWrite is short-term session planning state, not durable task graph.

Do:

- Preserve the public contract.
- Keep todo state in LangGraph short-term state.
- Keep activeForm required.
- Keep parallel TodoWrite rejection.
- Keep stale reminder bounded.

Do not:

- Merge TodoWrite with durable Task.
- Add persistence to TodoWrite by default.
- Add aliases for status/content fields.

### Benefit

- Reliability: model has visible progress discipline for multi-step work.
- Product parity: cc-aligned model-visible contract.
- Testability: state update shape is easy to prove.

### Status

Implemented / strong. Future work should preserve rather than refactor heavily.

## H09 — Durable Task Graph as Collaboration State

### Source evidence

- `/root/claude-code-haha/src/tools/TaskCreateTool/*`
- `/root/claude-code-haha/src/tools/TaskGetTool/*`
- `/root/claude-code-haha/src/tools/TaskListTool/*`
- `/root/claude-code-haha/src/tools/TaskUpdateTool/*`
- `/root/claude-code-haha/src/utils/tasks.ts`
- `/root/claude-code-haha/src/tasks/*`
- `/root/claude-code-haha/docs/must-read/04-task-workflow.md`

### Current local state

Implemented / partial:

- `TaskRecord`
- statuses: pending/in_progress/blocked/completed/cancelled
- transition validation
- dependencies
- owner
- metadata
- store-backed task namespace
- tools: `task_create`, `task_get`, `task_list`, `task_update`

Missing:

- No claim/lock/high-water-mark semantics.
- No task runtime object family.
- No mailbox/agent lifecycle linkage.
- No task-level evidence store.

### Target design

Durable Task is collaboration/runtime state, not TodoWrite replacement.

Do:

- Keep store-backed strict task records.
- Add readiness/dependency semantics before team runtime.
- Add task-level evidence and ownership only when agent lifecycle needs it.
- Keep task tools model-visible but clearly distinct from TodoWrite.

Do not:

- Add filesystem lock/claim mechanics unless multiple concurrent workers actually share the task store.
- Add UI task objects before background agents/mailbox exist.
- Collapse task graph into session memory.

### Benefit

- Multi-agent readiness: explicit work ownership and dependency graph.
- Reliability: durable state survives beyond one message window.
- Maintainability: separates current plan from durable work graph.

### Status

Partial. Good schema/store foundation; defer runtime task object complexity.

## H10 — Plan / Execute / Verify Workflow Discipline

### Source evidence

- `/root/claude-code-haha/src/tools/EnterPlanModeTool/*`
- `/root/claude-code-haha/src/tools/ExitPlanModeTool/*`
- `/root/claude-code-haha/src/coordinator/coordinatorMode.ts`
- `/root/claude-code-haha/src/tools/AgentTool/built-in/verificationAgent.ts`
- `/root/claude-code-haha/docs/must-read/04-task-workflow.md`
- `/tmp/claude-code-book/第四部分-工程实践篇/14-Plan模式与结构化工作流.md`

### Current local state

Implemented / partial:

- permission mode includes `plan`
- prompt/todo workflow exists
- subagent type includes `verifier`
- no explicit EnterPlan/ExitPlan tools
- no persistent plan file/recovery
- no independent verification workflow

### Target design

Plan / Execute / Verify is a product workflow protocol that prevents complex coding work from drifting.

Do:

- Preserve plan mode as permission/read-only mode, not only a prompt hint.
- Add explicit plan artifact only when implementation work needs approval/recovery.
- Treat verification as an independent role/tool/subagent when product runtime can support it.
- Keep coordinator synthesis principle: research and implementation can be delegated, synthesis must be owned.

Do not:

- Add full plan-mode UI now.
- Add coordinator/team runtime before subagent/task/session foundations mature.
- Require plan mode for trivial tasks.

### Benefit

- Reliability: prevents premature action.
- Testability: plan artifacts can be verified against implementation.
- Product-grade behavior: separates research, synthesis, implementation, and verification.

### Status

Partial concept only. Needs a planned product stage after core context/session/subagent foundations are stronger.

## Summary Status

| Highlight | Current status | Near-term target |
|---|---|---|
| H01 Tool-first runtime | Partial | deepen metadata, dynamic tool policy, invariants |
| H02 Permission runtime | Partial/strong | harden deterministic policy and tests |
| H03 Prompt contract | Partial | preserve builder, clarify overlays, test prompt drift |
| H04 Dynamic context | Partial/weak | introduce typed context payload protocol |
| H05 Context pressure | Early partial | add projection/invariant design before summarization |
| H06 Session/resume | Partial/strong | audit runtime use of state/evidence |
| H07 Memory | Partial | add memory quality policy and bounded recall tests |
| H08 TodoWrite | Implemented/strong | preserve contract |
| H09 Durable Task | Partial | keep schema/store; defer runtime task complexity |
| H10 Plan/Verify | Concept partial | design after H04-H07/H11 mature |

## Recommended Next Stage

The next implementation stage should not jump to advanced multi-agent/team features.

Recommended next target:

**Stage 12: Context and Recovery Hardening**

Rationale:

- H01/H02/H03 are already directionally strong.
- H04/H05 are weaker and will affect memory, task, and subagent correctness.
- H06/H07 have foundations but need integration semantics.
- H08 is already strong.
- H09/H10/H11+ should wait until context/recovery boundaries are more explicit.

Candidate Stage 12 scope:

1. Introduce typed dynamic context payload protocol.
2. Add deterministic message/context projection helpers with tool-result invariants.
3. Audit session resume path and recovery brief use.
4. Add memory quality rules and bounded recall tests.
5. Update docs/status to reflect the new target.

Out of scope for Stage 12:

- full auto-compact LLM summarization
- coordinator/team runtime
- mailbox/send-message
- plugin marketplace
- permission classifier / rich approval UI

## Stage 12 Iteration Plan

Stage 12 should be implemented in sub-stages, not as one large infrastructure push.

Rationale:

- H04/H05/H06/H07 are coupled, but each has different verification needs.
- A single large infrastructure pass would encourage speculative abstractions.
- Smaller stages make the benefit of each infrastructure layer measurable.

### Stage 12A — Context Payload Foundation

Goal:

Define a typed, bounded, testable payload protocol for dynamic context injection.

Expected benefit:

- Maintainability: future memory/todo/task/session/subagent context does not become ad hoc system prompt text.
- Context-efficiency: context renderers can enforce bounded output.
- Reliability: context payload injection can fail soft and be tested.

Scope:

- typed context payload model
- bounded render helper(s)
- integration target for existing todo/memory dynamic context middleware
- tests proving payload rendering is bounded and non-duplicative

Out of scope:

- message projection
- auto compact
- session resume changes
- memory quality policy

### Stage 12B — Message Projection / Tool Result Invariants

Goal:

Add deterministic context pressure primitives before LLM-based compaction.

Expected benefit:

- Reliability: tool-use/tool-result and state update protocol invariants survive projection.
- Context-efficiency: oversized tool outputs are handled consistently.
- Testability: deterministic projection can be proven without live model calls.

Scope:

- message/context projection helpers
- integration with existing tool-result budget helper
- invariant tests for tool-result preservation and recent-window behavior

Out of scope:

- LLM summarization
- full cc-haha microcompact/autocompact parity

### Stage 12C — Recovery Brief / Session Resume Audit

Goal:

Confirm and harden the current session transcript/state/evidence path as a recovery foundation.

Expected benefit:

- Recoverability: resume gives enough execution context to continue work.
- Testability: session load behavior is deterministic.
- Product parity: aligns with cc-haha's transcript + metadata recovery premise.

Scope:

- recovery brief target shape
- audit whether runtime invocation consumes loaded state/evidence appropriately
- resume-path tests

Out of scope:

- full agent runtime resume
- task-level evidence store
- database persistence

### Stage 12D — Memory Quality Policy

Goal:

Prevent long-term memory from becoming a dumping ground.

Expected benefit:

- Reliability: memory does not mislead the agent with stale/derivable facts.
- Context-efficiency: only reusable, non-derivable knowledge is recalled.
- Maintainability: memory stays distinct from todo/task/session state.

Scope:

- memory quality rules
- save-memory validation/review path
- bounded recall tests

Out of scope:

- embedding/vector recall
- auto memory extraction
- session-memory side agent

## Immediate Implementation Recommendation

Start with **Stage 12A: Context Payload Foundation**.

Do not start with 12B/12C/12D because they need a shared context payload boundary to avoid ad hoc prompt injection and duplicated render paths.
