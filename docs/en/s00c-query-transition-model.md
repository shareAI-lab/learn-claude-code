# s00c: Query Transition Model

> **Deep Dive** -- Best read alongside s11 (Error Recovery). It deepens the transition model introduced in s00a.

### When to Read This

When you're working on error recovery and want to understand why each continuation needs an explicit reason.

---

> This bridge note answers one narrow but important question:
>
> **Why does a high-completion agent need to know _why_ a query continues into the next turn, instead of treating every `continue` as the same thing?**

## Why This Note Exists

The mainline already teaches:

- `s01`: the smallest loop
- `s06`: compaction and context control
- `s11`: error recovery

That sequence is correct.

The problem is what you often carry in your head after reading those chapters separately:

> "The loop continues because it continues."

That is enough for a toy demo, but it breaks down quickly in a larger system.

A query can continue for very different reasons:

- a tool just finished and the model needs the result
- the output hit a token limit and the model should continue
- compaction changed the active context and the system should retry
- the transport layer failed and backoff says "try again"
- a stop hook said the turn should not fully end yet
- a budget policy still allows the system to keep going

If all of those collapse into one vague `continue`, three things get worse fast:

- logs stop being readable
- tests stop being precise
- the teaching mental model becomes blurry

## Terms First

### What is a transition

Here, a transition means:

> the reason the previous turn became the next turn

It is not the message content itself. It is the control-flow cause.

### What is a continuation

A continuation means:

> this query is still alive and should keep advancing

But continuation is not one thing. It is a family of reasons.

### What is a query boundary

A query boundary is the edge between one turn and the next.

Whenever the system crosses that boundary, it should know:

- why it is crossing
- what state was changed before the crossing
- how the next turn should interpret that change

## The Minimum Mental Model

Do not picture a query as a single straight line.

A better mental model is:

```text
one query
  = a chain of state transitions
    with explicit continuation reasons
```

For example:

```text
user input
  ->
model emits tool_use
  ->
tool finishes
  ->
tool_result_continuation
  ->
model output is truncated
  ->
max_tokens_recovery
  ->
compaction happens
  ->
compact_retry
  ->
final completion
```

That is why the real lesson is not:

> "the loop keeps spinning"

The real lesson is:

> "the system is advancing through typed transition reasons"

## Core Records

### 1. `transition` inside query state

Even a teaching implementation should carry an explicit transition field:

```python
state = {
    "messages": [...],
    "turn_count": 3,
    "continuation_count": 1,
    "has_attempted_compact": False,
    "transition": None,
}
```

This field is not decoration.

It tells you:

- why this turn exists
- how the log should explain it
- what path a test should assert

### 2. `TransitionReason`

A minimal teaching set can look like this:

```python
TRANSITIONS = (
    "tool_result_continuation",
    "max_tokens_recovery",
    "compact_retry",
    "transport_retry",
    "stop_hook_continuation",
    "budget_continuation",
)
```

These reasons are not equivalent:

- `tool_result_continuation`
  is normal loop progress
- `max_tokens_recovery`
  is continuation after truncated output
- `compact_retry`
  is continuation after context reshaping
- `transport_retry`
  is continuation after infrastructure failure
- `stop_hook_continuation`
  is continuation forced by external control logic
- `budget_continuation`
  is continuation allowed by policy and remaining budget

### 3. Continuation budget

High-completion systems do not just continue. They limit continuation.

Typical fields look like:

```python
state = {
    "max_output_tokens_recovery_count": 2,
    "has_attempted_reactive_compact": True,
}
```

The principle is:

> continuation is a controlled resource, not an infinite escape hatch

## Minimum Implementation Steps

### Step 1: make every continue site explicit

Many beginner loops still look like this:

```python
continue
```

Move one step forward:

```python
state["transition"] = "tool_result_continuation"
continue
```

### Step 2: pair each continuation with its state patch

```python
if response.stop_reason == "tool_use":
    state["messages"] = append_tool_results(...)
    state["turn_count"] += 1
    state["transition"] = "tool_result_continuation"
    continue

if response.stop_reason == "max_tokens":
    state["messages"].append({
        "role": "user",
        "content": CONTINUE_MESSAGE,
    })
    state["max_output_tokens_recovery_count"] += 1
    state["transition"] = "max_tokens_recovery"
    continue
```

The important part is not "one more line of code."

The important part is:

> before every continuation, the system knows both the reason and the state mutation

### Step 3: separate normal progress from recovery

```python
if should_retry_transport(error):
    time.sleep(backoff(...))
    state["transition"] = "transport_retry"
    continue

if should_recompact(error):
    state["messages"] = compact_messages(state["messages"])
    state["transition"] = "compact_retry"
    continue
```

Once you do this, "continue" stops being a vague action and becomes a typed control transition.

## What to Test

Your teaching repo should make these assertions straightforward:

- a tool result writes `tool_result_continuation`
- a truncated model output writes `max_tokens_recovery`
- compaction retry does not silently reuse the old reason
- transport retry increments retry state and does not look like a normal turn

If those paths are not easy to test, the model is probably still too implicit.

## What Not to Over-Teach

You do not need to bury yourself in vendor-specific transport details or every corner-case enum.

For a teaching repo, the core lesson is narrower:

> one query is a sequence of explicit transitions, and each transition should carry a reason, a state patch, and a budget rule

That is the part you actually need if you want to rebuild a high-completion agent from zero.

## Key Takeaway

**Every continuation needs a typed reason. Without one, logs blur, tests weaken, and the mental model collapses into "the loop keeps spinning."**
