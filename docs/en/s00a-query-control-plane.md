# s00a: Query Control Plane

> **Deep Dive** -- Best read after completing Stage 1 (s01-s06). It explains why the simple loop needs a coordination layer as the system grows.

### When to Read This

After you've built the basic loop and tools, and before you start Stage 2's hardening chapters.

---

> This bridge document answers one foundational question:
>
> **Why is `messages[] + while True` not enough for a high-completion agent?**

## Why This Document Exists

`s01` correctly teaches the smallest working loop:

```text
user input
  ->
model response
  ->
if tool_use then execute
  ->
append result
  ->
continue
```

That is the right starting point.

But once the system grows, the harness needs a separate layer that manages the **query process itself**. A "control plane" (the part of a system that coordinates behavior rather than performing the work directly) sits above the data path and decides when, why, and how the loop should keep running:

- current turn
- continuation reason
- recovery state
- compaction state
- budget changes
- hook-driven continuation

That layer is the **query control plane**.

## Terms First

### What is a query?

Here, a query is not a database lookup.

It means:

> the full multi-turn process the system runs in order to finish one user request

### What is a control plane?

A control plane does not perform the business action itself.

It coordinates:

- when execution continues
- why it continues
- what state is patched before the next turn

If you have worked with networking or infrastructure, the term is familiar -- the control plane decides where traffic goes, while the data plane carries the actual packets. The same idea applies here: the control plane decides whether the loop should keep running and why, while the execution layer does the actual model calls and tool work.

### What is a transition?

A transition explains:

> why the previous turn did not end and why the next turn exists

Common reasons:

- tool result write-back
- truncated output recovery
- retry after compaction
- retry after transport failure

## The Smallest Useful Mental Model

Think of the query path in three layers:

```text
1. Input layer
   - messages
   - system prompt
   - user/system context

2. Control layer
   - query state
   - turn count
   - transition reason
   - recovery / compaction / budget flags

3. Execution layer
   - model call
   - tool execution
   - write-back
```

The control plane does not replace the loop.

It makes the loop capable of handling more than one happy-path branch.

## Why `messages[]` Alone Stops Being Enough

At demo scale, many learners put everything into `messages[]`.

That breaks down once the system needs to know:

- whether reactive compaction already ran
- how many continuation attempts happened
- whether this turn is a retry or a normal write-back
- whether a temporary output budget is active

Those are not conversation contents.

They are **process-control state**.

## Core Structures

### `QueryParams`

External input passed into the query engine:

```python
params = {
    "messages": [...],
    "system_prompt": "...",
    "tool_use_context": {...},
    "max_output_tokens_override": None,
    "max_turns": None,
}
```

### `QueryState`

Mutable state that changes across turns:

```python
state = {
    "messages": [...],
    "tool_use_context": {...},
    "turn_count": 1,
    "continuation_count": 0,
    "has_attempted_compact": False,
    "max_output_tokens_override": None,
    "transition": None,
}
```

### `TransitionReason`

An explicit reason for continuing:

```python
TRANSITIONS = (
    "tool_result_continuation",
    "max_tokens_recovery",
    "compact_retry",
    "transport_retry",
)
```

This is not ceremony. It makes logs, testing, debugging, and teaching much clearer.

## Minimal Implementation Pattern

### 1. Split entry params from live state

```python
def query(params):
    state = {
        "messages": params["messages"],
        "tool_use_context": params["tool_use_context"],
        "turn_count": 1,
        "transition": None,
    }
```

### 2. Let every continue-site patch state explicitly

```python
state["transition"] = "tool_result_continuation"
state["turn_count"] += 1
```

### 3. Make the next turn enter with a reason

The next loop iteration should know whether it exists because of:

- normal write-back
- retry
- compaction
- continuation after truncated output

## What This Changes For You

Once you see the query control plane clearly, later chapters stop feeling like random features.

- `s06` compaction becomes a state patch, not a magic jump
- `s11` recovery becomes structured continuation, not just `try/except`
- `s17` autonomy becomes another controlled continuation path, not a separate mystery loop

## Key Takeaway

**A query is not just messages flowing through a loop. It is a controlled process with explicit continuation state.**
