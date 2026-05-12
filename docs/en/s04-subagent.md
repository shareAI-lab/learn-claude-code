# s04: Subagents

`s01 > s02 > s03 > [ s04 ] > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

## What You'll Learn
- Why exploring a side question can pollute the parent agent's context
- How a subagent gets a fresh, empty message history
- How only a short summary travels back to the parent
- Why the child's full message history is discarded after use

Imagine you ask your agent "What testing framework does this project use?" To answer, it reads five files, parses config blocks, and compares import statements. All of that exploration is useful for a moment -- but once the answer is "pytest," you really don't want those five file dumps sitting in the conversation forever. Every future API call now carries that dead weight, burning tokens and distracting the model. You need a way to ask a side question in a clean room and bring back only the answer.

## The Problem

As the agent works, its `messages` array grows. Every file read, every bash output stays in context permanently. A simple question like "what testing framework is this?" might require reading five files, but the parent only needs one word back: "pytest." Without isolation, those intermediate artifacts stay in context for the rest of the session, wasting tokens on every subsequent API call and muddying the model's attention. The longer a session runs, the worse this gets -- context fills with exploration debris that has nothing to do with the current task.

## The Solution

The parent agent delegates side tasks to a child agent that starts with an empty `messages=[]`. The child does all the messy exploration, then only its final text summary travels back. The child's full history is discarded.

```
Parent agent                     Subagent
+------------------+             +------------------+
| messages=[...]   |             | messages=[]      | <-- fresh
|                  |  dispatch   |                  |
| tool: task       | ----------> | while tool_use:  |
|   prompt="..."   |             |   call tools     |
|                  |  summary    |   append results |
|   result = "..." | <---------- | return last text |
+------------------+             +------------------+

Parent context stays clean. Subagent context is discarded.
```

## How It Works

**Step 1.** The parent gets a `task` tool that the child does not. This prevents recursive spawning -- a child cannot create its own children.

```python
PARENT_TOOLS = CHILD_TOOLS + [
    {"name": "task",
     "description": "Spawn a subagent with fresh context.",
     "input_schema": {
         "type": "object",
         "properties": {"prompt": {"type": "string"}},
         "required": ["prompt"],
     }},
]
```

**Step 2.** The subagent starts with `messages=[]` and runs its own agent loop. Only the final text block returns to the parent as a `tool_result`.

```python
def run_subagent(prompt: str) -> str:
    sub_messages = [{"role": "user", "content": prompt}]
    for _ in range(30):  # safety limit
        response = client.messages.create(
            model=MODEL, system=SUBAGENT_SYSTEM,
            messages=sub_messages,
            tools=CHILD_TOOLS, max_tokens=8000,
        )
        sub_messages.append({"role": "assistant",
                             "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                output = handler(**block.input)
                results.append({"type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(output)[:50000]})
        sub_messages.append({"role": "user", "content": results})
    # Extract only the final text -- everything else is thrown away
    return "".join(
        b.text for b in response.content if hasattr(b, "text")
    ) or "(no summary)"
```

The child's entire message history (possibly 30+ tool calls worth of file reads and bash outputs) is discarded the moment `run_subagent` returns. The parent receives a one-paragraph summary as a normal `tool_result`, keeping its own context clean.

## What Changed From s03

| Component      | Before (s03)     | After (s04)               |
|----------------|------------------|---------------------------|
| Tools          | 5                | 5 (base) + task (parent)  |
| Context        | Single shared    | Parent + child isolation  |
| Subagent       | None             | `run_subagent()` function |
| Return value   | N/A              | Summary text only         |

## Try It

```sh
cd learn-claude-code
python agents/s04_subagent.py
```

1. `Use a subtask to find what testing framework this project uses`
2. `Delegate: read all .py files and summarize what each one does`
3. `Use a task to create a new module, then verify it from here`

## What You've Mastered

At this point, you can:

- Explain why a subagent is primarily a **context boundary**, not a process trick
- Spawn a one-shot child agent with a fresh `messages=[]`
- Return only a summary to the parent, discarding all intermediate exploration
- Decide which tools the child should and should not have access to

You don't need long-lived workers, resumable sessions, or worktree isolation yet. The core idea is simple: give the subtask a clean workspace in memory, then bring back only the answer the parent still needs.

## What's Next

So far you've learned to keep context clean by isolating side tasks. But what about the knowledge the agent carries in the first place? In s05, you'll see how to avoid bloating the system prompt with domain expertise the model might never use -- loading skills on demand instead of upfront.

## Key Takeaway

> A subagent is a disposable scratch pad: fresh context in, short summary out, everything else discarded.
