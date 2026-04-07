# s02b: Tool Execution Runtime

> **Deep Dive** -- Best read after s02, when you want to understand concurrent tool execution.

### When to Read This

When you start wondering how multiple tool calls in one turn get executed safely.

---

> This bridge note is not about how tools are registered.
>
> It is about a deeper question:
>
> **When the model emits multiple tool calls, what rules decide concurrency, progress updates, result ordering, and context merging?**

## Why This Note Exists

`s02` correctly teaches:

- tool schema
- dispatch map
- `tool_result` flowing back into the loop

That is the right starting point.

But once the system grows, the hard questions move one layer deeper:

- which tools can run in parallel
- which tools should stay serial
- whether long-running tools should emit progress first
- whether concurrent results should write back in completion order or original order
- whether tool execution mutates shared context
- how concurrent mutations should merge safely

Those questions are not about registration anymore.

They belong to the **tool execution runtime** -- the set of rules the system follows once tool calls actually start executing, including scheduling, tracking, yielding progress, and merging results.

## Terms First

### What "tool execution runtime" means here

This is not the programming language runtime.

Here it means:

> the rules the system uses once tool calls actually start executing

Those rules include scheduling, tracking, yielding progress, and merging results.

### What "concurrency safe" means

A tool is concurrency safe when:

> it can run alongside similar work without corrupting shared state

Typical read-only tools are often safe:

- `read_file`
- some search tools
- query-only MCP tools

Many write tools are not:

- `write_file`
- `edit_file`
- tools that modify shared application state

### What a progress message is

A progress message means:

> the tool is not done yet, but the system already surfaces what it is doing

This keeps the user informed during long-running operations rather than leaving them staring at silence.

### What a context modifier is

Some tools do more than return text.

They also modify shared runtime context, for example:

- update a notification queue
- record active tools
- mutate app state

That shared-state mutation is called a context modifier.

## The Minimum Mental Model

Do not flatten tool execution into:

```text
tool_use -> handler -> result
```

A better mental model is:

```text
tool_use blocks
  ->
partition by concurrency safety
  ->
choose concurrent or serial execution
  ->
emit progress if needed
  ->
write results back in stable order
  ->
merge queued context modifiers
```

Two upgrades matter most:

- concurrency is not "all tools run together"
- shared context should not be mutated in random completion order

## Core Records

### 1. `ToolExecutionBatch`

A minimal teaching batch can look like:

```python
batch = {
    "is_concurrency_safe": True,
    "blocks": [tool_use_1, tool_use_2, tool_use_3],
}
```

The point is simple:

- tools are not always handled one by one
- the runtime groups them into execution batches first

### 2. `TrackedTool`

If you want a higher-completion execution layer, track each tool explicitly:

```python
tracked_tool = {
    "id": "toolu_01",
    "name": "read_file",
    "status": "queued",   # queued / executing / completed / yielded
    "is_concurrency_safe": True,
    "pending_progress": [],
    "results": [],
    "context_modifiers": [],
}
```

This makes the runtime able to answer:

- what is still waiting
- what is already running
- what has completed
- what has already yielded progress

### 3. `MessageUpdate`

Tool execution may produce more than one final result.

A minimal update can be treated as:

```python
update = {
    "message": maybe_message,
    "new_context": current_context,
}
```

In a larger runtime, updates usually split into two channels:

- messages that should surface upstream immediately
- context changes that should stay internal until merge time

### 4. Queued context modifiers

This is easy to skip, but it is one of the most important ideas.

In a concurrent batch, the safer strategy is not:

> "whichever tool finishes first mutates shared context first"

The safer strategy is:

> queue context modifiers first, then merge them later in the original tool order

For example:

```python
queued_context_modifiers = {
    "toolu_01": [modify_ctx_a],
    "toolu_02": [modify_ctx_b],
}
```

## Minimum Implementation Steps

### Step 1: classify concurrency safety

```python
def is_concurrency_safe(tool_name: str, tool_input: dict) -> bool:
    return tool_name in {"read_file", "search_files"}
```

### Step 2: partition before execution

```python
batches = partition_tool_calls(tool_uses)

for batch in batches:
    if batch["is_concurrency_safe"]:
        run_concurrently(batch["blocks"])
    else:
        run_serially(batch["blocks"])
```

### Step 3: let concurrent batches emit progress

```python
for update in run_concurrently(...):
    if update.get("message"):
        yield update["message"]
```

### Step 4: merge context in stable order

```python
queued_modifiers = {}

for update in concurrent_updates:
    if update.get("context_modifier"):
        queued_modifiers[update["tool_id"]].append(update["context_modifier"])

for tool in original_batch_order:
    for modifier in queued_modifiers.get(tool["id"], []):
        context = modifier(context)
```

This is one of the places where a teaching repo can still stay simple while remaining honest about the real system shape.

## The Picture You Should Hold

```text
tool_use blocks
  |
  v
partition by concurrency safety
  |
  +-- safe batch ----------> concurrent execution
  |                            |
  |                            +-- progress updates
  |                            +-- final results
  |                            +-- queued context modifiers
  |
  +-- exclusive batch -----> serial execution
                               |
                               +-- direct result
                               +-- direct context update
```

## Why This Matters More Than the Dispatch Map

In a tiny demo:

```python
handlers[tool_name](tool_input)
```

is enough.

But in a higher-completion agent, the hard part is no longer calling the right handler.

The hard part is:

- scheduling multiple tools safely
- keeping progress visible
- making result ordering stable
- preventing shared context from becoming nondeterministic

That is why tool execution runtime deserves its own deep dive.

## Key Takeaway

**Once the model emits multiple tool calls per turn, the hard problem shifts from dispatch to safe concurrent execution with stable result ordering.**
