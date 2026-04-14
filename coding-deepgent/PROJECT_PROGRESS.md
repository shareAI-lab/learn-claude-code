# coding-deepgent progress

## Current product stage

- `current_product_stage`: `stage-11-mcp-plugin-real-loading`
- `compatibility_anchor`: `mcp-plugin-real-loading`
- `architecture_reshape_status`: `s1-skeleton-complete`
- Status: MCP/plugin real loading implemented as one cumulative LangChain cc product surface
- Last updated: 2026-04-14

## Project-wide architecture reshape (S1 skeleton)

The facility stages remain at Stage 11, but the product skeleton has been reshaped to reduce central-file pressure and low-value public glue:

- `app.py` is now a thin entrypoint over `bootstrap.py` and `agent_loop_service.py`
- `cli.py` is now a thin Typer shell over `cli_service.py`
- startup validation is explicit instead of piggybacking on agent creation side effects
- filesystem execution and discovery now follow a runtime-owned service path
- session recording/loading now centers on `sessions/service.py`
- low-value facades and global mutable public surfaces were deleted instead of preserved

This reshape is the new baseline for the next cc-core upgrades.

## Upgrade gate

Advance by explicit product-stage plan approval, not tutorial chapter completion.

## Stage roadmap

1. Stage 1: TodoWrite / todos / activeForm product contract
2. Stage 2: architecture gate for filesystem/tool-system/session seams
3. Stage 3: professional domain runtime foundation with typed settings, DI composition, Typer/Rich CLI, runtime context, sessions, filesystem/tool_system, and local events
4. Stage 4: control-plane foundation (permissions, hooks, structured prompt/context)
5. Stage 5: memory/context/compact foundation
6. Stage 6: skills/subagents/durable task graph
7. Stage 7: local MCP/plugin extension foundation
8. Stage 8: recovery/evidence/runtime-continuation foundation
9. Stage 9: permission/trust-boundary hardening
10. Stage 10: hooks/lifecycle expansion
11. Stage 11: MCP/plugin real loading

## Abstraction checkpoint

Before implementing the next stage, re-evaluate whether the current domain packages and containers still preserve the boundary rules in `.trellis/plans/prd-coding-deepgent-runtime-foundation.md`.

## Renderer boundary note

The current product has a dependency-free planning renderer seam for terminal plan/reminder output. This is a behavior-preserving boundary, not a browser/API/event-bus implementation.

## Stage 4 control-plane foundation

Stage 4 adds deterministic permission/safety decisions, local lifecycle hooks, and structured prompt/context assembly as LangChain-native seams over the existing `create_agent` runtime. Interactive UI approval, auto classifiers, memory, durable tasks, subagents, and MCP/plugin loading remain future stages.

## Stage 5 memory/context/compact foundation

Stage 5 adds a store-backed long-term memory foundation seam, the model-visible `save_memory` tool, bounded memory context injection, and deterministic tool-result budget helpers. Message-history projection/pruning, LLM autocompact, session-memory side-agent writing, subagents, durable tasks, and MCP/plugin memory sync remain future work.

## Stage 6 skills/subagents/task graph

Stage 6 adds local skill loading, a store-backed durable task graph, and a minimal synchronous/stateless `run_subagent` tool. Background agents, SendMessage/mailbox, worktrees, remote/team runtime, sidechain resume, forked skill execution, extension distribution, and custom query loops remain future work.

## Stage 7 MCP/plugin extension foundation

Stage 7 adds local-only extension seams: MCP tool descriptors can become agent-bindable `ToolCapability` entries, MCP resources remain separate metadata/read surfaces, and strict local `plugin.json` manifests declare local tools, skills, and resources without executing plugin code. Connection management, installer/update flows, remote trust, background daemons, and runtime replacement remain deferred.


## Stage 8 recovery/evidence/runtime-continuation foundation

Stage 8 adds session-scoped evidence records, loaded-session evidence, a deterministic recovery brief, and default CLI session-store wiring for listing and resuming recorded sessions. It preserves LangChain `create_agent`/LangGraph `thread_id` runtime boundaries and defers checkpoint browsers, task-level evidence stores, mailbox/background resume, and new persistence dependencies.


## Stage 9 permission/trust-boundary hardening

Stage 9 hardens the existing permission runtime with typed settings-backed rules, explicit trusted extra workspace directories, and builtin/extension capability trust metadata. It stays deterministic and local-only: no HITL UI, no remote trust flow, no marketplace/install/update behavior, and no runtime replacement.


## Stage 10 hooks/lifecycle expansion

Stage 10 wires the local sync hook registry into real runtime boundaries: `SessionStart` and `UserPromptSubmit` run from the app invocation path, while `PreToolUse`, `PostToolUse`, and `PermissionDenied` run from tool middleware. Hooks remain deterministic and local-only: no async/plugin/HTTP/remote hook platform and no model-visible prompt mutation from hook context.


## Stage 11 MCP/plugin real loading

Stage 11 adds typed root `.mcp.json` loading, an optional official adapter-backed MCP tool loading seam, and plugin declaration validation against known local capabilities/skills. It still defers dependency installation, marketplace/install/update, remote trust/auth UX, and runtime replacement.
