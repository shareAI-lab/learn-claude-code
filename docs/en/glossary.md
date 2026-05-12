# Glossary

> **Reference** -- Bookmark this page. Come back whenever you hit an unfamiliar term.

This glossary collects the terms that matter most to the teaching mainline -- the ones that most often trip up beginners. If you find yourself staring at a word mid-chapter and thinking "wait, what does that mean again?", this is the page to return to.

## Recommended Companion Docs

- [`entity-map.md`](./entity-map.md) for layer boundaries
- [`data-structures.md`](./data-structures.md) for record shapes
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) if you keep mixing up different kinds of "task"

## Agent

A model that can reason over input and call tools to complete work. (Think of it as the "brain" that decides what to do next.)

## Harness

The working environment prepared around the model -- everything the model needs but cannot provide for itself:

- tools
- filesystem
- permissions
- prompt assembly
- memory
- task runtime

## Agent Loop

The repeating core cycle that drives every agent session. Each iteration looks like this:

1. send current input to the model
2. inspect whether it answered or asked for tools
3. execute tools if needed
4. write results back
5. continue or stop

## Message / `messages[]`

The visible conversation and tool-result history used as working context. (This is the rolling transcript the model sees on every turn.)

## Tool

An action the model may request, such as reading a file, writing a file, editing content, or running a shell command.

## Tool Schema

The description shown to the model:

- name
- purpose
- input parameters
- input types

## Dispatch Map

A routing table from tool names to handlers. (Like a phone switchboard: the name comes in, and the map connects it to the right function.)

## Stop Reason

Why the current model turn ended. Common values:

- `end_turn`
- `tool_use`
- `max_tokens`

## Context

The total information currently visible to the model. (Everything inside the model's "window" on a given turn.)

## Compaction

The process of shrinking active context while preserving the important storyline and next-step information. (Like summarizing meeting notes so you keep the action items but drop the small talk.)

## Subagent

A one-shot delegated worker that runs in a separate context and usually returns a summary. (A temporary helper spun up for one job, then discarded.)

## Permission

The decision layer that determines whether a requested action may execute.

## Hook

An extension point that lets the system observe or add side effects around the loop without rewriting the loop itself. (Like event listeners -- the loop fires a signal, and hooks respond.)

## Memory

Cross-session information worth keeping because it remains valuable later and is not cheap to re-derive.

## System Prompt

The stable system-level instruction surface that defines identity, rules, and long-lived constraints.

## Query

The full multi-turn process used to complete one user request. (One query may span many loop turns before the answer is ready.)

## Transition Reason

The reason the system continues into another turn.

## Task

A durable work goal node in the work graph. (Unlike a todo item that disappears when the session ends, a task persists.)

## Runtime Task / Runtime Slot

A live execution slot representing something currently running. (The task says "what should happen"; the runtime slot says "it is happening right now.")

## Teammate

A persistent collaborator inside a multi-agent system. (Unlike a subagent that is fire-and-forget, a teammate sticks around.)

## Protocol Request

A structured request with explicit identity, status, and tracking, usually backed by a `request_id`. (A formal envelope rather than a casual message.)

## Worktree

An isolated execution directory lane used so parallel work does not collide. (Each lane gets its own copy of the workspace, like separate desks for separate tasks.)

## MCP

Model Context Protocol. In this repo it represents an external capability integration surface, not only a tool list. (The bridge that lets your agent talk to outside services.)

## DAG

Directed Acyclic Graph. A set of nodes connected by one-way edges with no cycles. (If you draw arrows between tasks showing "A must finish before B", and no arrow path ever loops back to where it started, you have a DAG.) Used in this repo for task dependency graphs.

## FSM / State Machine

Finite State Machine. A system that is always in exactly one state from a known set, and transitions between states based on defined events. (Think of a traffic light cycling through red, green, and yellow.) The agent loop's turn logic is modeled as a state machine.

## Control Plane

The layer that decides what should happen next, as opposed to the layer that actually does the work. (Air traffic control versus the airplane.) In this repo, the query engine and tool dispatch act as control planes.

## Tokens

The atomic units a language model reads and writes. One token is roughly 3/4 of an English word. Context limits and compaction thresholds are measured in tokens.
