# coding-deepgent progress

## Current product stage

- `current_product_stage`: `stage-4-control-plane-foundation`
- `compatibility_anchor`: `control-plane-foundation`
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
