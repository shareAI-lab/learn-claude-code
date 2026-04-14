# s00b: One Request Lifecycle

> **Deep Dive** -- Best read after Stage 2 (s07-s11) when you want to see how all the pieces connect end-to-end.

### When to Read This

When you've learned several subsystems and want to see the full vertical flow of a single request.

---

> This bridge document connects the whole system into one continuous execution chain.
>
> It answers:
>
> **What really happens after one user message enters the system?**

## Why This Document Exists

When you read chapter by chapter, you can understand each mechanism in isolation:

- `s01` loop
- `s02` tools
- `s07` permissions
- `s09` memory
- `s12-s19` tasks, teams, worktrees, MCP

But implementation gets difficult when you cannot answer:

- what comes first?
- when do memory and prompt assembly happen?
- where do permissions sit relative to tools?
- when do tasks, runtime slots, teammates, worktrees, and MCP enter?

This document gives you the vertical flow.

## The Most Important Full Picture

```text
user request
  |
  v
initialize query state
  |
  v
assemble system prompt / messages / reminders
  |
  v
call model
  |
  +-- normal answer --------------------------> finish request
  |
  +-- tool_use
        |
        v
    tool router
        |
        +-- permission gate
        +-- hooks
        +-- native tool / MCP / agent / task / team
        |
        v
    execution result
        |
        +-- may update task / runtime / memory / worktree state
        |
        v
    write tool_result back to messages
        |
        v
    patch query state
        |
        v
    continue next turn
```

## Segment 1: A User Request Becomes Query State

The system does not treat one user request as one API call.

It first creates a query state for a process that may span many turns:

```python
query_state = {
    "messages": [{"role": "user", "content": user_text}],
    "turn_count": 1,
    "transition": None,
    "tool_use_context": {...},
}
```

The key mental shift:

**a request is a multi-turn runtime process, not a single model response.**

Related reading:

- [`s01-the-agent-loop.md`](./s01-the-agent-loop.md)
- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)

## Segment 2: The Real Model Input Is Assembled

The harness usually does not send raw `messages` directly.

It assembles:

- system prompt blocks
- normalized messages
- memory attachments
- reminders
- tool definitions

So the actual payload is closer to:

```text
system prompt
+ normalized messages
+ tools
+ optional reminders and attachments
```

Related chapters:

- `s09`
- `s10`
- [`s10a-message-prompt-pipeline.md`](./s10a-message-prompt-pipeline.md)

## Segment 3: The Model Produces Either an Answer or an Action Intent

There are two important output classes.

### Normal answer

The request may end here.

### Action intent

This usually means a tool call, for example:

- `read_file(...)`
- `bash(...)`
- `task_create(...)`
- `mcp__server__tool(...)`

The system is no longer receiving only text.

It is receiving an instruction that should affect the real world.

## Segment 4: The Tool Control Plane Takes Over

Once `tool_use` appears, the system enters the tool control plane (the layer that decides how a tool call gets routed, checked, and executed).

It answers:

1. which tool is this?
2. where should it route?
3. should it pass a permission gate?
4. do hooks observe or modify the action?
5. what shared runtime context can it access?

Minimal picture:

```text
tool_use
  |
  v
tool router
  |
  +-- native handler
  +-- MCP client
  +-- agent / team / task runtime
```

Related reading:

- [`s02-tool-use.md`](./s02-tool-use.md)
- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)

## Segment 5: Execution May Update More Than Messages

A tool result does not only return text.

Execution may also update:

- task board state
- runtime task state
- memory records
- request records
- worktree records

That is why middle and late chapters are not optional side features. They become part of the request lifecycle.

## Segment 6: Results Rejoin the Main Loop

The crucial step is always the same:

```text
real execution result
  ->
tool_result or structured write-back
  ->
messages / query state updated
  ->
next turn
```

If the result never re-enters the loop, the model cannot reason over reality.

## A Useful Compression

When you get lost, compress the whole lifecycle into three layers:

### Query loop

Owns the multi-turn request process.

### Tool control plane

Owns routing, permissions, hooks, and execution context.

### Platform state

Owns durable records such as tasks, runtime slots, teammates, worktrees, and external capability configuration.

## Key Takeaway

**A user request enters as query state, moves through assembled input, becomes action intent, crosses the tool control plane, touches platform state, and then returns to the loop as new visible context.**
