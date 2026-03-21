# s01: The Agent Loop

`[ s01 ] s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"One loop & Bash is all you need"* -- one tool + one loop = an agent.
>
> **Harness layer**: The loop -- the model's first connection to the real world.

## Problem

A language model can reason about code, but it can't *touch* the real world -- can't read files, run tests, or check errors. Without a loop, every tool call requires you to manually copy-paste results back. You become the loop.

## Solution

```
+--------+      +-------+      +---------+
|  User  | ---> |  LLM  | ---> |  Tool   |
| prompt |      |       |      | execute |
+--------+      +---+---+      +----+----+
                    ^                |
                    |   tool_result  |
                    +----------------+
                    (loop until stop_reason != "tool_use")
```

One exit condition controls the entire flow. The loop runs until the model stops calling tools.

## How It Works

1. User prompt becomes the first message.

```python
# Start the conversation with the user's request.
# The model only sees what we store in `messages`.
messages.append({"role": "user", "content": query})
```

2. Send messages + tool definitions to the LLM.

```python
# Send the entire conversation state plus the tool definitions.
# `tools=TOOLS` is what tells the model which actions it may call.
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
```

3. Append the assistant response. Check `stop_reason` -- if the model didn't call a tool, we're done.

```python
# Preserve the assistant turn exactly as returned.
# `response.content` may contain text blocks and tool calls together.
messages.append({"role": "assistant", "content": response.content})
# If the model is done thinking with tools, exit the loop.
if response.stop_reason != "tool_use":
    return
```

4. Execute each tool call, collect results, append as a user message. Loop back to step 2.

```python
# Gather every tool result from this assistant turn into one payload.
results = []
for block in response.content:
    # A single response can contain multiple content blocks.
    # Only `tool_use` blocks should be executed locally.
    if block.type == "tool_use":
        # Read the command proposed by the model and run it.
        output = run_bash(block.input["command"])
        results.append({
            # `tool_result` links this output back to the original tool call.
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
# Feed the tool outputs back so the model can continue reasoning.
messages.append({"role": "user", "content": results})
```

Assembled into one function:

```python
def agent_loop(query):
    # Begin with a fresh conversation containing only the current task.
    messages = [{"role": "user", "content": query}]
    while True:
        # Ask the model what to do next given the conversation so far.
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        # Save the assistant turn before inspecting it.
        messages.append({"role": "assistant", "content": response.content})

        # No tool call means the agent has reached its final answer.
        if response.stop_reason != "tool_use":
            return

        # Otherwise, execute each requested tool and collect the outputs.
        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_bash(block.input["command"])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        # Turn tool outputs into the next user message, then loop again.
        messages.append({"role": "user", "content": results})
```

That's the entire agent in under 30 lines. Everything else in this course layers on top -- without changing the loop.

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
