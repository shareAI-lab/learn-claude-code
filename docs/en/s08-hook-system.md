# s08: Hook System

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > [ s08 ] > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

## What You'll Learn

- Three lifecycle events that let external code observe and influence the agent loop
- How shell-based hooks run as subprocesses with full context about the current tool call
- The exit code protocol: 0 means continue, 1 means block, 2 means inject a message
- How to configure hooks in an external JSON file so you never touch the main loop code

Your agent from s07 has a permission system that controls what it is allowed to do. But permissions are a yes/no gate -- they do not let you add new behavior. Suppose you want every bash command to be logged to an audit file, or you want a linter to run automatically after every file write, or you want a custom security scanner to inspect tool inputs before they execute. You could add if/else branches inside the main loop for each of these, but that turns your clean loop into a tangle of special cases. What you really want is a way to extend the agent's behavior from the outside, without modifying the loop itself.

## The Problem

You are running your agent in a team environment. Different teams want different behaviors: the security team wants to scan every bash command, the QA team wants to auto-run tests after file edits, and the ops team wants an audit trail of every tool call. If each of these requires code changes to the agent loop, you end up with a mess of conditionals that nobody can maintain. Worse, every new requirement means redeploying the agent. You need a way for teams to plug in their own logic at well-defined moments -- without touching the core code.

## The Solution

The agent loop exposes three fixed extension points (lifecycle events). At each point, it runs external shell commands called hooks. Each hook communicates its intent through its exit code: continue silently, block the operation, or inject a message into the conversation.

```
tool_call from LLM
     |
     v
[PreToolUse hooks]
     |  exit 0 -> continue
     |  exit 1 -> block tool, return stderr as error
     |  exit 2 -> inject stderr into conversation, continue
     |
     v
[execute tool]
     |
     v
[PostToolUse hooks]
     |  exit 0 -> continue
     |  exit 2 -> append stderr to result
     |
     v
return result
```

## Read Together

- If you still picture hooks as "more if/else branches inside the main loop," you might find it helpful to revisit [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md) first.
- If the main loop, the tool handler, and hook side effects start to blur together, [`entity-map.md`](./entity-map.md) can help you separate who advances core state and who only watches from the side.
- If you plan to continue into prompt assembly, recovery, or teams, keeping [`s00e-reference-module-map.md`](./s00e-reference-module-map.md) nearby is useful because this "core loop plus sidecar extension" pattern returns repeatedly.

## How It Works

**Step 1.** Define three lifecycle events. `SessionStart` fires once when the agent starts up -- useful for initialization, logging, or environment checks. `PreToolUse` fires before every tool call and is the only event that can block execution. `PostToolUse` fires after every tool call and can annotate the result but cannot undo it.

| Event | When | Can Block? |
|-------|------|-----------|
| `SessionStart` | Once at session start | No |
| `PreToolUse` | Before each tool call | Yes (exit 1) |
| `PostToolUse` | After each tool call | No |

**Step 2.** Configure hooks in an external `.hooks.json` file at the workspace root. Each hook specifies a shell command to run. An optional `matcher` field filters by tool name -- without a matcher, the hook fires for every tool.

```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "bash", "command": "echo 'Checking bash command...'"},
      {"matcher": "write_file", "command": "/path/to/lint-check.sh"}
    ],
    "PostToolUse": [
      {"command": "echo 'Tool finished'"}
    ],
    "SessionStart": [
      {"command": "echo 'Session started at $(date)'"}
    ]
  }
}
```

**Step 3.** Implement the exit code protocol. This is the heart of the hook system -- three exit codes, three meanings. The protocol is deliberately simple so that any language or script can participate. Write your hook in bash, Python, Ruby, whatever -- as long as it exits with the right code.

| Exit Code | Meaning | PreToolUse | PostToolUse |
|-----------|---------|-----------|------------|
| 0 | Success | Continue to execute tool | Continue normally |
| 1 | Block | Tool NOT executed, stderr returned as error | Warning logged |
| 2 | Inject | stderr injected as message, tool still executes | stderr appended to result |

**Step 4.** Pass context to hooks via environment variables. Hooks need to know what is happening -- which event triggered them, which tool is being called, and what the input looks like. For `PostToolUse` hooks, the tool output is also available.

```
HOOK_EVENT=PreToolUse
HOOK_TOOL_NAME=bash
HOOK_TOOL_INPUT={"command": "npm test"}
HOOK_TOOL_OUTPUT=...  (PostToolUse only)
```

**Step 5.** Integrate hooks into the agent loop. The integration is clean: run pre-hooks before execution, check if any blocked, execute the tool, run post-hooks, and collect any injected messages. The loop still owns control flow -- hooks only observe, block, or annotate at named moments.

```python
# Before tool execution
pre_result = hooks.run_hooks("PreToolUse", ctx)
if pre_result["blocked"]:
    output = f"Blocked by hook: {pre_result['block_reason']}"
    continue

# Execute tool
output = handler(**tool_input)

# After tool execution
post_result = hooks.run_hooks("PostToolUse", ctx)
for msg in post_result["messages"]:
    output += f"\n[Hook note]: {msg}"
```

## What Changed From s07

| Component | Before (s07) | After (s08) |
|-----------|-------------|-------------|
| Extensibility | None | Shell-based hook system |
| Events | None | PreToolUse, PostToolUse, SessionStart |
| Control flow | Permission pipeline only | Permission + hooks |
| Configuration | In-code rules | External `.hooks.json` file |

## Try It

```sh
cd learn-claude-code
# Create a hook config
cat > .hooks.json << 'EOF'
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "bash", "command": "echo 'Auditing bash command' >&2; exit 0"}
    ],
    "SessionStart": [
      {"command": "echo 'Agent session started'"}
    ]
  }
}
EOF
python agents/s08_hook_system.py
```

1. Watch SessionStart hook fire at startup
2. Ask the agent to run a bash command -- see PreToolUse hook fire
3. Create a blocking hook (exit 1) and watch it prevent tool execution
4. Create an injecting hook (exit 2) and watch it add messages to the conversation

## What You've Mastered

At this point, you can:

- Explain why extension points are better than in-loop conditionals for adding new behavior
- Define lifecycle events at the right moments in the agent loop
- Write shell hooks that communicate intent through a three-code exit protocol
- Configure hooks externally so different teams can customize behavior without touching the agent code
- Maintain the boundary: the loop owns control flow, the handler owns execution, hooks only observe, block, or annotate

## What's Next

Your agent can now execute tools safely (s07) and be extended without code changes (s08). But it still has amnesia -- every new session starts from zero. The user's preferences, corrections, and project context are forgotten the moment the session ends. In s09, you will build a memory system that lets the agent carry durable facts across sessions.

## Key Takeaway

> The main loop can expose fixed extension points without giving up ownership of control flow -- hooks observe, block, or annotate, but the loop still decides what happens next.
