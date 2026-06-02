# s13: Slash Commands

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > [ s13 ] s14 > s15 > s16 > s17 > s18 > s19`

> *"User shortcuts that bypass the model"* -- instant actions with zero API cost.
>
> **Harness layer**: Input interception -- the harness catches commands before they reach the model.

## Problem

By s12, the agent is powerful but every interaction goes through the LLM. "Show me the tasks" costs tokens. "Clear history" costs tokens. "What tools do I have?" costs tokens. These are harness operations, not model operations.

## Solution

```
User input:
+-------------+
| "/tasks"    |
+-----+-------+
      |
      v
[Slash command router]  <--- harness intercepts, model never sees it
      |
+----+-----+------------+
|     |     |            |
v     v     v            v
List  Clear  Show     Inject context
tasks  history  tools  (e.g. /plan)

Two categories:
  1. Standalone (no model call): /tasks, /clear, /tools
     - Zero API cost, zero latency
  2. Context injection (becomes a message): /plan, /debug
     - Short input -> rich, pre-written instruction
```

## How It Works

1. **Parse input.** If it starts with `/`, route to the command handler.

```python
def handle_slash_command(query):
    if not query.startswith("/"):
        return (None, query)  # not a command
    cmd = query[1:].split()[0]
    handler = SLASH_COMMANDS.get(cmd)
    ...
```

2. **Execute standalone commands.** Print output, skip the model entirely.

```python
if action == "standalone":
    if payload == "__CLEAR__":
        history.clear()
    else:
        print(payload)
    continue  # never reaches agent_loop()
```

3. **Inject context commands.** Expand to a rich prompt, send to the model.

```python
if action == "inject":
    history.append({"role": "user", "content": payload})
    agent_loop(history)
```

## Try It

```sh
cd learn-claude-code
python agents/s13_slash_commands.py
```

Try these:

1. `/tasks` -- list tasks (no API call)
2. `/tools` -- show available tools (no API call)
3. `/plan` -- enters structured planning mode
4. `/clear` -- clears conversation history
5. Any normal text -- routes to the model as usual
