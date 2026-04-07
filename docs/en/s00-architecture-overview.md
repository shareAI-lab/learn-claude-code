# s00: Architecture Overview

Welcome to the map. Before diving into building piece by piece, it helps to see the whole picture from above. This document shows you what the full system contains, why the chapters are ordered this way, and what you will actually learn.

## The Big Picture

The mainline of this repo is reasonable because it grows the system in four dependency-driven stages:

1. build a real single-agent loop
2. harden that loop with safety, memory, and recovery
3. turn temporary session work into durable runtime work
4. grow the single executor into a multi-agent platform with isolated lanes and external capability routing

This order follows **mechanism dependencies**, not file order and not product glamour.

If the learner does not already understand:

`user input -> model -> tools -> write-back -> next turn`

then permissions, hooks, memory, tasks, teams, worktrees, and MCP all become disconnected vocabulary.

## What This Repo Is Trying To Reconstruct

This repository is not trying to mirror a production codebase line by line.

It is trying to reconstruct the parts that determine whether an agent system actually works:

- what the main modules are
- how those modules cooperate
- what each module is responsible for
- where the important state lives
- how one request flows through the system

That means the goal is:

**high fidelity to the design backbone, not 1:1 fidelity to every outer implementation detail.**

## Three Tips Before You Start

### Tip 1: Learn the smallest correct version first

For example, a subagent does not need every advanced capability on day one.

The smallest correct version already teaches the core lesson:

- the parent defines the subtask
- the child gets a separate `messages[]`
- the child returns a summary

Only after that is stable should you add:

- inherited context
- separate permissions
- background runtime
- worktree isolation

### Tip 2: New terms should be explained before they are used

This repo uses terms such as:

- state machine
- dispatch map
- dependency graph
- worktree
- protocol envelope
- MCP

If a term is unfamiliar, pause and check the reference docs rather than pushing forward blindly.

Recommended companions:

- [`glossary.md`](./glossary.md)
- [`entity-map.md`](./entity-map.md)
- [`data-structures.md`](./data-structures.md)
- [`teaching-scope.md`](./teaching-scope.md)

### Tip 3: Do not let peripheral complexity pretend to be core mechanism

Good teaching does not try to include everything.

It explains the important parts completely and keeps low-value complexity out of your way:

- packaging and release flow
- enterprise integration glue
- telemetry
- product-specific compatibility branches
- file-name / line-number reverse-engineering trivia

## Bridge Docs That Matter

Treat these as cross-chapter maps:

| Doc | What It Clarifies |
|---|---|
| [`s00d-chapter-order-rationale.md`](./s00d-chapter-order-rationale.md) (Deep Dive) | why the curriculum order is what it is |
| [`s00e-reference-module-map.md`](./s00e-reference-module-map.md) (Deep Dive) | how the reference repo's real module clusters map onto the current curriculum |
| [`s00a-query-control-plane.md`](./s00a-query-control-plane.md) (Deep Dive) | why a high-completion agent needs more than `messages[] + while True` |
| [`s00b-one-request-lifecycle.md`](./s00b-one-request-lifecycle.md) (Deep Dive) | how one request moves through the full system |
| [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md) (Deep Dive) | why tools become a control plane, not just a function table |
| [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md) (Deep Dive) | why system prompt is only one input surface |
| [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) (Deep Dive) | why durable tasks and live runtime slots must split |
| [`s19a-mcp-capability-layers.md`](./s19a-mcp-capability-layers.md) (Deep Dive) | why MCP is more than a remote tool list |

## The Four Learning Stages

### Stage 1: Core Single-Agent (`s01-s06`)

Goal: build a single agent that can actually do work.

| Chapter | New Layer |
|---|---|
| `s01` | loop and write-back |
| `s02` | tools and dispatch |
| `s03` | session planning |
| `s04` | delegated subtask isolation |
| `s05` | skill discovery and loading |
| `s06` | context compaction |

### Stage 2: Hardening (`s07-s11`)

Goal: make the loop safer, more stable, and easier to extend.

| Chapter | New Layer |
|---|---|
| `s07` | permission gate |
| `s08` | hooks and side effects |
| `s09` | durable memory |
| `s10` | prompt assembly |
| `s11` | recovery and continuation |

### Stage 3: Runtime Work (`s12-s14`)

Goal: upgrade session work into durable, background, and scheduled runtime work.

| Chapter | New Layer |
|---|---|
| `s12` | persistent task graph |
| `s13` | runtime execution slots |
| `s14` | time-based triggers |

### Stage 4: Platform (`s15-s19`)

Goal: grow from one executor into a larger platform.

| Chapter | New Layer |
|---|---|
| `s15` | persistent teammates |
| `s16` | structured team protocols |
| `s17` | autonomous claiming and resuming |
| `s18` | isolated execution lanes |
| `s19` | external capability routing |

## Quick Reference: What Each Chapter Adds

| Chapter | Core Structure | What You Should Be Able To Build |
|---|---|---|
| `s01` | `LoopState`, `tool_result` write-back | a minimal working agent loop |
| `s02` | `ToolSpec`, dispatch map | stable tool routing |
| `s03` | `TodoItem`, `PlanState` | visible session planning |
| `s04` | isolated child context | delegated subtasks without polluting the parent |
| `s05` | `SkillRegistry` | cheap discovery and deep on-demand loading |
| `s06` | compaction records | long sessions that stay usable |
| `s07` | permission decisions | execution behind a gate |
| `s08` | lifecycle events | extension without rewriting the loop |
| `s09` | memory records | selective long-term memory |
| `s10` | prompt parts | staged input assembly |
| `s11` | continuation reasons | recovery branches that stay legible |
| `s12` | `TaskRecord` | durable work graphs |
| `s13` | `RuntimeTaskState` | background execution with later write-back |
| `s14` | `ScheduleRecord` | time-triggered work |
| `s15` | `TeamMember`, inboxes | persistent teammates |
| `s16` | protocol envelopes | structured request / response coordination |
| `s17` | claim policy | self-claim and self-resume |
| `s18` | `WorktreeRecord` | isolated execution lanes |
| `s19` | capability routing | unified native + plugin + MCP routing |

## Key Takeaway

**A good chapter order is not a list of features. It is a path where each mechanism grows naturally out of the last one.**
