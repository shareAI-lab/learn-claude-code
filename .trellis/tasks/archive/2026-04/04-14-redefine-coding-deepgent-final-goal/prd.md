# brainstorm: redefine coding-deepgent final goal

## Goal

Redefine the long-term final goal of `coding-deepgent` after partial plan loss, so future stages are evaluated against one explicit target: implement the essential cc / `cc-haha` runtime logic through LangChain/LangGraph-native primitives, while keeping the codebase professional-grade, modular, maintainable, and suitable for a large product rather than a demo.

## What I already know

* The user wants the final project goal to be: use LangChain to implement the essence of cc, specifically guided by `cc-haha` alignment.
* The user explicitly wants LangChain-first implementation choices and long-term adherence to Trellis LangChain-native implementation guidelines.
* The user wants a professional large-project codebase, not a demo.
* The user accepts complex architecture when it improves clarity.
* The architecture preferences are: modularity, open-closed principle, maintainability, and clear concise code.
* `coding-deepgent` already describes itself as an independent cumulative LangChain cc product surface.
* Current product state says it is at `stage-11-mcp-plugin-real-loading`.
* The restored Stage 3 PRD establishes these architectural principles:
  - domain-first, LangChain-inside
  - explicit dependency graph
  - high cohesion, low coupling
  - functional skeleton over empty architecture
  - no cc clone drift
* Existing product-local alignment docs already say implementation must stay LangChain-first: `create_agent`, `AgentMiddleware`, strict Pydantic tools, `Command(update=...)`, state/context schemas, store/checkpointer before custom runtime.
* Current codebase already contains explicit domains for runtime, tool_system, filesystem, todo, sessions, permissions, hooks, memory, compact, skills, tasks, subagents, MCP, and plugins.

## Assumptions (temporary)

* The final goal should be stated at the product level, not only as a chapter/tutorial roadmap.
* The final goal should define both behavior target and architecture target.
* We should preserve cc-aligned functional essence, but not blindly copy cc-haha product/UI/infrastructure details.
* We should keep the LangChain runtime boundary intact instead of replacing it with a custom query loop.

## Open Questions

* None for the current goal-definition pass.

## Requirements (evolving)

* Define the final product goal in a way that survives partial document loss.
* Make `cc-haha` the primary behavior-alignment source, with explicit evidence-based alignment decisions.
* Make LangChain/LangGraph the primary implementation framework and runtime boundary.
* Favor official LangChain components and patterns over custom framework-shaped abstractions.
* Keep the project suitable for professional long-term evolution.
* Preserve modular architecture with clear domain ownership and extension seams.
* Keep code understandable and maintainable despite architectural depth.
* Final product shape chosen: product-parity core, LangChain-native execution.
* Final-goal scope applies to the `coding-deepgent` product track only.
* “cc essence” in scope means the core systems identified by the user:
  - tool system
  - context system
  - session system
  - memory system
  - subagent / multi-agent system
  - todo system
  - task system
  - skill system
  - prompt system
* The original tutorial's 19 points are treated as the foundational implementation baseline rather than the final product boundary.
* `agents_deepagents` remains a teaching/alignment/verification track, not the final product target itself.
* Before new implementation work, define and prioritize source-backed cc core highlights instead of asking the user to approve every low-level system detail one by one.
* The highlight pass should happen in dependency order so later systems do not redefine earlier boundaries.
* Every future upgrade proposal must include a concrete benefit statement before implementation begins.
* Every upgrade discussion must explain:
  - what concrete function is being added or changed
  - what concrete gain it brings
  - which category the gain belongs to: user-visible, agent-runtime, safety, reliability, context-efficiency, maintainability, testability, or product parity
  - why the gain is worth the added complexity now
* Cross-session memory is a required product property, not a nice-to-have.
* Planned upgrades must say whether they improve cross-session memory directly, indirectly, or not at all.

## Acceptance Criteria (evolving)

* [x] The final goal states what must align with cc-haha and what must not be copied.
* [x] The final goal states which LangChain/LangGraph primitives are the preferred implementation boundary.
* [x] The final goal states the expected project shape: product-grade, modular, maintainable, non-demo.
* [x] The final goal defines stage progression logic or target completion criteria.
* [x] The final goal clarifies the boundary between product parity, teaching material, and deferred infrastructure.
* [x] The final goal names the core systems that must eventually reach cc-haha essence alignment.
* [x] Each core system gets a written “essence definition” before implementation planning resumes.
* [x] Each planned upgrade includes an explicit expected-benefit section and a why-now judgment.
* [x] Each planned upgrade includes an explicit function summary before implementation begins.
* [x] The final goal explicitly treats cross-session memory as a required end-state capability.
* [x] A source-backed cc core highlights roadmap exists and is used as the planning backlog.

## Definition of Done (team quality bar)

* Tests added/updated where implementation behavior changes
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Implementing new product code in this brainstorm task
* Reconstructing every lost historical plan verbatim
* Blind line-by-line cloning of `cc-haha`
* Prematurely committing to UI/platform/remote/runtime infrastructure details without a concrete local effect

## Technical Notes

* New brainstorm task: `.trellis/tasks/04-14-redefine-coding-deepgent-final-goal`
* Key product docs:
  - `coding-deepgent/README.md`
  - `coding-deepgent/PROJECT_PROGRESS.md`
  - `coding-deepgent/project_status.json`
* Recovered planning docs:
  - `.trellis/plans/prd-coding-deepgent-runtime-foundation.md`
  - `.trellis/plans/test-spec-coding-deepgent-runtime-foundation.md`
  - `.trellis/plans/master-plan-coding-deepgent-reconstructed.md`
  - `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
  - `.trellis/plans/coding-deepgent-h01-h10-target-design.md`
  - `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
* Existing prompt surface already encodes product intent:
  - `coding_deepgent.prompting.builder.build_default_system_prompt()`
  - “independent cumulative LangChain cc product agent”
  - “Prefer LangChain-native tools and state updates over prose when an action is needed.”
* 2026-04-14 correction: the first essence pass was too narrow because it started from individual feature bands before reading all architecture docs. Restart essence definition from a full documentation pass.
* Completed documentation read pass:
  - `/tmp/claude-code-book/README.md`
  - `/tmp/claude-code-book/00-前言.md`
  - `/tmp/claude-code-book/第一部分-基础篇/01-智能体编程的新范式.md`
  - `/tmp/claude-code-book/第一部分-基础篇/02-对话循环-Agent的心跳.md`
  - `/tmp/claude-code-book/第一部分-基础篇/03-工具系统-Agent的双手.md`
  - `/tmp/claude-code-book/第一部分-基础篇/04-权限管线-Agent的护栏.md`
  - `/tmp/claude-code-book/第二部分-核心系统篇/05-设置与配置-Agent的基因.md`
  - `/tmp/claude-code-book/第二部分-核心系统篇/06-记忆系统-Agent的长期记忆.md`
  - `/tmp/claude-code-book/第二部分-核心系统篇/07-上下文管理-Agent的工作记忆.md`
  - `/tmp/claude-code-book/第二部分-核心系统篇/08-钩子系统-Agent的生命周期扩展点.md`
  - `/tmp/claude-code-book/第三部分-高级模式篇/09-子智能体与Fork模式.md`
  - `/tmp/claude-code-book/第三部分-高级模式篇/10-协调器模式-多智能体编排.md`
  - `/tmp/claude-code-book/第三部分-高级模式篇/11-技能系统与插件架构.md`
  - `/tmp/claude-code-book/第三部分-高级模式篇/12-MCP集成与外部协议.md`
  - `/tmp/claude-code-book/第四部分-工程实践篇/13-流式架构与性能优化.md`
  - `/tmp/claude-code-book/第四部分-工程实践篇/14-Plan模式与结构化工作流.md`
  - `/tmp/claude-code-book/第四部分-工程实践篇/15-构建你自己的Agent-Harness.md`
  - `/tmp/claude-code-book/附录/A-源码导航地图.md`
  - `/tmp/claude-code-book/附录/B-工具完整清单.md`
  - `/tmp/claude-code-book/附录/C-功能标志速查表.md`
  - `/tmp/claude-code-book/附录/D-术语表.md`
  - `/root/claude-code-haha/docs/must-read/*.md`
  - `/root/claude-code-haha/docs/modules/*-deep-dive.md`

## Research Notes

### Constraints from our repo/project

* We already have a stage-based cumulative product model.
* The repo contains both a teaching track (`agents_deepagents/`) and a product track (`coding-deepgent/`).
* The product track already has cc alignment notes for later stages.
* The architecture baseline already favors domain modules plus dependency injection and explicit runtime seams.

### Expected effect

Aligning the final project goal now should improve: maintainability, product clarity, and testability. The local effect is: future stages stop drifting between “tutorial clone”, “demo”, and “product”, and every new feature can be judged against one explicit rule set: cc-haha functional essence, LangChain-native implementation, and professional product architecture.

### Compact alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Model-visible contracts | cc-haha tool names, schema fields, and required state semantics are stable and matter for agent behavior | fewer schema drifts and easier parity reasoning | strict Pydantic tools + `Command(update=...)` + typed state | align | Keep model-visible contracts cc-aware |
| Runtime boundary | cc-haha has its own runtime/product internals | avoid cloning the wrong abstraction layer | LangChain `create_agent`, middleware, state/context/store/checkpointer seams | partial | Match essence, not runtime internals |
| Product infrastructure breadth | cc-haha includes UI/platform/runtime breadth beyond current local need | avoid speculative complexity | local product-grade architecture only when effect is concrete | defer | No platform parity by default |
| Architecture style | cc-haha source implies large-product concerns, not toy examples | keep long-term extensibility and maintainability | explicit domain modules + DI + clear boundaries | align | Favor professional modular architecture |
| Core system coverage | secondary analysis from `claude-code-book` highlights tool/context/session/memory/subagent-agent/todo/task/skill/prompt systems as the meaningful conceptual core; source confirmation remains required per band | keep final-goal scope concrete instead of vague “be like cc” | final-goal scope statement + stage map | align | Treat these systems as required end-state coverage |
| 19 tutorial points | current repo teaching material uses 19 points as a staged implementation baseline | preserve learning/build order without confusing it for the full product target | foundational implementation track | align | Treat the 19 points as baseline, not final parity endpoint |

### Feasible approaches here

**Approach A: Product-parity core, LangChain-native execution** (Recommended)

* How it works:
  Define the final goal as: reproduce the essential cc-haha product logic and model-visible behavior where it has concrete local value, but always express it through official LangChain/LangGraph primitives and a professional modular architecture.
* Pros:
  - Matches the user's stated goal closely
  - Keeps parity efforts disciplined
  - Avoids custom-runtime drift
  - Fits the current codebase direction
* Cons:
  - Requires repeated scope discipline to avoid copying non-essential cc details

**Approach B: LangChain-first agent platform inspired by cc**

* How it works:
  Treat cc-haha mostly as inspiration rather than as an alignment target. Optimize for LangChain best practices first, and adopt cc behavior only when obviously useful.
* Pros:
  - Simpler planning burden
  - Less source-mapping overhead
* Cons:
  - Too weak for the user's parity intent
  - Higher risk of slowly drifting away from cc essence

**Approach C: Dual-target project**

* How it works:
  Define two equal top-level goals: teaching track parity and product track parity, each with separate completion standards.
* Pros:
  - Makes tutorial/product split explicit
  - Could help docs organization
* Cons:
  - Splits focus
  - Risks weakening the product-track final goal

## Decision (ADR-lite)

**Context**: The project needs one stable long-term target after partial plan loss, and the user wants cc-haha-aligned functional essence without abandoning LangChain-native structure.

**Decision**: Choose Approach A: product-parity core, LangChain-native execution.

**Consequences**:
- `cc-haha` remains the primary behavior-alignment reference.
- LangChain/LangGraph remains the implementation and runtime boundary.
- Product parity is judged at the level of functional essence, model-visible contracts, and important runtime semantics, not UI/platform cloning.
- Future planning must keep asking whether a cc behavior has a concrete local effect before aligning it.
- The required long-term feature bands are the core systems explicitly named by the user, with the tutorial's 19 points acting as foundation rather than completion.
- The final-goal constraint applies to `coding-deepgent`; `agents_deepagents` remains a supporting teaching/alignment track.

## Technical Approach

Define a product-level master goal for `coding-deepgent` with these rules:

* Target the functional essence of `cc-haha`, not superficial similarity or file-by-file cloning.
* Require evidence-backed alignment per feature band against local `cc-haha` source, using `claude-code-book` only as secondary orientation.
* Express behavior through official LangChain/LangGraph primitives wherever they fit:
  - `create_agent`
  - state/context schema
  - middleware
  - strict Pydantic tool schemas
  - `Command(update=...)`
  - store/checkpointer
  - graph seams where needed
* Keep a professional modular architecture with stable domain boundaries, explicit dependency composition, and open-closed extensibility.
* Treat the tutorial's 19 points as the implementation foundation and learning baseline, while the product end-state is the larger cc core-system parity target inside `coding-deepgent`.
* Treat benefit evaluation as a first-class planning gate: no upgrade should proceed on “closer to cc” alone without a concrete local payoff.

## Essence Workshop Order

Superseded by the highlight backlog in `.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`.

Original dependency-first order:

1. tool system
2. prompt system
3. context system
4. todo system
5. session system
6. memory system
7. task system
8. skill system
9. subagent / multi-agent system

Rationale:

* Tools are the model's executable surface.
* Prompt and context define how the model understands and chooses those tools.
* Todo, session, and memory define the main state layers around the loop.
* Task, skill, and subagent/multi-agent build on those boundaries rather than precede them.

## Essence Definitions (draft)

### Global correction after full documentation read

The earlier per-system definitions must be treated as provisional notes, not final decisions.

The global cc essence should be framed first as an Agent Harness architecture:

* tool-first execution loop
* permission-aware runtime
* cache-aware prompt/context engineering
* recoverable session and agent lifecycle
* explicit task/workflow discipline
* scoped memory and context compaction
* multi-agent runtime objects rather than prompt-only subcalls
* extension platform where MCP/plugin/skill/hook capabilities still flow through the same execution and permission runtime
* observability, failure recovery, and benefit/complexity evaluation as product-grade requirements

Future per-system essence definitions must be derived from this global model and then checked against `cc-haha` source for the concrete feature band.

### Global cc essence charter (draft)

#### Product target

`coding-deepgent` should become a LangChain-native implementation of the core Claude Code / cc-haha Agent Harness ideas, not a UI clone, tutorial replica, or flat demo agent.

#### Core thesis

The LLM is the reasoning engine; the harness is the product runtime that makes that reasoning safe, stateful, observable, extensible, recoverable, and useful for real coding work.

#### Required global properties

1. Tool-first execution
   All model-facing executable capabilities should enter through a strict tool contract and a unified execution path. Important capabilities should not bypass tool validation, permission, telemetry, result protocol, and state update semantics.
2. Unified execution loop
   User input, model sampling, tool calls, tool results, continuation, compaction, hooks, and stopping conditions should form one explicit runtime loop. It should not be a loose chain of one-off API calls.
3. Permission-aware by construction
   Execution must be safe by default. Permissions are not scattered inside random tools; they form a runtime layer with modes, rules, guards, and conservative failure behavior.
4. Cache-aware prompt/context engineering
   Prompt and context are engineering surfaces. Stable prefixes, dynamic deltas, scoped attachments, and cache-sensitive fork/subagent behavior are part of the product, not micro-optimizations.
5. Long-session context management
   Context management includes selection, injection, projection, tool-result budgeting, micro/auto/reactive compaction, boundary markers, and continuation safety. It is required for runtime correctness, not just token cost reduction.
6. Scoped memory
   Memory should capture reusable non-derivable knowledge, not duplicate facts obtainable from code or git. Memory write paths must be controlled, scoped, and safe from pollution.
7. Recoverable session and agent lifecycle
   Sessions, transcripts, evidence/state snapshots, agent tasks, and resume paths should make long work recoverable. Recovery should rebuild enough runtime context to continue, not merely reopen text history.
8. Agent as runtime object
   Subagents and multi-agent workers should be modeled as runtime objects/tools with lifecycle, transcript, task status, permissions, context policy, and result protocol. They are not just prompt wrappers.
9. Explicit task/workflow discipline
   Todo, Task, Plan/Execute/Verify, and Coordinator-style workflows exist to prevent long work from drifting. Research and implementation can be delegated, but synthesis/coordination must remain an owned responsibility.
10. Extension platform, not shortcuts
   MCP, plugin, skill, and hook capabilities must enter through typed extension seams and still obey execution, permission, context, and observability boundaries. Extensions are not backdoors.
11. Production-grade observability and recovery
   The system must expose enough structured state, logs, evidence, and tests to debug runtime behavior. Failures should become protocol-safe results or recoverable transitions whenever possible.
12. Benefit-gated complexity
   Each upgrade must state the concrete local benefit and why the added complexity is worth it now. “Closer to cc” is not sufficient.

#### Non-goals

* Do not clone cc-haha file layout line-by-line.
* Do not copy UI/TUI implementation details unless they create a concrete local product effect.
* Do not replace LangChain/LangGraph runtime primitives with a custom query runtime unless there is no LangChain-native path.
* Do not collapse TodoWrite and durable Task into one concept.
* Do not let plugins, skills, hooks, MCP, or subagents bypass tool and permission boundaries.
* Do not store easily re-derivable codebase facts as long-term memory.

#### LangChain-native expression rule

When translating cc essence into `coding-deepgent`, prefer official LangChain/LangGraph primitives:

* `create_agent` / LangGraph runtime invocation
* state schema and context schema
* strict Pydantic `@tool(..., args_schema=...)`
* `Command(update=...)` for model-visible state updates
* middleware for guard/hook/context/memory behavior
* store/checkpointer for persistent or cross-thread state
* explicit graph seams only when the behavior is naturally graph-shaped

Avoid custom wrappers, fallback parsers, alias normalizers, or private mini-runtimes when an official primitive handles the boundary.

#### Per-system discussion template

Use this template for each core system before implementation planning:

* System role in the harness:
* Concrete benefit:
* cc / cc-haha essence:
* LangChain-native expression:
* Product-grade architecture shape:
* Must-align:
* Partial / LangChain equivalent:
* Defer:
* Do-not-copy:
* Complexity / why-now judgment:

### 1. Tool System

Status: current working definition, revised after full `claude-code-book` and `cc-haha/docs` reading.

#### Expected effect

Aligning the tool system should improve: agent-runtime reliability, safety, maintainability, testability, observability, and product parity.

The local runtime effect is: every model-facing executable capability enters through one strict LangChain tool contract and one guardable execution path, so validation, permission checks, progress/events, state updates, result mapping, and failure handling remain consistent across builtin tools, skills, MCP tools, durable tasks, and agent tools.

Why this is worth complexity:

* A strict tool system prevents special-case execution paths from bypassing safety and observability.
* It makes new capabilities easier to add because they attach to a known contract instead of requiring a new runtime branch.
* It protects LangChain-native simplicity: tool behavior lives in schemas, tool functions, middleware, and state updates rather than in prompt prose or private mini-runtimes.

#### Primary reference points

* `cc-haha` primary source:
  - `/root/claude-code-haha/src/Tool.ts`
    Evidence: `Tool` includes `call`, `description`, `inputSchema`, `isConcurrencySafe`, `isReadOnly`, `isDestructive`, `interruptBehavior`, `shouldDefer`, `alwaysLoad`, `mcpInfo`, `maxResultSizeChars`, `strict`, `validateInput`, `checkPermissions`, `toAutoClassifierInput`, `mapToolResultToToolResultBlockParam`, and result rendering hooks.
  - `/root/claude-code-haha/src/Tool.ts:743-792`
    Evidence: `buildTool` fills safe defaults, including fail-closed defaults for concurrency and read-only behavior.
  - `/root/claude-code-haha/docs/must-read/01-execution-engine.md:122-189`
    Evidence: tool execution flows through orchestration, streaming execution, validation, permission checks, hooks, tool call, telemetry, and result blocks; the tool pool is dynamic.
  - `/root/claude-code-haha/docs/modules/01-execution-engine-deep-dive.md:220-300`
    Evidence: deep-dive frames tool execution as a layered runtime pipeline and emphasizes streaming semantics.
  - related tool implementations under `/root/claude-code-haha/src/tools/*`
* Secondary analysis:
  - `/tmp/claude-code-book/第一部分-基础篇/03-工具系统-Agent的双手.md`
  - `/tmp/claude-code-book/附录/B-工具完整清单.md`
* LangChain primary docs:
  - `/oss/python/langchain/tools`: tools are callable functions with well-defined inputs/outputs; Pydantic `args_schema` supports complex inputs; `ToolRuntime` gives hidden runtime access; `Command(update=...)` updates state.
  - `/oss/python/langchain/agents`: `create_agent` is a LangGraph-backed agent runtime; tools can be statically registered, dynamically filtered, or dynamically registered/executed through middleware.
  - `/oss/python/langchain/middleware/custom`: middleware supports `wrap_tool_call` around each tool call and can return `Command` for state updates.

#### System role in the harness

The tool system is the harness boundary where model intent becomes executable action. It owns the model-visible action contract and routes every important capability into runtime validation, permission, execution, result/state update, and telemetry.

It is not merely:

* a Python function registry
* a bag of helper methods
* a prompt manual telling the model what actions exist
* a direct shortcut into filesystem/session/task/subagent internals

#### cc / cc-haha essence

* Tools are first-class runtime capabilities, not ad hoc callbacks.
* A tool has both a model-visible surface and runtime-only behavior.
* The model-visible surface must be stable:
  - name
  - description
  - strict input schema
  - required fields and field semantics
* The runtime-only behavior must be explicit:
  - input validation
  - permission and guard decision
  - read-only / destructive / concurrency-safe classification
  - interruption behavior
  - result size / persistence policy
  - progress/event emission
  - tool result mapping back to the model protocol
  - telemetry / classifier summary where relevant
* The execution path is layered:
  - tool orchestration decides scheduling
  - streaming executor preserves stream/progress/cancel semantics
  - single-tool execution performs validation, permission, hooks, call, result mapping, and telemetry
* The tool pool is dynamic runtime state:
  - mode changes may alter visible tools
  - deferred tools may unlock later
  - MCP/plugin/skill-provided tools may appear through extension surfaces
  - agent-specific and plan-mode tool pools may be constrained
* Agents exposed to the model should be tools too. `AgentTool` is the key architectural signal: subagents should inherit tool lifecycle, permission, transcript/evidence, task status, and result protocol rather than bypass the tool runtime.
* Failures should become protocol-safe tool results where possible. A bad tool call should not silently corrupt the loop or break tool-use/result pairing.

#### Feature boundary

In scope for tool-system essence:

* model-visible tool contracts
* strict input schemas and validation
* capability metadata and registry
* runtime-visible tool pool selection/filtering
* unified guardable execution path
* dynamic extension tool registration/execution where needed
* progress/event emission
* tool result and state update protocol
* concurrency/interruption semantics
* result budget/persistence hooks at tool boundary
* agent-as-tool principle

Not in scope for tool-system essence:

* prompt wording strategy
* context selection/compaction policy
* memory extraction/write policy beyond tool exposure
* durable task collaboration semantics beyond tool exposure
* UI/TUI rendering details
* implementation of every cc-haha tool class one-for-one
* provider-specific SDK plumbing that LangChain already abstracts

#### LangChain-native expression

The local LangChain/LangGraph shape should be:

* Use strict Pydantic input schemas with `ConfigDict(extra="forbid")`.
* Use `@tool(..., args_schema=...)` for structured model-visible tool contracts.
* Put model-visible guidance in the tool description and `Field(description=...)`, not in a giant system-prompt manual.
* Use `Command(update=...)` when a tool updates LangGraph state.
* Use hidden runtime access only through official `ToolRuntime` / injected runtime surfaces; do not make runtime-only fields model-visible.
* Use `AgentMiddleware.wrap_tool_call` for guard, permission, hook dispatch, telemetry, and safe error mapping.
* Use `wrap_model_call` / request override for dynamic tool filtering when tools are known at startup but exposed conditionally.
* Use both `wrap_model_call` and `wrap_tool_call` for truly runtime-discovered tools, such as MCP-loaded tools, because the agent must both expose and execute them.
* Keep a product-local `CapabilityRegistry` for metadata LangChain tools do not natively encode well: source, trust, read-only/destructive/concurrency classifications, extension provenance, and policy codes.
* Avoid fallback parsers, alias guessing, and `dict[str, Any]` normalization for model input. Schema validation should fail clearly.

#### Product-grade architecture shape

Suggested product-local boundaries:

* `tool_system.capabilities`: capability metadata, source/trust, registry, and tool-pool descriptors
* `tool_system.policy`: permission and safety decisions over tool calls
* `tool_system.middleware`: LangChain `AgentMiddleware` bridge for guard/hooks/events
* domain-owned `tools.py`: actual LangChain tool definitions near their domain, for example `todo/tools.py`, `filesystem/tools.py`, `tasks/tools.py`
* extension domains (`mcp`, `plugins`, `skills`) adapt external declarations into capabilities, but execution still returns to the same guardable tool path

Do not create a second generic `Tool` framework that competes with LangChain. The registry should complement LangChain with metadata and policy, not replace `@tool` / middleware.

#### Alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Tool contract | `Tool.ts` defines a rich tool interface with name, schema, call, validation, permission, concurrency, interruption, result mapping, classifier input, and rendering hooks | model-facing action surface is stable and runtime behavior is inspectable | strict Pydantic `@tool` plus product capability metadata | align | Match functional contract, not TypeScript interface shape |
| Safe defaults | `buildTool` fills defaults and assumes non-read-only / non-concurrency-safe unless tools opt in | new tools are safe by default and require explicit safety metadata | `CapabilityRegistry` defaults plus tests | align | Fail closed for policy metadata |
| Execution pipeline | docs map `tool_use -> orchestration -> streaming executor -> execution -> tool_result` | one guardable path for validation, permission, hooks, execution, telemetry | LangChain `wrap_tool_call` middleware around tool execution | partial | Use LangChain middleware rather than custom executor unless LangChain lacks needed semantics |
| Tool pool dynamics | docs state deferred tools, plan mode, MCP, and agent changes can alter visible tools | model sees the right tool set for mode/context without prompt overload | pre-register/filter tools via middleware; dynamic MCP via middleware | align | Use official dynamic tool patterns first |
| Agent as tool | Agent runtime docs model agent launch through `AgentTool` | subagents inherit lifecycle/safety/result boundaries | `run_subagent` / future richer agent tool | align | All model-facing subagent calls remain tools |
| UI rendering hooks | `Tool.ts` contains rich rendering methods | terminal UX improves, but not essential for LangChain product core now | CLI renderers outside tool contract | defer/do-not-copy | Do not copy UI surface unless a concrete product need appears |
| Provider-specific schema details | cc-haha uses Zod/Anthropic-specific tool schemas | avoid wrong abstraction layer in Python product | Pydantic + LangChain tool schema | do-not-copy | Preserve behavior, not provider-specific implementation |

#### Must-align

* Model-visible names and schemas for cc-critical tools such as `TodoWrite`.
* Unified guardable execution path.
* Tool result/state update protocol.
* Dynamic tool-pool control by mode, context, and extension state.
* Agent/subagent model-facing entry as a tool.
* Safe default metadata and explicit opt-in for risky classifications.

#### Partial / LangChain equivalent

* cc-haha `Tool` interface becomes LangChain tool + capability metadata + middleware, not a new custom base class.
* cc-haha streaming executor semantics are approximated through LangChain/LangGraph streaming and middleware first; add custom helpers only for demonstrated gaps.
* cc-haha result rendering belongs in product CLI renderers, not in the model-facing tool contract.

#### Defer

* Full ToolSearch / deferred-tool parity until tool count or MCP growth creates measurable context pressure.
* Fine-grained parallel scheduling beyond LangGraph's current tool execution semantics until tests show it affects correctness or performance.
* Rich UI grouped rendering and transcript-search rendering.

#### Do-not-copy

* TypeScript/Zod interface structure as Python architecture.
* UI/TUI rendering methods inside core tool contracts.
* Alias compatibility that hides model-visible schema drift.
* A custom tool executor that bypasses LangChain just to look like cc-haha.

#### Complexity / why-now judgment

Worth doing now:

* strict schemas, capability registry metadata, and `wrap_tool_call` guard path, because they directly improve safety, testability, and maintainability for every current and future tool
* explicit dynamic tool-pool policy, because current product already has MCP/plugin/skill/task/subagent surfaces

Not worth doing yet:

* full custom streaming executor parity, because LangChain already supplies an agent runtime and middleware hooks; we should first identify exact missing behavior with tests
* UI-level rendering parity, because product correctness does not depend on it yet

#### Confirmed decisions

* Core principle confirmed by user: all important capabilities should become tools first.
* Exception boundary: pure runtime-internal plumbing may remain non-tool if it is not a model-facing capability.

### 2. Permission / Safety System

Status: current working definition, derived after full documentation read and source re-check.

#### Expected effect

Aligning the permission / safety system should improve: safety, reliability, maintainability, testability, observability, and product parity.

The local runtime effect is: the product can allow the model to take real actions without turning every tool into a bespoke risk decision. Tool calls are evaluated by one explicit safety runtime with modes, rules, hard guards, trust metadata, hook integration, conservative headless behavior, and auditable decision reasons.

Why this is worth complexity:

* Coding agents are dangerous because they can edit files, run commands, call external tools, and spawn other agents. A single guard function is not enough.
* Permission decisions must be explainable and testable, otherwise later MCP/plugin/skill/subagent expansion becomes unsafe.
* The project already has extension tools and task/subagent tools; a stronger safety runtime is a foundation, not a late add-on.

#### Primary reference points

* `cc-haha` primary source:
  - `/root/claude-code-haha/docs/must-read/05-permission-security.md:5-19`
    Evidence: permission is framed as deciding when model actions execute, ask, degrade, or deny; it includes modes, rules, filesystem safety, auto classifier, tool handlers, UI approval, plan mode, and ask-user semantics.
  - `/root/claude-code-haha/docs/must-read/05-permission-security.md:113-150`
    Evidence: permission runtime has rule, resource-safety, strategy, and interaction layers; auto mode is fail-safe, not direct allow.
  - `/root/claude-code-haha/docs/must-read/05-permission-security.md:166-200`
    Evidence: hooks cannot skip permission, auto mode strips dangerous broad rules, bypass is not unlimited, shadowed rules matter, and AskUserQuestion is protected.
  - `/root/claude-code-haha/src/types/permissions.ts`
    Evidence: modes, rule sources, update destinations, allow/ask/deny decisions, passthrough, and structured decision reasons are typed separately to avoid import cycles and improve explainability.
  - `/root/claude-code-haha/src/utils/permissions/permissions.ts:473-880`
    Evidence: permission decisions reset/track denials, convert `dontAsk` asks to deny, guard auto mode safety checks, use accept-edits fast paths, safe-tool allowlists, classifier decisions, overhead telemetry, and fail-closed classifier behavior.
* Secondary analysis:
  - `/tmp/claude-code-book/第一部分-基础篇/04-权限管线-Agent的护栏.md`
  - `/tmp/claude-code-book/第二部分-核心系统篇/05-设置与配置-Agent的基因.md`
  - `/tmp/claude-code-book/第二部分-核心系统篇/08-钩子系统-Agent的生命周期扩展点.md`
* LangChain primary docs:
  - `/oss/python/langchain/guardrails`: guardrails can be deterministic or model-based and implemented with middleware around agent execution.
  - `/oss/python/langchain/human-in-the-loop`: HITL middleware interrupts tool calls, persists graph state through checkpointing, and supports approve/edit/reject decisions.
  - `/oss/python/langchain/middleware/custom`: `wrap_tool_call` runs around each tool call and is the right primitive for permission/guard decisions at the tool boundary.

#### System role in the harness

Permission / Safety is the runtime layer that turns “the model wants to act” into “the product may or may not execute this action now.”

It is not merely:

* a boolean allow/deny helper
* a set of per-tool if statements
* a CLI confirmation prompt
* a LangChain middleware with no durable policy model
* a post-hoc audit log after dangerous actions already ran

#### cc / cc-haha essence

* The product treats an agent as a potentially dangerous executor, not just a helpful model.
* Permission mode is top-level runtime state:
  - default
  - plan
  - acceptEdits
  - auto
  - bypassPermissions
  - dontAsk
  - internal/bubble-style delegation where applicable
* Permission decisions are layered:
  - tool input/schema validity
  - allow / ask / deny rules
  - hard resource safety, especially filesystem/path safety
  - mode strategy
  - classifier or automated decision where appropriate
  - interactive / headless / coordinator / worker behavior
* Filesystem safety is its own kernel-level concern for a coding agent:
  - dangerous paths
  - workspace escape
  - extra trusted workdirs
  - shell command risk
  - symlink / path normalization and cross-platform path edge cases where needed
* Auto mode is not “trust the model.” It is a constrained automation layer with:
  - safe fast paths
  - dangerous broad-rule stripping
  - classifier decision
  - denial tracking
  - conservative fallback when classifier fails or prompts are unavailable
* Bypass mode is not absolute; some safety checks remain immune to bypass.
* Hooks and extensions are not safety backdoors. Hook allow/ask must still respect the permission runtime.
* AskUserQuestion and plan-mode transitions are safety-sensitive user-interaction capabilities, not ordinary text.
* Decisions must carry reasons and metadata, not just booleans, so the system can explain, test, log, and later refine behavior.

#### Feature boundary

In scope for permission/safety essence:

* permission modes and mode transitions
* allow / ask / deny local rules
* rule sources and destinations
* hard safety guards for filesystem and command execution
* trusted/untrusted capability source handling
* extension trust metadata for MCP/plugin/skill tools
* headless / non-interactive fallback behavior
* pre-tool hooks that cannot bypass hard guards
* structured decision reasons and local runtime events
* plan-mode read-only boundary
* ask-user-question protection
* future HITL approval path

Not in scope for current permission/safety essence:

* cloning cc-haha's full permission UI
* full YOLO/auto classifier parity before deterministic policy is solid
* enterprise policy/MDM/marketplace trust UX unless a concrete product need appears
* remote auth / XAA / bridge control surfaces until the product has those runtime modes
* fully general shell AST classifier unless simple command policy proves insufficient

#### LangChain-native expression

The local LangChain/LangGraph shape should be:

* Use `AgentMiddleware.wrap_tool_call` as the primary tool-boundary guard.
* Return `ToolMessage(status="error")` for denied/rejected actions so the model receives protocol-safe feedback.
* Use LangGraph `Command` / interrupt patterns for future human-in-the-loop approval where execution must pause and resume.
* Use checkpointer persistence when HITL interrupts are introduced, because LangChain HITL requires graph state persistence across interrupts.
* Use deterministic guard middleware before adding model-based classifiers.
* Use capability metadata from `CapabilityRegistry` to evaluate source, trust, read-only, destructive, and domain information.
* Keep policy logic in `permissions` / `tool_system.policy`, not in individual tool functions except for tool-local invariants.
* Use built-in or custom LangChain guardrails only where they match the local product boundary; do not import broad guardrail machinery without a concrete benefit.

#### Product-grade architecture shape

Suggested product-local boundaries:

* `permissions.modes`: external/internal modes and transitions
* `permissions.rules`: explicit local rules, sources, and match semantics
* `permissions.manager`: deterministic permission runtime for one tool call
* `permission_specs`: settings/env-facing rule specs
* `filesystem.policy`: command/path hard safety
* `tool_system.policy`: maps capability metadata + permission runtime to tool-call decisions
* `tool_system.middleware`: LangChain `wrap_tool_call` integration, hook dispatch, event emission
* future `permissions.hitl`: LangGraph interrupt/resume based approval flow

Current local evidence:

* `coding_deepgent.permissions.manager.PermissionManager` already has mode, rules, hard safety, read-only bash recognition, trusted workdirs, extension trust, and `dontAsk` conversion.
* `coding_deepgent.tool_system.middleware.ToolGuardMiddleware` already uses LangChain middleware to deny/allow, emit runtime events, and dispatch `PreToolUse`, `PostToolUse`, and `PermissionDenied` hooks.

#### Alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Runtime framing | permission is a runtime deciding execute/ask/deny/degrade, not per-tool private logic | one safety layer for all tools | `PermissionManager` + `ToolGuardMiddleware` | align | Keep one permission runtime |
| Modes | cc-haha has default/plan/acceptEdits/auto/bypass/dontAsk plus internal delegation | actions change behavior by explicit mode | `PermissionMode` with deterministic local modes | partial | Keep current modes; add richer mode semantics incrementally |
| Rule engine | allow/deny/ask rules with sources and update destinations | explainable local policy | `PermissionRule`, specs, metadata | partial | Expand only as needed; do not overbuild enterprise sources yet |
| Hard filesystem safety | filesystem/path safety is an independent core layer | prevent workspace escape and dangerous command/path behavior | `filesystem.policy` + hard safety before rules/mode where appropriate | align | Treat as bypass-resistant guard |
| Auto classifier | auto mode uses fast paths, classifier, denial tracking, fail-safe behavior | reduce prompts without unsafe automation | future classifier layer | defer | Do deterministic policy first |
| Headless behavior | no UI means asks cannot hang; fallback is conservative | background/subagent/tool calls do not deadlock | deny/ToolMessage for no-approval contexts | align | Keep conservative non-interactive behavior |
| Hook relationship | hooks cannot bypass permission runtime | extension hooks are not backdoors | `ToolGuardMiddleware` order + hard guard checks | align | PreToolUse can block, not override hard safety |
| Approval UI | cc-haha has rich per-tool UI | better UX but not core runtime now | future CLI/HITL approval UX | defer | Use LangGraph HITL only when local interactive approval is required |
| Decision reasons | decisions carry rule/mode/hook/classifier/safety reasons | auditable tests and debugging | structured `PermissionDecision` metadata/events | align | Make every deny/ask explainable |

#### Must-align

* Permission is one runtime layer, not scattered per-tool business logic.
* Deny/hard-safety decisions must be explicit and explainable.
* Plan mode must prevent write/destructive actions while allowing meaningful read/research.
* `dontAsk` converts would-ask actions to deny rather than blocking indefinitely.
* Extension-provided or untrusted capabilities should be more conservative than builtin trusted tools.
* Headless/background contexts must not wait for impossible user approval.
* Hooks and extensions must not bypass hard safety or permission runtime.

#### Partial / LangChain equivalent

* cc-haha interactive approval UI becomes LangChain `ToolMessage` deny path now, with future LangGraph HITL interrupt/resume when user approval UX is intentionally added.
* cc-haha classifier/auto mode becomes deterministic local policy now; model-based classifier is a later optional layer.
* cc-haha rich rule sources become a small local settings/env rule model now.
* cc-haha permission telemetry becomes local `RuntimeEvent` evidence now, with richer observability later.

#### Defer

* YOLO / auto-mode classifier parity
* shadowed-rule UI
* enterprise managed policy UX
* remote approval routing / bridge permission callbacks
* broad shell AST classifier parity
* per-tool rich approval dialogs

#### Do-not-copy

* React/Ink permission UI internals
* Anthropic-specific classifier telemetry fields
* broad allow stripping rules without a local auto-mode classifier to justify them
* bypass behavior that allows hard filesystem safety to be skipped
* permission aliases that hide tool/schema mismatch

#### Complexity / why-now judgment

Worth doing now:

* deterministic mode/rule/hard-safety policy because current product already executes filesystem, memory, skills, tasks, subagents, MCP, and plugin-related tools
* structured decision reasons and runtime events because debugging safety behavior without them is guesswork
* extension trust metadata because Stage 7-11 already introduced MCP/plugin surfaces

Not worth doing yet:

* model-based classifier and auto-mode broad-rule stripping, because deterministic guard behavior must be trusted first
* rich HITL UI, because current API/CLI can safely return protocol-level deny/ask messages until there is a concrete approval UX requirement

### 3. Prompt System

Status: current working definition, revised after full documentation read and source re-check.

#### Expected effect

Aligning the prompt system should improve: reliability, context-efficiency, maintainability, agent-role clarity, cache efficiency, and product parity.

The local runtime effect is: the model receives a stable, layered instruction contract that defines product identity, behavioral invariants, role/mode overlays, and user customizations without turning dynamic runtime state into a fragile monolithic system prompt.

Why this is worth complexity:

* Prompt drift is one of the easiest ways to make an agent unreliable, especially once tools, tasks, memory, skills, and subagents interact.
* A layered prompt makes role/mode behavior auditable and testable instead of buried in one large string.
* Cache-aware prompt structure matters for long-running agents and fork/subagent behavior; changing high-volatility prompt bytes can destroy cache efficiency.

#### Primary reference points

* `cc-haha` primary source:
  - `/root/claude-code-haha/docs/must-read/03-prompt-context-memory.md:5-16`
    Evidence: prompt/context/memory is framed as engineering for long-running agents, not just writing a good prompt.
  - `/root/claude-code-haha/docs/must-read/03-prompt-context-memory.md:66-77`
    Evidence: system prompt assembly flows through `systemPrompt.ts`, default prompt, coordinator/main-thread/custom/append layers, `context.ts`, `queryContext.ts`, and then query cache-key prefix use.
  - `/root/claude-code-haha/docs/must-read/03-prompt-context-memory.md:117-145`
    Evidence: system prompt has five layers; `userContext` and `systemContext` are separated for cache engineering.
  - `/root/claude-code-haha/docs/modules/03-prompt-context-memory-deep-dive.md:19-40`
    Evidence: system prompt is multi-layered so core behavior, role overlays, custom prompt, and append prompt remain separated.
  - `/root/claude-code-haha/src/utils/queryContext.ts:30-43`
    Evidence: `fetchSystemPromptParts` returns default system prompt, user context, and system context as cache-key prefix pieces; custom prompt replaces default prompt and skips default system context.
  - `/root/claude-code-haha/src/context.ts:113-188`
    Evidence: system and user context are cached for the conversation and kept distinct.
* Secondary analysis:
  - `/tmp/claude-code-book/第二部分-核心系统篇/07-上下文管理-Agent的工作记忆.md`
  - `/tmp/claude-code-book/第四部分-工程实践篇/13-流式架构与性能优化.md`
* LangChain primary docs:
  - `/oss/python/langchain/agents`: `system_prompt` shapes agent behavior; `SystemMessage` gives control over prompt structure and provider features like Anthropic prompt caching.
  - `/oss/python/langchain/agents`: `@dynamic_prompt` middleware can generate prompts from runtime context or state.
  - `/oss/python/langchain/context-engineering`: model context includes instructions, messages, tools, model choice, and response format; middleware is the mechanism for modifying context across the agent lifecycle.

#### System role in the harness

The prompt system is the harness layer that defines the model's stable operating contract: identity, product role, behavioral invariants, role/mode overlays, and customization boundaries.

It is not merely:

* prose copywriting
* a dump of all project context
* a replacement for tool descriptions
* a memory retrieval system
* a task/workflow state store
* a place to hide missing schemas or policies

#### cc / cc-haha essence

* The prompt is a layered instruction architecture, not one giant string.
* Stable behavior rules and product identity are separate from dynamic runtime context.
* Role overlays are first-class:
  - coordinator prompt
  - main-thread agent prompt
  - subagent / specialized agent prompt
  - plan-mode prompt
  - verification/coordinator constraints where applicable
* Custom prompt and append prompt have distinct semantics:
  - custom prompt may replace the default base
  - append prompt extends after the base
  - neither should silently erase safety/tool/model-visible contracts without an explicit product decision
* User context and system context are separated because their volatility and cache effects differ.
* Dynamic state such as plan mode, agent list deltas, deferred tools, task status, teammate mailbox, and relevant memory does not belong in the stable core prompt by default.
* Tool-specific rules belong in tool descriptions/schemas/validators, not a global tool manual embedded into the prompt.
* Prompt assembly must be cache-aware. A high-volatility prompt prefix is a product/runtime bug, not just a cost issue.
* Prompt engineering, context engineering, and memory engineering are adjacent but not identical:
  - prompt defines stable behavioral contract
  - context decides dynamic information placement
  - memory decides what durable knowledge exists and how it is recalled

#### Feature boundary

In scope for prompt-system essence:

* layered system-prompt construction
* stable vs dynamic instruction separation
* prompt role composition
* role/mode overlay semantics
* custom vs append prompt semantics
* cache-aware prompt prefix design
* small, auditable prompt builder API
* tests proving tool manuals and dynamic data are not accidentally shoved into system prompt

Not in scope for prompt-system essence:

* memory retrieval policy itself
* session replay/recovery mechanics
* full context selection and compaction strategy
* UI copy or presentation style
* tool-specific manuals that belong in tool schemas/descriptions
* full prompt-cache block metadata until provider-specific caching becomes an explicit local goal

#### LangChain-native expression

The local LangChain/LangGraph shape should be:

* Use a small `PromptContext` / prompt builder as the default static prompt source.
* Use LangChain `system_prompt` for stable base prompt when prompt is known at agent construction.
* Use `SystemMessage` only when provider-specific block-level structure or cache controls are intentionally needed.
* Use `dynamic_prompt` middleware when prompt must change based on runtime context or state.
* Use `context_schema` to pass immutable runtime facts used by prompt middleware.
* Keep dynamic task/memory/tool deltas in context/message assembly middleware, not in the core base prompt.
* Keep tool-specific behavior in `@tool` descriptions and Pydantic `Field(description=...)`.
* Keep prompt builders dependency-light; they should not import heavy domain services or become a service locator.

#### Product-grade architecture shape

Suggested product-local boundaries:

* `prompting.builder`: stable base prompt, custom/append semantics, prompt parts
* `prompting.context`: structured prompt context object and render helpers if builder grows
* `prompting.middleware`: future LangChain `dynamic_prompt` middleware for role/mode overlays that truly depend on state/context
* domain-level prompt fragments only when the domain owns global behavior, not tool-local usage docs

Current local evidence:

* `coding_deepgent.prompting.builder.PromptContext` already separates `default_system_prompt`, `user_context`, `system_context`, `append_system_prompt`, and `memory_context`.
* `build_default_system_prompt()` already encodes product identity and LangChain-native tool/state preference.
* Current tests already assert `write_file` / stale tool wording is not accidentally present in the system prompt.

#### Alignment matrix

| Area | cc-haha source behavior | Expected local effect | Local target | Status | Decision |
|---|---|---|---|---|---|
| Layered prompt | cc-haha separates default, coordinator, main-thread agent, custom, and append prompt | role and mode behavior stays auditable | `PromptContext` + builder / future middleware | align | Keep layers explicit |
| Cache-key prefix | `queryContext.ts` fetches default prompt, user context, system context as cache-key pieces | stable prompt prefix and lower cache churn | stable builder + avoid volatile prompt injection | align | Treat volatility as architecture concern |
| Custom prompt | cc-haha custom prompt can replace default and skip default system context | user override is explicit and testable | `custom_system_prompt` replaces base | align | Preserve current behavior, document risk |
| Append prompt | cc-haha append prompt extends after base | local customization without replacing base identity | `append_system_prompt` | align | Keep separate from custom replacement |
| Dynamic attachments | cc-haha routes many dynamic states through attachments, not the base prompt | avoid giant fragile system prompt | context/message assembly layer | partial | Handle in context system, not prompt system |
| Tool manuals | cc-haha tools own prompts/descriptions | reduce prompt bloat and schema drift | tool descriptions and Field docs | align | Do not put full tool manual in system prompt |
| Provider cache blocks | LangChain supports `SystemMessage` content blocks/cache controls | optimize costs when needed | future explicit provider-specific prompt blocks | defer | Only add with measured cache benefit |

#### Must-align

* Prompt is layered, not a single undifferentiated string.
* Stable product identity and behavioral invariants remain in the base prompt.
* Custom and append prompt semantics stay distinct.
* Dynamic state does not rewrite the core prompt by default.
* Tool-specific instructions live with tools.
* Prompt structure is tested because regressions are hard to see from behavior alone.

#### Partial / LangChain equivalent

* cc-haha's attachment relationship belongs mostly to the Context System in this product, not Prompt System.
* cc-haha's provider/cache-specific system prompt block handling becomes LangChain `SystemMessage` only when required.
* role overlays can initially be builder-level flags; use `dynamic_prompt` middleware only when runtime state/context actually drives prompt changes.

#### Defer

* full prompt-cache block metadata
* coordinator/subagent prompt overlays until those runtime modes are upgraded
* dynamic prompt middleware if static builder is still enough
* prompt dumping / prompt-cache break diagnostics as first-class UX

#### Do-not-copy

* a huge cc-haha system prompt verbatim
* dynamic task/memory/tool state embedded into the stable base prompt
* Anthropic-only prompt block structures unless explicitly needed
* tool manuals in the base prompt
* prompt-builder imports of containers or business services

#### Complexity / why-now judgment

Worth doing now:

* preserve a structured prompt builder and tests, because the current product already has memory, tasks, skills, permissions, and tool contracts whose wording can drift
* clarify custom/append/memory roles, because those settings already exist locally

Not worth doing yet:

* provider-specific prompt-cache block structure, because the current product has not established a measured cache optimization need
* complex dynamic prompt middleware for roles not yet productized in `coding-deepgent`

#### Confirmed decisions

* Core principle confirmed by user: dynamic state should normally enter through attachment / delta / runtime message assembly rather than repeated rewrites of the core system prompt.

### 4. Context System

#### Expected effect

Aligning the context system should improve: context-efficiency, reliability, maintainability, and long-session continuity. The local runtime effect is: only relevant dynamic information enters the model window, context pressure is handled through controlled projection/compaction/recovery paths, and protocol-critical message structure survives long tasks instead of collapsing into an unbounded transcript.

#### Primary reference points

* `cc-haha` primary source:
  - `/root/claude-code-haha/docs/must-read/03-prompt-context-memory.md`
  - `/root/claude-code-haha/docs/must-read/01-execution-engine.md`
  - `/root/claude-code-haha/src/utils/attachments.ts`
  - `/root/claude-code-haha/src/utils/messages.ts`
  - `/root/claude-code-haha/src/context.ts`
  - `/root/claude-code-haha/src/utils/queryContext.ts`
  - `/root/claude-code-haha/src/services/compact/compact.ts`
  - `/root/claude-code-haha/src/services/compact/autoCompact.ts`
  - `/root/claude-code-haha/src/services/compact/microCompact.ts`
  - `/root/claude-code-haha/src/services/compact/sessionMemoryCompact.ts`
  - `/root/claude-code-haha/src/utils/toolResultStorage.ts`
* Secondary analysis:
  - `claude-code-book` orientation on context management and compaction

#### Essence

* The context system decides what information enters the model window, when it enters, where it is placed, and how long it remains useful.
* It is a scoped dynamic-information and context-pressure management system, not a dump-everything mechanism.
* Context must have explicit categories and scopes:
  - project/user context
  - system/runtime context
  - file/path-scoped context
  - tool/task/agent/mode deltas
  - memory-derived context
* Dynamic context should be deduplicated and scoped rather than globally injected.
* Context injection should fail soft: one broken attachment or missing memory file should not break the whole runtime.
* Context should be lifecycle-aware:
  - some context is per-turn
  - some is session-scoped
  - some is path-scoped
  - some is role/agent-scoped
  - some is long-term memory-derived
* The system must protect token budget and cache stability while preserving enough state for continuation.
* Context compression is a core context-system responsibility, not an optional summarization utility.
* Compression is multi-strategy, not one summary function:
  - tool-result budgeting and persistence
  - message projection / normalization that preserves protocol structure
  - microcompact for lower-cost cleanup of old tool results
  - auto-compact when the window approaches threshold
  - session-memory-assisted compaction when available
  - reactive prompt-too-long recovery when proactive paths fail
  - post-compact cleanup and restoration of important working context
* Context compression must preserve protocol correctness:
  - tool use / tool result pairing
  - recent execution window
  - compact boundary markers
  - enough file/task/skill context to continue work
* Context pressure should be observable and guardable through thresholds, warning state, and circuit breakers rather than infinite failed retry loops.

#### Feature boundary

In scope for context-system essence:

* dynamic attachment/delta protocol
* context scope and deduplication
* runtime message assembly for contextual state
* path-scoped project context
* fail-soft context injection
* context lifecycle categories
* context budget measurement and thresholds
* tool-result budget / persistence strategy
* message projection and normalization for API-bound context
* microcompact / auto-compact / reactive compact behavior
* post-compact restoration of critical working context
* compact boundary markers and continuation safety

Not in scope for context-system essence:

* exact memory extraction/write policy
* session transcript persistence itself
* task state machine semantics
* UI rendering
* the exact wording of compact prompts, except where it affects continuation quality

#### LangChain-native expression

The local LangChain/LangGraph shape should be:

* typed runtime context object(s)
* bounded context rendering helpers
* state/context schemas for runtime-visible state
* middleware or invocation assembly for dynamic per-turn context
* LangGraph store/checkpointer only where the context is persistent or cross-turn
* deterministic compaction/projector helpers around LangGraph message history
* explicit tests that compressed/projected history still preserves tool/state protocol invariants
