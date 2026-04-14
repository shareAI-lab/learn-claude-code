# s01: The Agent Loop

`[ s01 ] > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

## What You'll Learn

- How the core agent loop works: send messages, run tools, feed results back
- Why the "write-back" step is the single most important idea in agent design
- How to build a working agent in under 30 lines of Python

Imagine you have a brilliant assistant who can reason about code, plan solutions, and write great answers -- but cannot touch anything. Every time it suggests running a command, you have to copy it, run it yourself, paste the output back, and wait for the next suggestion. You are the loop. This chapter removes you from that loop.

## The Problem

Without a loop, every tool call requires a human in the middle. The model says "run this test." You run it. You paste the output. The model says "now fix line 12." You fix it. You tell the model what happened. This manual back-and-forth might work for a single question, but it falls apart completely when a task requires 10, 20, or 50 tool calls in a row.

The solution is simple: let the code do the looping.

## The Solution

Here's the entire system in one picture:

```
+--------+      +-------+      +---------+
|  User  | ---> |  LLM  | ---> |  Tool   |
| prompt |      |       |      | execute |
+--------+      +---+---+      +----+----+
                    ^                |
                    |   tool_result  |
                    +----------------+
                    (loop until the model stops calling tools)
```

The model talks, the harness (the code wrapping the model) executes tools, and the results go right back into the conversation. The loop keeps spinning until the model decides it's done.

## How It Works

**Step 1.** The user's prompt becomes the first message.

```python
messages.append({"role": "user", "content": query})
```

**Step 2.** Send the conversation to the model, along with tool definitions.

```python
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
```

**Step 3.** Add the model's response to the conversation. Then check: did it call a tool, or is it done?

```python
messages.append({"role": "assistant", "content": response.content})

# If the model didn't call a tool, the task is finished
if response.stop_reason != "tool_use":
    return
```

**Step 4.** Execute each tool call, collect the results, and put them back into the conversation as a new message. Then loop back to Step 2.

```python
results = []
for block in response.content:
    if block.type == "tool_use":
        output = run_bash(block.input["command"])
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,  # links result to the tool call
            "content": output,
        })
# This is the "write-back" -- the model can now see the real-world result
messages.append({"role": "user", "content": results})
```

Put it all together, and the entire agent fits in one function:

```python
def agent_loop(query):
    messages = [{"role": "user", "content": query}]
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return  # model is done

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_bash(block.input["command"])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})
```

That's the entire agent in under 30 lines. Everything else in this course layers on top of this loop -- without changing its core shape.

> **A note about real systems:** Production agents typically use streaming responses, where the model's output arrives token by token instead of all at once. That changes the user experience (you see text appearing in real time), but the fundamental loop -- send, execute, write back -- stays exactly the same. We skip streaming here to keep the core idea crystal clear.

## What Changed

| Component     | Before     | After                          |
|---------------|------------|--------------------------------|
| Agent loop    | (none)     | `while True` + stop_reason     |
| Tools         | (none)     | `bash` (one tool)              |
| Messages      | (none)     | Accumulating list              |
| Control flow  | (none)     | `stop_reason != "tool_use"`    |

## Try It

```sh
cd learn-claude-code
python agents/s01_agent_loop.py
```

1. `Create a file called hello.py that prints "Hello, World!"`
2. `List all Python files in this directory`
3. `What is the current git branch?`
4. `Create a directory called test_output and write 3 files in it`

## What You've Mastered

At this point, you can:

- Build a working agent loop from scratch
- Explain why tool results must flow back into the conversation (the "write-back")
- Redraw the loop from memory: messages -> model -> tool execution -> write-back -> next turn

## What's Next

Right now, the agent can only run bash commands. That means every file read uses `cat`, every edit uses `sed`, and there's no safety boundary at all. In the next chapter, you'll add dedicated tools with a clean routing system -- and the loop itself won't need to change at all.

## Key Takeaway

> An agent is just a loop: send messages to the model, execute the tools it asks for, feed the results back, and repeat until it's done.
