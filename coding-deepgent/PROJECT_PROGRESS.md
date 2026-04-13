# coding-deepgent progress

## Current product stage

- `current_product_stage`: `stage-6-skills-subagents-task-graph`
- `compatibility_anchor`: `skills-subagents-task-graph`
- Status: control-plane foundation implemented as one cumulative LangChain cc product surface
- Last updated: 2026-04-12

## Upgrade gate

Advance by explicit product-stage plan approval, not tutorial chapter completion.

## Stage roadmap

1. Stage 1: TodoWrite / todos / activeForm product contract
2. Stage 2: architecture gate for filesystem/tool-system/session seams
3. Stage 3: professional domain runtime foundation with typed settings, DI composition, Typer/Rich CLI, runtime context, sessions, filesystem/tool_system, and local events
4. Stage 4: control-plane foundation (permissions, hooks, structured prompt/context)
5. Stage 5+: memory, compact, MCP, subagents, recovery, durable tasks, and teams

## Abstraction checkpoint

Before implementing the next stage, re-evaluate whether the current domain packages and containers still preserve the boundary rules in `.omx/plans/prd-coding-deepgent-runtime-foundation.md`.

## Renderer boundary note

The current product has a dependency-free planning renderer seam for terminal plan/reminder output. This is a behavior-preserving boundary, not a browser/API/event-bus implementation.

## Stage 4 control-plane foundation

Stage 4 adds deterministic permission/safety decisions, local lifecycle hooks, and structured prompt/context assembly as LangChain-native seams over the existing `create_agent` runtime. Interactive UI approval, auto classifiers, memory, durable tasks, subagents, and MCP/plugin loading remain future stages.

## Stage 5 memory/context/compact foundation

Stage 5 adds a store-backed long-term memory foundation seam, the model-visible `save_memory` tool, bounded memory context injection, and deterministic tool-result budget helpers. Message-history projection/pruning, LLM autocompact, session-memory side-agent writing, subagents, durable tasks, and MCP/plugin memory sync remain future work.

## Stage 6 skills/subagents/task graph

Stage 6 adds local skill loading, a store-backed durable task graph, and a minimal synchronous/stateless `run_subagent` tool. Background agents, SendMessage/mailbox, worktrees, remote/team runtime, sidechain resume, forked skill execution, MCP/plugin marketplace, and custom query loops remain future work.
