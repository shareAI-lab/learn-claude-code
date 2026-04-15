# coding-deepgent

Independent cumulative LangChain cc product surface.

## Canonical Working Docs

For current implementation work, treat these as canonical first:

- `../AGENTS.md`
- `../.trellis/workflow.md`
- `../.trellis/project-handoff.md`
- `../.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`
- `../.trellis/spec/backend/*.md`

This README is a product summary, not the canonical place for live
coordination rules or executable implementation contracts.

## Current product stage

- `current_product_stage`: `stage-11-mcp-plugin-real-loading`
- `compatibility_anchor`: `mcp-plugin-real-loading`
- `architecture_reshape_status`: `s1-skeleton-complete`
- Upgrade policy: advance by explicit product-stage plan approval, not tutorial chapter completion.

The `current_product_stage` marker is retained here as a product-local
compatibility anchor for `coding-deepgent` docs and contract tests.

Canonical live release status has moved to Trellis:

- `../.trellis/project-handoff.md`
- `../.trellis/plans/coding-deepgent-cc-core-highlights-roadmap.md`

As of 2026-04-15, the canonical MVP closeout line is complete through
`Stage 29`, and the current recommended next task is
`release validation / PR cleanup for Approach A MVP`.

## Current architecture

- LangChain remains the runtime boundary: `RuntimeState`, `RuntimeContext`, `context=`, and LangGraph `thread_id` config own runtime invocation.
- Dependency-injector containers compose settings, runtime seams, domain tools, middleware, session storage, and agent creation; domain packages do not import containers.
- The public planning contract remains cc-aligned `TodoWrite(todos=[...])` with required `activeForm` on every todo item.
- The current product has explicit domains for runtime, permissions, hooks, prompt/context, memory, compact helpers, local skills, durable tasks, bounded subagents, local MCP tool registration, and local plugin manifests without replacing LangChain's agent runtime.

## Architecture reshape status

Project-wide S1 skeleton reshape is complete:

- bootstrap / agent-loop / CLI orchestration moved into dedicated services
- startup validation is explicit
- filesystem execution is runtime-owned instead of settings-driven by default
- session defaults now have one owner (`runtime.default_runtime_state`)
- low-value facades and global mutable public state were removed rather than kept for compatibility

## CLI surface

The stage-3 runtime-foundation CLI keeps the legacy `--prompt` path while adding grouped commands:

- `coding-deepgent --prompt "..."` — run one prompt and exit
- `coding-deepgent run "..."` — explicit one-shot command
- `coding-deepgent config show` — render the resolved local configuration without exposing secrets
- `coding-deepgent sessions list` — render the current session index view
- `coding-deepgent sessions resume <session-id> --prompt "..."` — continue a recorded session when a session provider is wired
- `coding-deepgent doctor` — verify CLI/rendering/logging dependencies locally

Rich table renderers live in `coding_deepgent.renderers.text`, and local structured logging setup lives in `coding_deepgent.logging_config`.

## Stage 4 control-plane foundation

Stage 4 adds deterministic permission/safety decisions, local lifecycle hooks, and structured prompt/context assembly as LangChain-native seams over the existing `create_agent` runtime. Interactive UI approval, auto classifiers, memory, durable tasks, subagents, and MCP/plugin loading remain future stages.

## Stage 5 memory/context/compact foundation

Stage 5 adds a store-backed long-term memory foundation seam, the model-visible `save_memory` tool, bounded memory context injection, and deterministic tool-result budget helpers. Message-history projection/pruning, LLM autocompact, session-memory side-agent writing, subagents, durable tasks, and MCP/plugin memory sync remain future work.

## Stage 6 skills/subagents/task graph

Stage 6 adds local skill loading, a store-backed durable task graph, and a minimal synchronous/stateless `run_subagent` tool. Background agents, SendMessage/mailbox, worktrees, remote/team runtime, sidechain resume, forked skill execution, extension distribution, and custom query loops remain future work.

## Stage 7 MCP/plugin extension foundation

Stage 7 adds a local MCP adapter seam that converts already-discovered MCP tools into agent-bindable `ToolCapability` entries while keeping MCP resources in a separate read-surface registry. It also adds a strict local `plugin.json` manifest loader/registry for metadata-only declarations of local tools, skills, and resources. Stage 7 intentionally does not add a connection manager, installer/update flow, remote trust workflow, background daemon, or runtime replacement.


## Stage 8 recovery/evidence/runtime-continuation foundation

Stage 8 adds a minimal recovery facility before deeper cc-core upgrades: session JSONL transcripts can carry factual evidence records, loaded sessions expose evidence alongside history/state, `sessions resume` can render a recovery brief, and the default CLI runtime uses the real local session store for list/resume. Full checkpoint browsing, task-level evidence stores, mailbox/background resume, and additional persistence dependencies remain future work.


## Stage 9 permission/trust-boundary hardening

Stage 9 extends the middleware-based permission runtime with typed settings-backed rules, explicitly trusted extra workspace directories, and capability trust metadata that distinguishes builtin tools from extension-provided tools. This stage intentionally defers interactive approval UX, remote trust, and marketplace/install flows.


## Stage 10 hooks/lifecycle expansion

Stage 10 upgrades hooks from a passive registry to a real local lifecycle seam. The runtime context now carries a hook registry, `app.agent_loop()` dispatches `SessionStart` / `UserPromptSubmit`, and `ToolGuardMiddleware` dispatches `PreToolUse`, `PostToolUse`, and `PermissionDenied`. Async hooks, plugin hooks, remote hooks, and model-visible hook context remain deferred.


## Stage 11 MCP/plugin real loading

Stage 11 upgrades the Stage 7 foundation into real loading: a root `.mcp.json` file can be parsed strictly, official `langchain-mcp-adapters` loading is used when available, MCP tool capabilities flow into the agent tool list, and local plugin declarations are validated against known local capabilities and skills. Dependency installation, marketplace/install/update flows, remote trust/auth UX, and runtime replacement remain deferred.
